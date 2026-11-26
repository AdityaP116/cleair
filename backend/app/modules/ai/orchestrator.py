from typing import Dict, Any, Optional, List
import json
from app.modules.safety.rules import safety_engine
from app.modules.safety.validator import output_validator
from app.modules.impact.interventions import interventions_calc
from app.modules.impact.purifier import purifier_model
from app.modules.knowledge.retrieval import knowledge_retrieval
from app.modules.ai.guard import classify_input
from app.modules.ai.llm_provider import LLMProvider, get_llm_provider

_SYSTEM_PROMPT = (
    "You are Cleair, an air-quality guidance assistant for Indian urban families and communities. "
    "Use ONLY numbers present in FactsBundle; never invent statistics or percentages. "
    "Never recommend medication, dosages, or diagnose. Output valid JSON only matching the schema. "
    "Include daily_routines, indoor_hacks, and sustainable_alternatives tailored to the user's profile and budget. "
    "Reply in the user's language."
)

_RISK_ORDER = {"NORMAL": 0, "LOW": 0, "CAUTION": 1, "MODERATE": 1, "HIGH": 2, "SEVERE": 3, "EMERGENCY": 4}


class AgentOrchestrator:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm = llm_provider

    def _get_llm(self) -> Optional[LLMProvider]:
        return self._llm if self._llm is not None else get_llm_provider()

    def process_turn(
        self,
        message: str,
        profile: Dict[str, Any],
        current_aqi: int = 100,
        air_reading: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lang = profile.get("language", "en")
        guard_class, cleaned = classify_input(message)

        if guard_class == "empty":
            return self._canned(
                "NORMAL",
                "Please enter a question",
                "Ask me about today's air quality, indoor air hacks, commute protection, or community actions.",
            )

        if guard_class == "emergency":
            _, escalation_msg = safety_engine.check_symptom_escalation(cleaned, lang=lang)
            return {
                "advice_level": "EMERGENCY",
                "headline": "Emergency Health Alert",
                "summary": escalation_msg or "Severe respiratory or cardiac symptoms require immediate medical care. Call 112 or visit the nearest hospital.",
                "daily_routines": [{"title": "Seek Emergency Care", "detail": "Call 112 or go to the nearest emergency room immediately.", "when": "Now", "impact_ref": None}],
                "indoor_hacks": [],
                "sustainable_alternatives": [],
                "impact_explanations": [],
                "who_needs_extra_care": ["Anyone experiencing breathing distress or chest pain"],
                "when_to_seek_help": ["Immediately — call 112 or visit emergency services"],
                "disclaimer": "Emergency guidance only. Not a substitute for professional medical care.",
                "symptom_escalation": True,
                "generated_by": "guard",
            }

        if guard_class == "injection":
            return self._canned(
                "NORMAL",
                "Request Declined",
                "I cannot reveal internal instructions or override safety rules. I can help you with air-quality guidance and exposure reduction.",
            )

        if guard_class == "off_topic":
            return self._canned(
                "NORMAL",
                "Air Quality Assistant",
                "I specialize in air quality, indoor air protection, and low-emission daily routines. Ask me about local AQI, masks, purifiers, or commute options.",
            )

        if guard_class == "medication":
            return self._canned(
                "CAUTION",
                "Consult a Doctor or Pharmacist",
                "I cannot recommend medications or dosages. Please consult a qualified doctor or pharmacist for cough or respiratory symptoms. Meanwhile, stay indoors, keep windows closed during peak traffic, and use an N95 mask if stepping out.",
            )

        # Build deterministic FactsBundle from real air_reading + profile
        city = (air_reading or {}).get("location", {}).get("city", profile.get("city", "Your Area"))
        pm25 = float((air_reading or {}).get("pm25", max(10.0, current_aqi * 0.55)))
        source = (air_reading or {}).get("source", "demo")
        observed_at = (air_reading or {}).get("observed_at", "")
        stale = bool((air_reading or {}).get("stale", False))

        risk = safety_engine.evaluate(worst_aqi=current_aqi, profile=profile, lang=lang)
        advice_level = risk["advice_level"]

        mask_impact = interventions_calc.calc_mask_impact(
            ambient_pm25=pm25,
            mask_type="n95_good",
            duration_hours=1.5,
            is_child=profile.get("has_child", False),
        )
        purifier_impact = purifier_model.calculate_steady_state(
            ambient_pm25=pm25,
            floor_area_sqm=profile.get("home_size_sqm", 25.0),
            cadr_m3h=profile.get("purifier_cadr_m3h", 250.0),
        )

        facts_bundle = {
            "location": {"city": city, "source": source, "observed_at": observed_at, "stale": stale},
            "air": {"aqi": current_aqi, "pm25": pm25, "category": (air_reading or {}).get("category", advice_level)},
            "profile": {
                "has_child": profile.get("has_child", False),
                "has_elderly": profile.get("has_elderly", False),
                "is_pregnant": profile.get("is_pregnant", False),
                "has_respiratory_condition": profile.get("has_respiratory_condition", False),
                "commute_mode": profile.get("commute_mode", "two_wheeler"),
                "budget_tier": profile.get("budget_tier", "low"),
            },
            "safety": {"level": advice_level, "must_say": risk.get("mandatory_actions", [])},
            "computed_impacts": [
                {"id": "I1", "action": "n95_mask_commute", "value": mask_impact["value"], "unit": mask_impact["unit"], "basis": mask_impact["formula_id"]},
                {"id": "I2", "action": "hepa_purifier_bedroom", "value": purifier_impact["value"], "reduction_pct": purifier_impact["reduction_pct"], "unit": purifier_impact["unit"], "basis": purifier_impact["formula_id"]},
            ],
        }

        if guard_class == "misinformation_bait":
            return {
                "advice_level": advice_level,
                "headline": f"Air Purifier Limits ({city}, AQI {current_aqi})",
                "summary": f"Air purifiers do NOT remove 100% of pollution. Based on CADR mass-balance math, a 250 m³/h purifier reduces indoor PM2.5 by ~{purifier_impact['reduction_pct']}% (to ~{purifier_impact['value']} µg/m³), depending on room sealing and outdoor infiltration.",
                "daily_routines": [{"title": "Seal Windows During Peak Traffic", "detail": "Reduce outdoor infiltration so filtration works effectively.", "when": "08:00–11:00 AM & 06:00–10:00 PM", "impact_ref": None}],
                "indoor_hacks": [{"title": "Run Purifier on Medium/Auto", "detail": f"Targets ~{purifier_impact['value']} µg/m³ steady-state indoor PM2.5.", "cost": "medium", "impact_ref": "I2"}],
                "sustainable_alternatives": [{"title": "Wet-Mop Floors Instead of Dry Sweeping", "detail": "Prevents settled dust resuspension at zero cost.", "cost": "free", "long_term_benefit": "Lower indoor coarse particulates", "impact_ref": None}],
                "impact_explanations": [{"ref": "I2", "plain_explanation": f"Reduces indoor PM2.5 by ~{purifier_impact['reduction_pct']}%", "assumptions": "Closed windows, 25 m² room, 250 m³/h CADR"}],
                "who_needs_extra_care": ["Children, elderly, and people with asthma"],
                "when_to_seek_help": ["If experiencing persistent cough, wheezing, or shortness of breath"],
                "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
                "provenance": facts_bundle["location"],
                "generated_by": "rules",
            }

        # Try real LLM if configured
        llm = self._get_llm()
        if llm is not None:
            try:
                user_prompt = f"FactsBundle:\n{json.dumps(facts_bundle)}\n\nUserMessage:\n<<<{cleaned}>>>"
                llm_out = llm.generate_json(_SYSTEM_PROMPT, user_prompt)
                if isinstance(llm_out, dict) and "summary" in llm_out:
                    model_level = str(llm_out.get("risk_level", advice_level)).upper()
                    if _RISK_ORDER.get(model_level, 0) < _RISK_ORDER.get(advice_level, 0):
                        llm_out["risk_level"] = advice_level
                    llm_out["advice_level"] = llm_out.get("risk_level", advice_level)
                    llm_out["disclaimer"] = "General guidance, not medical advice. Consult a doctor for health concerns."
                    valid, _ = output_validator.validate(llm_out, advice_level)
                    if valid:
                        llm_out["headline"] = f"{city}: {llm_out['advice_level']} (AQI {current_aqi})"
                        llm_out["provenance"] = facts_bundle["location"]
                        llm_out["generated_by"] = "llm"
                        return llm_out
            except Exception:
                pass

        # Honest, location-aware deterministic fallback
        return self._build_rule_fallback(facts_bundle, risk, mask_impact, purifier_impact)

    def _canned(self, level: str, headline: str, summary: str) -> Dict[str, Any]:
        return {
            "advice_level": level,
            "headline": headline,
            "summary": summary,
            "daily_routines": [],
            "indoor_hacks": [],
            "sustainable_alternatives": [],
            "impact_explanations": [],
            "disclaimer": "General guidance, not medical advice.",
            "generated_by": "guard",
        }

    def _build_rule_fallback(
        self,
        facts: Dict[str, Any],
        risk: Dict[str, Any],
        mask_impact: Dict[str, Any],
        purifier_impact: Dict[str, Any],
    ) -> Dict[str, Any]:
        city = facts["location"]["city"]
        aqi = facts["air"]["aqi"]
        level = facts["safety"]["level"]
        if aqi <= 50:
            summary = f"Air quality in {city} is Good (AQI {aqi}). Outdoor activities are safe for most people."
        elif aqi <= 150:
            summary = f"Air quality in {city} is Moderate (AQI {aqi}). Sensitive groups should pace prolonged outdoor exertion."
        else:
            summary = f"Air quality in {city} is {level} (AQI {aqi}). Limit outdoor exposure and use protective measures."

        return {
            "advice_level": level,
            "headline": f"{city}: {level} (AQI {aqi})",
            "summary": summary,
            "daily_routines": [
                {
                    "title": "Time Outdoor Errands for Midday" if aqi > 100 else "Normal Outdoor Routine",
                    "detail": "Avoid early-morning and late-evening inversion peaks when pollutants trap near ground level." if aqi > 100 else "AQI is low; outdoor exercise and ventilation are safe.",
                    "when": "01:00 PM – 04:00 PM",
                    "impact_ref": None,
                },
                {
                    "title": "Wear N95/FFP2 During Commute" if aqi > 100 else "Optional Light Mask in Heavy Traffic",
                    "detail": f"Avoids ~{mask_impact['value']} {mask_impact['unit']} during a 1.5h commute.",
                    "when": "During transit",
                    "impact_ref": "I1",
                },
            ],
            "indoor_hacks": [
                {
                    "title": "Ventilation & Purifier Schedule",
                    "detail": f"Keep windows closed during traffic peaks; HEPA filtration brings indoor PM2.5 toward ~{purifier_impact['value']} µg/m³ ({purifier_impact['reduction_pct']}% reduction).",
                    "cost": "medium",
                    "impact_ref": "I2",
                },
                {
                    "title": "Wet-Mop Instead of Dry Sweeping",
                    "detail": "Prevents settled dust from re-entering indoor air.",
                    "cost": "free",
                    "impact_ref": None,
                },
            ],
            "sustainable_alternatives": [
                {
                    "title": "Use Public Transit / Metro or Carpool",
                    "detail": "Reduces tailpipe emissions and personal roadside exposure compared to open two-wheelers.",
                    "cost": "low",
                    "long_term_benefit": "Lower neighbourhood PM2.5 and NO2 emissions",
                    "impact_ref": None,
                },
                {
                    "title": "Avoid Waste or Leaf Burning",
                    "detail": "Report open burning to local municipal ward offices.",
                    "cost": "free",
                    "long_term_benefit": "Prevents acute local smoke spikes",
                    "impact_ref": None,
                },
            ],
            "impact_explanations": [
                {"ref": "I1", "plain_explanation": f"N95 mask avoids ~{mask_impact['value']} {mask_impact['unit']} inhaled", "assumptions": "1.5h outdoor travel, proper N95 fit"},
                {"ref": "I2", "plain_explanation": f"HEPA purifier reduces indoor PM2.5 by ~{purifier_impact['reduction_pct']}%", "assumptions": "25 m² room, 250 m³/h CADR, closed windows"},
            ],
            "who_needs_extra_care": ["Children, elderly, pregnant individuals, and people with asthma or heart conditions"],
            "when_to_seek_help": ["Seek medical care if experiencing wheezing, chest tightness, or shortness of breath"],
            "disclaimer": "General guidance, not medical advice. Consult a doctor for health concerns.",
            "provenance": facts["location"],
            "generated_by": "rules",
        }


orchestrator = AgentOrchestrator()
