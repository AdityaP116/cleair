from typing import Dict, Any, Tuple
from datetime import datetime

def check_reading_quality(observed_at_iso: str, distance_km: float) -> Tuple[bool, str]:
    """
    Checks if air reading is stale (>3h) and assigns confidence based on station distance.
    Confidence:
      High: <= 3 km
      Medium: <= 10 km
      Low: > 10 km or model only
    """
    is_stale = False
    try:
        obs_time = datetime.fromisoformat(observed_at_iso.replace("Z", "+00:00"))
        now = datetime.now(obs_time.tzinfo)
        diff_hours = (now - obs_time).total_seconds() / 3600.0
        if diff_hours > 3.0:
            is_stale = True
    except Exception:
        pass

    if distance_km <= 3.0:
        confidence = "High"
    elif distance_km <= 10.0:
        confidence = "Medium"
    else:
        confidence = "Low"

    return is_stale, confidence
