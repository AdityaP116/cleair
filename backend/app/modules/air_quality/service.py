from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.modules.air_quality.calculator import calculate_cpcb_subindex, get_aqi_category
from app.modules.air_quality.quality_checker import check_reading_quality

class AirQualityService:
    def get_current(self, lat: float = 28.6139, lon: float = 77.2090) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        pm25 = 198.4
        pm10 = 320.1
        aqi = calculate_cpcb_subindex(pm25)
        cat = get_aqi_category(aqi)
        is_stale, confidence = check_reading_quality(now_iso, distance_km=3.4)

        return {
            "location": {"city": "Delhi-NCR", "geohash": "ttnfv2", "lat": lat, "lon": lon},
            "aqi": aqi,
            "category": cat,
            "dominant_pollutant": "PM2.5",
            "pm25": pm25,
            "pm10": pm10,
            "no2": 45.2,
            "o3": 28.0,
            "so2": 14.5,
            "co": 1.8,
            "station": {
                "name": "Anand Vihar, Delhi",
                "distance_km": 3.4,
                "source": "CPCB/DPCC"
            },
            "confidence": confidence,
            "observed_at": now_iso,
            "stale": is_stale
        }

    def get_forecast(self, lat: float = 28.6139, lon: float = 77.2090, hours: int = 48) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        points = []
        hourly_curve = [210, 240, 260, 230, 160, 130, 115, 140, 185, 240, 290, 320]
        
        for i in range(min(hours, 48)):
            pm25 = hourly_curve[i % len(hourly_curve)]
            aqi = calculate_cpcb_subindex(pm25)
            cat = get_aqi_category(aqi)
            t_str = (now + timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
            points.append({
                "valid_at": t_str,
                "aqi": aqi,
                "aqi_category": cat,
                "pm25": float(pm25),
                "pm10": round(pm25 * 1.6, 1),
                "wind_speed_ms": 2.2,
                "temp_c": 19.5,
                "humidity_pct": 65.0
            })

        return {
            "geohash": "ttnfv2",
            "issued_at": now.isoformat(),
            "points": points
        }

air_service = AirQualityService()
