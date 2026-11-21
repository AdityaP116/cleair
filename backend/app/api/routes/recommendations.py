from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo
from app.modules.safety.rules import safety_engine

router = APIRouter()

@router.get("/plan")
def get_daily_plan(date: str = "today", user_id: str = Depends(get_current_user_id)):
    profile = repo.get_profile(user_id)
    risk = safety_engine.evaluate(worst_aqi=348, profile=profile)
    level = risk["advice_level"]

    return {
        "date": date,
        "best_outdoor_window": {
            "start": "13:00",
            "end": "15:00",
            "pm25": 115.0,
            "reason": "Midday thermal solar heating temporarily disperses ground-level smog accumulation."
        },
        "blocks": [
            {
                "start": "07:00",
                "end": "09:00",
                "type": "commute",
                "note": "Morning inversion peak",
                "reason": "Low boundary layer traps traffic emissions.",
                "benefit": "N95 mask avoids 75% inhaled fine particle mass.",
                "severity": level
            },
            {
                "start": "13:00",
                "end": "14:30",
                "type": "ventilation",
                "note": "Best room airing slot",
                "reason": "Daily PM2.5 minimum occurs during early afternoon.",
                "benefit": "15-minute quick airing clears indoor CO2.",
                "severity": "NORMAL" if level in ["NORMAL", "CAUTION"] else "HIGH"
            },
            {
                "start": "18:00",
                "end": "20:00",
                "type": "exercise",
                "note": "Evening exercise indoors only",
                "reason": "Surface cooling in winter causes swift evening particulate surge.",
                "benefit": "Exercising indoors prevents up to 180 µg inhaled PM2.5.",
                "severity": level
            }
        ]
    }
