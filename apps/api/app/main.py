"""
FastAPI Main Application (SRS B3, B7)
Implements contract-first REST endpoints for UAQA SmogSense.
"""
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import datetime

from app.services.rules_service import RuleEngine
from app.services.impact_service import ImpactCalculator
from app.services.rag_service import KnowledgeService
from app.services.guardrail_service import OutputGuardrail
from app.services.planner_service import PlannerService

app = FastAPI(
    title="Urban Air Quality Assistant (SmogSense) API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/v1/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for sessions, profiles, logs
SESSIONS: Dict[str, str] = {} # token -> user_id
PROFILES: Dict[str, Dict[str, Any]] = {}
ACTION_LOGS: Dict[str, List[Dict[str, Any]]] = {}

# Services
rules_engine = RuleEngine()
impact_calc = ImpactCalculator()
rag_service = KnowledgeService()
guardrail = OutputGuardrail()
planner_service = PlannerService()

# ----------------- Helper Auth -----------------
def get_user_id(x_session_token: Optional[str] = Header(None)) -> str:
    if not x_session_token:
        # Default anonymous demo session
        return "default-demo-user"
    if x_session_token not in SESSIONS:
        SESSIONS[x_session_token] = "user-" + str(uuid.uuid4())[:8]
    return SESSIONS[x_session_token]

# ----------------- Endpoints -----------------

@app.get("/v1/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dependencies": {
            "rule_engine": "operational",
            "impact_calculator": "operational",
            "rag_knowledge_base": "operational",
            "guardrail": "active"
        }
    }

@app.post("/v1/session")
def create_session():
    token = "sess-" + str(uuid.uuid4())
    user_id = "user-" + str(uuid.uuid4())[:8]
    SESSIONS[token] = user_id
    PROFILES[user_id] = {
        "user_id": user_id,
        "city": "Delhi",
        "has_child": False,
        "has_elderly": False,
        "is_pregnant": False,
        "has_respiratory_condition": False,
        "has_heart_condition": False,
        "commute_mode": "two_wheeler",
        "commute_minutes_per_day": 45,
        "outdoor_work": False,
        "home_size_sqm": 25.0,
        "ceiling_height_m": 2.7,
        "has_purifier": True,
        "purifier_cadr_m3h": 250.0,
        "has_ac": True,
        "cooking_fuel": "png",
        "budget_tier": "low",
        "language": "en",
        "briefing_time": "06:30"
    }
    ACTION_LOGS[user_id] = []
    return {"session_token": token, "user_id": user_id}

@app.get("/v1/profile")
def get_profile(x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    if uid not in PROFILES:
        PROFILES[uid] = {
            "user_id": uid,
            "city": "Delhi",
            "has_child": True,
            "has_elderly": False,
            "is_pregnant": False,
            "has_respiratory_condition": True,
            "has_heart_condition": False,
            "commute_mode": "two_wheeler",
            "budget_tier": "low",
            "language": "en",
            "briefing_time": "06:30"
        }
    return PROFILES[uid]

@app.put("/v1/profile")
def update_profile(update: Dict[str, Any], x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    if uid not in PROFILES:
        PROFILES[uid] = {"user_id": uid}
    PROFILES[uid].update(update)
    return PROFILES[uid]

@app.get("/v1/air/current")
def get_current_air(lat: Optional[float] = 28.6139, lon: Optional[float] = 77.2090):
    return {
        "location": {"city": "Delhi-NCR", "geohash": "ttnfv2"},
        "aqi": 348,
        "category": "Very Poor",
        "dominant_pollutant": "PM2.5",
        "pm25": 198.4,
        "pm10": 320.1,
        "no2": 45.2,
        "o3": 28.0,
        "station": {"name": "Anand Vihar, Delhi", "distance_km": 3.4, "source": "CPCB/DPCC"},
        "confidence": "High",
        "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stale": False
    }

@app.get("/v1/air/forecast")
def get_forecast(lat: Optional[float] = 28.6139, lon: Optional[float] = 77.2090, hours: int = 48):
    now = datetime.datetime.now(datetime.timezone.utc)
    points = []
    hourly_pm25 = [210, 240, 260, 220, 160, 130, 115, 140, 190, 250, 310, 340]
    for i in range(min(hours, 24)):
        val = hourly_pm25[i % len(hourly_pm25)]
        aqi_val = int(val * 1.6)
        cat = rules_engine.get_category_for_aqi(aqi_val)
        time_str = (now + datetime.timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
        points.append({
            "valid_at": time_str,
            "aqi": aqi_val,
            "aqi_category": cat,
            "pm25": val,
            "pm10": round(val * 1.6, 1),
            "wind_speed_ms": 2.2,
            "temp_c": 19.5
        })
    return {
        "geohash": "ttnfv2",
        "issued_at": now.isoformat(),
        "points": points
    }

@app.get("/v1/risk")
def get_risk(x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    profile = PROFILES.get(uid, {"has_child": True, "has_respiratory_condition": True})
    lang = profile.get("language", "en")
    
    # Evaluate at current worst peak (348 AQI)
    risk = rules_engine.evaluate(worst_aqi=348, profile=profile, lang=lang)
    risk["grap_stage"] = "Stage III (Severe)"
    risk["evaluated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return risk

@app.get("/v1/plan")
def get_daily_plan(date: str = "today", x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    profile = PROFILES.get(uid, {})
    risk = rules_engine.evaluate(worst_aqi=348, profile=profile)
    return planner_service.build_plan([], risk["advice_level"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@app.post("/v1/chat")
def chat_turn(req: ChatRequest, x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    profile = PROFILES.get(uid, {"has_child": True, "has_respiratory_condition": True, "language": "en"})
    lang = profile.get("language", "en")

    # 1. Check for immediate symptom escalation (SR-02 / B8.6)
    has_symptoms, escalation_text = rules_engine.check_symptom_escalation(req.message, lang=lang)
    if has_symptoms:
        return {
            "advice_level": "EMERGENCY",
            "headline": "Emergency Health Alert",
            "summary": escalation_text,
            "actions": [
                {
                    "title": "Immediate Medical Assistance",
                    "why": "Severe acute respiratory or cardiac symptoms require in-person clinical assessment.",
                    "impact": {"text": "Urgent Medical Care", "value": 1, "unit": "Emergency", "formula_id": "SR-02"},
                    "cost_tier": "free",
                    "citations": ["kb-who-2021"]
                }
            ],
            "citations": rag_service.search("respiratory distress asthma", top_k=2),
            "uncertainty_note": None,
            "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
            "symptom_escalation": True,
            "followups": ["Where is the nearest hospital?", "How to use an emergency rescue inhaler?"]
        }

    # 2. Get rule-engine severity
    risk = rules_engine.evaluate(worst_aqi=348, profile=profile, lang=lang)
    advice_level = risk["advice_level"]

    # 3. Retrieve relevant citations
    citations = rag_service.search(req.message, top_k=3)

    # 4. Impact calculation sample
    mask_impact = impact_calc.calc_mask_impact(ambient_pm25=198.4, mask_type="n95_good", duration_hours=1.5, is_child=profile.get("has_child", False))
    purifier_impact = impact_calc.calc_purifier_impact(ambient_pm25=198.4, floor_area_sqm=22.0, cadr_m3h=250.0)

    # 5. Formulate structured response
    response_data = {
        "advice_level": advice_level,
        "headline": f"Risk Level: {advice_level} (AQI 348 - Very Poor)",
        "summary": f"Given your household profile with vulnerable family members, outdoor exposure should be strictly minimized today.",
        "actions": [
            {
                "title": "Equip Certified N95 / FFP2 Respirator",
                "why": "Unfiltered ambient air contains hazardous PM2.5 concentrations exceeding safe limits by 13x.",
                "impact": {
                    "text": f"Avoids {mask_impact['value']} µg PM2.5 inhalation during commute",
                    "value": mask_impact["value"],
                    "unit": mask_impact["unit"],
                    "formula_id": mask_impact["formula_id"]
                },
                "cost_tier": "low",
                "citations": ["kb-epa-masks"]
            },
            {
                "title": "Run HEPA Purifier in Main Living Space",
                "why": "Reduces steady-state indoor particulate infiltration down to comfortable thresholds.",
                "impact": {
                    "text": f"Reduces indoor PM2.5 to ~{purifier_impact['value']} µg/m³ ({purifier_impact['reduction_pct']}% reduction)",
                    "value": purifier_impact["value"],
                    "unit": purifier_impact["unit"],
                    "formula_id": purifier_impact["formula_id"]
                },
                "cost_tier": "mid",
                "citations": ["kb-epa-cadr"]
            },
            {
                "title": "Reschedule Outdoor Routine to Midday Window",
                "why": "Atmospheric boundary layer is highest between 13:00 - 15:00, lowering surface particulate spikes.",
                "impact": {
                    "text": "Lowest daily ambient exposure window",
                    "value": 115.0,
                    "unit": "µg/m³ ambient",
                    "formula_id": "IMP-VENT-01"
                },
                "cost_tier": "free",
                "citations": ["kb-cpcb-aqi"]
            }
        ],
        "citations": citations,
        "uncertainty_note": "Impact calculations are estimations based on ambient measurements and standard ventilation heuristics.",
        "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
        "followups": [
            "Which mask is safe for my child?",
            "How should I size an air purifier for my room?",
            "Is it safe to walk in the morning?"
        ]
    }

    # 6. Run Guardrail Verification
    is_valid, violations = guardrail.validate(response_data, expected_level=advice_level)
    if not is_valid:
        # Fallback to guaranteed rule-engine template (SR-06)
        response_data["summary"] = " " .join(risk["mandatory_actions"])
        response_data["limited_mode"] = True

    return response_data

@app.post("/v1/impact/estimate")
def estimate_impact(req: Dict[str, Any]):
    action = req.get("action")
    params = req.get("params", {})
    if action == "wear_mask":
        return impact_calc.calc_mask_impact(
            ambient_pm25=params.get("ambient_pm25", 198.4),
            mask_type=params.get("mask_type", "n95_good"),
            duration_hours=params.get("duration_hours", 1.0)
        )
    elif action == "run_purifier":
        return impact_calc.calc_purifier_impact(
            ambient_pm25=params.get("ambient_pm25", 198.4),
            floor_area_sqm=params.get("floor_area_sqm", 20.0),
            cadr_m3h=params.get("cadr_m3h", 250.0)
        )
    elif action == "commute_switch":
        return impact_calc.calc_commute_switch(
            distance_km=params.get("distance_km", 15.0),
            baseline_mode=params.get("baseline_mode", "petrol_car"),
            new_mode=params.get("new_mode", "metro")
        )
    else:
        return impact_calc.calc_mask_impact(ambient_pm25=198.4)

@app.post("/v1/actions")
def log_action(req: Dict[str, Any], x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    if uid not in ACTION_LOGS:
        ACTION_LOGS[uid] = []
    
    action_type = req.get("action_type", "wore_n95")
    entry = {
        "id": "act-" + str(uuid.uuid4())[:8],
        "action_type": action_type,
        "logged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "exposure_delta_ugm3h": 148.8,
        "co2_saved_kg": 2.1
    }
    ACTION_LOGS[uid].append(entry)
    
    score = impact_calc.calc_clean_air_score(
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

@app.get("/v1/dashboard")
def get_dashboard(range: str = "7d", x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    logs = ACTION_LOGS.get(uid, [])
    cig = impact_calc.calc_cigarette_equivalence(pm25_24h_avg=198.4, exposure_hours=8.0)

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

@app.delete("/v1/privacy/data")
def delete_user_data(x_session_token: Optional[str] = Header(None)):
    uid = get_user_id(x_session_token)
    if uid in PROFILES:
        del PROFILES[uid]
    if uid in ACTION_LOGS:
        del ACTION_LOGS[uid]
    return {"success": True, "message": "All personal profile and activity logs have been permanently deleted."}
