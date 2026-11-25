from typing import Dict, Any, List, Optional
from app.modules.safety.rules import safety_engine
from app.modules.safety.validator import output_validator
from app.modules.impact.interventions import interventions_calc
from app.modules.impact.purifier import purifier_model
from app.modules.knowledge.retrieval import knowledge_retrieval

class AgentOrchestrator:
    def process_turn(self, message: str, profile: Dict[str, Any], current_aqi: int = 348, air_reading: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        lang = profile.get("language", "en")

        # 1. Symptom check (SR-02 / B8.6)
        has_sym, escalation_msg = safety_engine.check_symptom_escalation(message, lang=lang)
        if has_sym:
            return {
                "advice_level": "EMERGENCY",
                "headline": "Emergency Health Alert",
                "summary": escalation_msg,
                "actions": [
                    {
                        "title": "Immediate Medical Assistance",
                        "why": "Severe acute respiratory or cardiac symptoms require emergency in-person medical care.",
                        "impact": {"text": "Urgent Medical Care", "value": 1, "unit": "Emergency", "formula_id": "SR-02"},
                        "cost_tier": "free",
                        "citations": ["kb-who-2021"]
                    }
                ],
                "citations": knowledge_retrieval.search("respiratory distress asthma", top_k=2),
                "uncertainty_note": None,
                "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
                "symptom_escalation": True,
                "followups": ["Where is the nearest hospital?", "Emergency inhaler technique"]
            }

        # 2. Rule-engine deterministic evaluation
        risk = safety_engine.evaluate(worst_aqi=current_aqi, profile=profile, lang=lang)
        advice_level = risk["advice_level"]

        # 3. Retrieve relevant citations
        citations = knowledge_retrieval.search(message, top_k=3)

        # 4. Impact calculation
        mask_impact = interventions_calc.calc_mask_impact(
            ambient_pm25=198.4,
            mask_type="n95_good",
            duration_hours=1.5,
            is_child=profile.get("has_child", False)
        )
        purifier_impact = purifier_model.calculate_steady_state(
            ambient_pm25=198.4,
            floor_area_sqm=profile.get("home_size_sqm", 25.0),
            cadr_m3h=profile.get("purifier_cadr_m3h", 250.0)
        )

        # 5. Build structured response
        response = {
            "advice_level": advice_level,
            "headline": f"Risk Level: {advice_level} (AQI {current_aqi})",
            "summary": f"Based on your profile, air quality requires strict protective measures today. {risk['mandatory_actions'][0] if risk['mandatory_actions'] else ''}",
            "actions": [
                {
                    "title": "Wear Certified N95/FFP2 Outdoors",
                    "why": "Ambient PM2.5 levels are hazardous. Standard cloth masks offer minimal filtration against fine particulates.",
                    "impact": {
                        "text": f"Avoids {mask_impact['value']} µg PM2.5 inhaled during outdoor travel",
                        "value": mask_impact["value"],
                        "unit": mask_impact["unit"],
                        "formula_id": mask_impact["formula_id"]
                    },
                    "cost_tier": "low",
                    "citations": ["kb-epa-masks"]
                },
                {
                    "title": "Run HEPA Purifier in Main Living Room",
                    "why": "Allows steady-state indoor PM2.5 to decrease to safer levels.",
                    "impact": {
                        "text": f"Brings indoor PM2.5 to ~{purifier_impact['value']} µg/m³ ({purifier_impact['reduction_pct']}% reduction)",
                        "value": purifier_impact["value"],
                        "unit": purifier_impact["unit"],
                        "formula_id": purifier_impact["formula_id"]
                    },
                    "cost_tier": "mid",
                    "citations": ["kb-epa-cadr"]
                },
                {
                    "title": "Reschedule Outdoor Routine to Midday Window",
                    "why": "Atmospheric boundary layer height reaches peak dispersion in the early afternoon.",
                    "impact": {
                        "text": "Avoids severe morning/evening temperature inversion",
                        "value": 115.0,
                        "unit": "µg/m³ ambient",
                        "formula_id": "IMP-VENT-01"
                    },
                    "cost_tier": "free",
                    "citations": ["kb-cpcb-aqi"]
                }
            ],
            "citations": citations,
            "uncertainty_note": "Impact numbers are model estimates based on standard ambient readings and ventilation heuristics.",
            "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
            "followups": [
                "Which mask fits a child securely?",
                "How long should I run my purifier?",
                "What is the best time for grocery shopping today?"
            ],
            "symptom_escalation": False,
            "limited_mode": False
        }

        # 6. Safety Guardrail
        is_valid, violations = output_validator.validate(response, expected_level=advice_level)
        if not is_valid:
            response["summary"] = " " .join(risk["mandatory_actions"])
            response["limited_mode"] = True

        return response

orchestrator = AgentOrchestrator()
