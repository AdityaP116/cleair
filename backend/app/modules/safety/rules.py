from typing import Dict, Any, List, Tuple
from pathlib import Path
import yaml
import re

RULES_CONFIG_PATH = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "config" / "rules.yaml"

class SafetyRuleEngine:
    def __init__(self, config_path: Path = RULES_CONFIG_PATH):
        if not config_path.exists():
            # Fallback path if run from root
            config_path = Path("apps/api/app/config/rules.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.matrix = self.config["matrix"]
        self.categories = self.config["aqi_categories"]
        self.mandatory_actions = self.config["mandatory_actions"]
        self.symptoms_config = self.config.get("symptoms_escalation", {})

    def get_category_for_aqi(self, aqi: int) -> str:
        for cat in self.categories:
            if cat["min"] <= aqi <= cat["max"]:
                return cat["name"]
        return "Severe" if aqi > 500 else "Good"

    def is_sensitive(self, profile: Dict[str, Any]) -> bool:
        flags = [
            "has_child",
            "has_elderly",
            "is_pregnant",
            "has_respiratory_condition",
            "has_heart_condition"
        ]
        return any(bool(profile.get(f)) for f in flags)

    def evaluate(self, worst_aqi: int, profile: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
        category = self.get_category_for_aqi(worst_aqi)
        vuln_class = "SENSITIVE" if self.is_sensitive(profile) else "GENERAL"
        
        category_entry = self.matrix.get(category, self.matrix["Moderate"])
        advice_level = category_entry.get(vuln_class, "NORMAL")

        actions_dict = self.mandatory_actions.get(advice_level, {})
        actions = actions_dict.get(lang) or actions_dict.get("en", [])

        rule_id = f"RULE-{category.upper()[:4]}-{vuln_class[:4]}-v1"

        return {
            "advice_level": advice_level,
            "worst_aqi": worst_aqi,
            "worst_category": category,
            "vulnerability_class": vuln_class,
            "rule_id": rule_id,
            "mandatory_actions": actions,
            "grap_stage": "Stage III (Severe)" if worst_aqi >= 301 else "Normal Advisory"
        }

    def check_symptom_escalation(self, text: str, lang: str = "en") -> Tuple[bool, str]:
        if not text:
            return False, ""
        text_lower = text.lower()
        keywords_dict = self.symptoms_config.get("keywords", {})
        
        all_keywords = []
        if lang in keywords_dict:
            all_keywords.extend(keywords_dict[lang])
        for l, kws in keywords_dict.items():
            if l != lang:
                all_keywords.extend(kws)

        for kw in all_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower) or kw in text_lower:
                msg = self.symptoms_config.get("escalation_message", {}).get(
                    lang, self.symptoms_config.get("escalation_message", {}).get("en", "")
                )
                return True, msg
        return False, ""

safety_engine = SafetyRuleEngine()
