from typing import Dict, Any, List

def calculate_cpcb_subindex(pm25: float) -> int:
    """
    Computes CPCB AQI sub-index for PM2.5 (24-hour breakpoint concentration in µg/m³)
    Standard breakpoints:
    0-30: 0-50 (Good)
    31-60: 51-100 (Satisfactory)
    61-90: 101-200 (Moderate)
    91-120: 201-300 (Poor)
    121-250: 301-400 (Very Poor)
    250+: 401-500 (Severe)
    """
    if pm25 <= 30:
        return int((50 / 30) * pm25)
    elif pm25 <= 60:
        return int(50 + ((100 - 50) / (60 - 30)) * (pm25 - 30))
    elif pm25 <= 90:
        return int(100 + ((200 - 100) / (90 - 60)) * (pm25 - 60))
    elif pm25 <= 120:
        return int(200 + ((300 - 200) / (120 - 90)) * (pm25 - 90))
    elif pm25 <= 250:
        return int(300 + ((400 - 300) / (250 - 120)) * (pm25 - 120))
    else:
        # Severe
        aqi = int(400 + ((500 - 400) / (380 - 250)) * (pm25 - 250))
        return min(500, max(401, aqi))

def get_aqi_category(aqi: int) -> str:
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"
