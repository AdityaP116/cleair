from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import math
import time
import httpx

from app.modules.air_quality.calculator import calculate_cpcb_subindex, get_aqi_category
from app.modules.air_quality.quality_checker import check_reading_quality

_CITY_BASELINES = [
    {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777, "pm25": 58.5, "pm10": 105.0, "no2": 32.1, "so2": 10.2, "co": 0.9, "o3": 24.5},
    {"city": "Thane", "lat": 19.2183, "lon": 72.9781, "pm25": 62.0, "pm10": 112.0, "no2": 34.0, "so2": 11.0, "co": 1.0, "o3": 26.0},
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567, "pm25": 48.0, "pm10": 88.0, "no2": 26.5, "so2": 8.5, "co": 0.7, "o3": 29.0},
    {"city": "Delhi-NCR", "lat": 28.6139, "lon": 77.2090, "pm25": 198.4, "pm10": 320.1, "no2": 45.2, "so2": 14.5, "co": 1.8, "o3": 28.0},
    {"city": "Kolkata", "lat": 22.5726, "lon": 88.3639, "pm25": 95.0, "pm10": 165.0, "no2": 38.0, "so2": 12.0, "co": 1.2, "o3": 25.0},
    {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "pm25": 32.0, "pm10": 62.0, "no2": 22.0, "so2": 6.0, "co": 0.6, "o3": 30.0},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nearest_city(lat: float, lon: float) -> Tuple[Dict[str, Any], float]:
    best = min(_CITY_BASELINES, key=lambda c: _haversine_km(lat, lon, c["lat"], c["lon"]))
    dist = round(_haversine_km(lat, lon, best["lat"], best["lon"]), 1)
    return best, dist


import json
import logging
from app.core.redis_client import get_redis_client

_aq_logger = logging.getLogger("cleair.air_quality")

class AirQualityService:
    OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    CACHE_TTL_SEC = 900

    def __init__(self):
        self._cache: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}

    def _cache_key(self, lat: float, lon: float) -> str:
        return f"air_quality:v1:{round(lat, 4):.4f}:{round(lon, 4):.4f}"

    def _get_cached(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        r = get_redis_client()
        if r is not None:
            try:
                raw = r.get(self._cache_key(lat, lon))
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                _aq_logger.warning("Redis cache get failed: %s", type(exc).__name__)
        key = (round(lat, 3), round(lon, 3))
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self.CACHE_TTL_SEC:
                return data
        return None

    def _set_cached(self, lat: float, lon: float, data: Dict[str, Any]) -> None:
        r = get_redis_client()
        if r is not None:
            try:
                r.setex(self._cache_key(lat, lon), self.CACHE_TTL_SEC, json.dumps(data))
            except Exception as exc:
                _aq_logger.warning("Redis cache set failed: %s", type(exc).__name__)
        key = (round(lat, 3), round(lon, 3))
        self._cache[key] = (time.time(), data)

    def _fetch_open_meteo(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "timezone": "auto",
        }
        for attempt in range(2):
            try:
                with httpx.Client(timeout=4.0) as client:
                    res = client.get(self.OPEN_METEO_URL, params=params)
                    if res.status_code == 200:
                        return res.json().get("current", {})
            except Exception:
                if attempt == 0:
                    time.sleep(0.2)
        return None

    def get_current(self, lat: float = 28.6139, lon: float = 77.2090) -> Dict[str, Any]:
        key = (round(lat, 2), round(lon, 2))
        now_ts = time.time()
        now_utc = datetime.now(timezone.utc)
        nearest, dist_km = _nearest_city(lat, lon)

        cached_val = self._get_cached(lat, lon)
        if cached_val is not None:
            return cached_val

        curr = self._fetch_open_meteo(lat, lon)
        if curr and curr.get("pm2_5") is not None:
            pm25 = float(curr["pm2_5"])
            pm10 = float(curr.get("pm10") or round(pm25 * 1.6, 1))
            no2 = float(curr.get("nitrogen_dioxide") or 0.0)
            so2 = float(curr.get("sulphur_dioxide") or 0.0)
            co = float(curr.get("carbon_monoxide") or 0.0)
            o3 = float(curr.get("ozone") or 0.0)
            aqi = calculate_cpcb_subindex(pm25)
            cat = get_aqi_category(aqi)
            is_stale, confidence = check_reading_quality(now_utc.isoformat(), distance_km=dist_km)
            reading = {
                "location": {"city": nearest["city"], "lat": lat, "lon": lon, "distance_km": dist_km},
                "aqi": aqi,
                "category": cat,
                "dominant_pollutant": "PM2.5" if pm25 >= pm10 * 0.5 else "PM10",
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2,
                "so2": so2,
                "co": co,
                "o3": o3,
                "pollutants": {"pm25": pm25, "pm10": pm10, "no2": no2, "so2": so2, "co": co, "o3": o3},
                "station": {"name": f"{nearest['city']} Grid", "distance_km": dist_km, "source": "open-meteo"},
                "source": "live",
                "confidence": confidence,
                "observed_at": now_utc.isoformat(),
                "stale": is_stale,
                "age_minutes": 0.0,
            }
            self._cache[key] = (now_ts, reading)
            return reading

        if key in self._cache:
            cached_ts, cached_val = self._cache[key]
            return {
                **cached_val,
                "source": "cached",
                "stale": True,
                "age_minutes": round((now_ts - cached_ts) / 60.0, 1),
            }

        pm25 = nearest["pm25"]
        aqi = calculate_cpcb_subindex(pm25)
        cat = get_aqi_category(aqi)
        return {
            "location": {"city": nearest["city"], "lat": lat, "lon": lon, "distance_km": dist_km},
            "aqi": aqi,
            "category": cat,
            "dominant_pollutant": "PM2.5",
            "pm25": pm25,
            "pm10": nearest["pm10"],
            "no2": nearest["no2"],
            "so2": nearest["so2"],
            "co": nearest["co"],
            "o3": nearest["o3"],
            "pollutants": {
                "pm25": pm25, "pm10": nearest["pm10"], "no2": nearest["no2"],
                "so2": nearest["so2"], "co": nearest["co"], "o3": nearest["o3"],
            },
            "station": {"name": f"{nearest['city']} Demo Baseline", "distance_km": dist_km, "source": "demo"},
            "source": "demo",
            "confidence": "Low",
            "observed_at": now_utc.isoformat(),
            "stale": True,
            "age_minutes": 0.0,
        }

    def get_forecast(self, lat: float = 28.6139, lon: float = 77.2090, hours: int = 48) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        nearest, _ = _nearest_city(lat, lon)
        base_pm25 = nearest["pm25"]
        points = []
        factors = [0.9, 1.0, 1.1, 1.0, 0.75, 0.65, 0.6, 0.7, 0.85, 1.05, 1.15, 1.2]
        for i in range(min(hours, 48)):
            pm25 = round(base_pm25 * factors[i % len(factors)], 1)
            aqi = calculate_cpcb_subindex(pm25)
            cat = get_aqi_category(aqi)
            points.append({
                "valid_at": (now + timedelta(hours=i)).strftime("%Y-%m-%d %H:00"),
                "aqi": aqi,
                "aqi_category": cat,
                "pm25": float(pm25),
                "pm10": round(pm25 * 1.6, 1),
                "wind_speed_ms": 2.2,
                "temp_c": 24.0 if lat < 23 else 18.0,
                "humidity_pct": 65.0,
            })
        return {"city": nearest["city"], "issued_at": now.isoformat(), "source": "demo", "points": points}


air_service = AirQualityService()
