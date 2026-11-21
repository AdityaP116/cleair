from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo
from app.modules.impact.interventions import interventions_calc
from app.modules.impact.purifier import purifier_model
from app.modules.impact.exposure import exposure_calc
from app.schemas import ImpactEstimateRequest, LogActionRequest

router = APIRouter()

@router.post("/estimate")
def estimate_impact(req: ImpactEstimateRequest):
    params = req.params or {}
    if req.action == "wear_mask":
        return interventions_calc.calc_mask_impact(
            ambient_pm25=params.get("ambient_pm25", 198.4),
            mask_type=params.get("mask_type", "n95_good"),
            duration_hours=params.get("duration_hours", 1.0)
        )
    elif req.action == "run_purifier":
        return purifier_model.calculate_steady_state(
            ambient_pm25=params.get("ambient_pm25", 198.4),
            floor_area_sqm=params.get("floor_area_sqm", 20.0),
            cadr_m3h=params.get("cadr_m3h", 250.0)
        )
    elif req.action == "commute_switch":
        return interventions_calc.calc_commute_switch(
            distance_km=params.get("distance_km", 15.0),
            baseline_mode=params.get("baseline_mode", "petrol_car"),
            new_mode=params.get("new_mode", "metro")
        )
    return interventions_calc.calc_mask_impact(ambient_pm25=198.4)

@router.post("/actions")
def log_action(req: LogActionRequest, user_id: str = Depends(get_current_user_id)):
    entry = {
        "action_type": req.action_type,
        "exposure_delta_ugm3h": 148.8,
        "co2_saved_kg": 2.1
    }
    repo.add_action_log(user_id, entry)
    score = interventions_calc.calc_clean_air_score(
        exposure_reduction_pct=72.0,
        action_consistency_pct=85.0,
        emissions_saved_kg=4.2
    )
    return {
        "success": True,
        "exposure_delta_ugm3h": entry["exposure_delta_ugm3h"],
        "co2_saved_kg": entry["co2_saved_kg"],
        "clean_air_score": score
    }

@router.get("/dashboard")
def get_dashboard(range: str = "7d", user_id: str = Depends(get_current_user_id)):
    logs = repo.get_action_logs(user_id)
    cig = exposure_calc.calculate_cigarette_equiv(pm25_24h_avg=198.4, exposure_hours=8.0)
    return {
        "clean_air_score": 78,
        "streak_days": 5,
        "cigarette_equiv_avoided": round(cig["value"] * 0.75, 1),
        "cigarette_disclaimer": cig["disclaimer"],
        "co2_saved_kg": 6.3,
        "exposure_reduction_pct": 68.5,
        "exposure_trend": [
            {"date": "Mon", "actual_ugm3h": 140, "baseline_ugm3h": 320},
            {"date": "Tue", "actual_ugm3h": 125, "baseline_ugm3h": 340},
            {"date": "Wed", "actual_ugm3h": 160, "baseline_ugm3h": 380},
            {"date": "Thu", "actual_ugm3h": 90, "baseline_ugm3h": 310},
            {"date": "Fri", "actual_ugm3h": 110, "baseline_ugm3h": 350},
            {"date": "Sat", "actual_ugm3h": 85, "baseline_ugm3h": 348},
            {"date": "Sun", "actual_ugm3h": 70, "baseline_ugm3h": 290}
        ],
        "recent_actions": logs[-5:]
    }
