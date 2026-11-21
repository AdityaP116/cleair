from typing import Dict, Any, List, Tuple
from pathlib import Path
import yaml
import re

IMPACT_CONFIG_PATH = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "config" / "impact.yaml"

class OutputValidator:
    def __init__(self, config_path: Path = IMPACT_CONFIG_PATH):
        if not config_path.exists():
            config_path = Path("apps/api/app/config/impact.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.banned_phrases = cfg.get("banned_phrases_high_severity", [])
        self.medication_denylist = [
            "mg", "milligram", "tablet", "dosage", "prescribe", "azithromycin",
            "montelukast", "prednisone", "steroid", "inhaler puffs"
        ]

    def validate(self, response: Dict[str, Any], expected_level: str) -> Tuple[bool, List[str]]:
        violations = []
        actual_level = response.get("advice_level")

        if actual_level != expected_level:
            violations.append(f"SR-01 violation: Advice level altered from {expected_level} to {actual_level}")

        if expected_level in ["HIGH", "SEVERE", "EMERGENCY"]:
            full_text = (response.get("headline", "") + " " + response.get("summary", "")).lower()
            for action in response.get("actions", []):
                full_text += " " + action.get("title", "").lower() + " " + action.get("why", "").lower()
            
            for phrase in self.banned_phrases:
                if phrase in full_text:
                    violations.append(f"SR-05 violation: High-severity response contains forbidden phrase '{phrase}'")

        full_text = (response.get("headline", "") + " " + response.get("summary", "")).lower()
        for med in self.medication_denylist:
            if re.search(r"\b" + re.escape(med) + r"\b", full_text):
                violations.append(f"SR-03 violation: Medical/dosage term '{med}' detected in non-clinical advice")

        if not response.get("disclaimer"):
            violations.append("SR-07 violation: Missing mandatory health disclaimer")

        return len(violations) == 0, violations

output_validator = OutputValidator()
