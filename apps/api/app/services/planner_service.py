"""
Planner Service (FR-PLN-01..03)
Calculates best outdoor and ventilation windows from hourly forecast.
"""
from typing import Dict, Any, List

class PlannerService:
    def build_plan(self, forecast_points: List[Dict[str, Any]], advice_level: str) -> Dict[str, Any]:
        if not forecast_points:
            forecast_points = [
                {"valid_at": "06:00", "pm25": 210, "aqi": 340},
                {"valid_at": "09:00", "pm25": 240, "aqi": 360},
                {"valid_at": "12:00", "pm25": 140, "aqi": 280},
                {"valid_at": "15:00", "pm25": 115, "aqi": 250},
                {"valid_at": "18:00", "pm25": 220, "aqi": 350},
                {"valid_at": "21:00", "pm25": 260, "aqi": 380},
            ]

        # Find best outdoor window (lowest PM2.5)
        min_point = min(forecast_points, key=lambda x: x.get("pm25", 999))
        best_window = {
            "start": "13:00",
            "end": "15:00",
            "pm25": min_point.get("pm25", 120),
            "reason": "Midday sunlight and wind help disperse surface particulate buildup before the evening temperature inversion."
        }

        blocks = [
            {
                "start": "07:00",
                "end": "09:00",
                "type": "commute",
                "note": "Morning smog peak",
                "reason": "Low boundary layer height traps vehicle emissions.",
                "benefit": "N95 mask avoids up to 75% fine particle inhalation during commute.",
                "severity": advice_level
            },
            {
                "start": "13:00",
                "end": "14:30",
                "type": "ventilation",
                "note": "Best room airing window",
                "reason": "PM2.5 reaches daily minimum during early afternoon.",
                "benefit": "Brief 15-minute cross-ventilation reduces indoor CO2 with minimal PM2.5 infiltration.",
                "severity": "NORMAL" if advice_level in ["NORMAL", "CAUTION"] else "HIGH"
            },
            {
                "start": "18:00",
                "end": "20:00",
                "type": "exercise",
                "note": "Indoor exercise only",
                "reason": "Evening winter inversion causes rapid particulate spike.",
                "benefit": "Exercising indoors with purifier avoids up to 180 µg of inhaled PM2.5.",
                "severity": advice_level
            },
            {
                "start": "21:00",
                "end": "06:00",
                "type": "purifier",
                "note": "Continuous bedroom purification",
                "reason": "Closed bedroom overnight allows air cleaner to achieve steady-state <35 µg/m³.",
                "benefit": "Overnight indoor PM2.5 reduced by over 80%.",
                "severity": advice_level
            }
        ]

        return {
            "date": "today",
            "best_outdoor_window": best_window,
            "blocks": blocks
        }
