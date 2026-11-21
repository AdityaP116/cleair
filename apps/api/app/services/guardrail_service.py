"""
Output Guardrail (SRS B12.2)
Deterministic checks enforcing non-negotiable safety rules before responses leave the backend.
"""
from typing import Dict, Any, List, Tuple
from pathlib import Path
import re
import yaml

IMPACT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "impact.yaml"

class OutputGuardrail:
    def __init__(self, config_path: Path = IMPACT_CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.banned_phrases = cfg.get("banned_phrases_high_severity", [])
        
        # Denylist for prescription medication and dosages (SR-03)
        self.medication_denylist = [
            "mg", "milligram", "tablet", "dosage", "prescribe", "azithromycin",
            "montelukast", "prednisone", "steroid", "inhaler puffs"
        ]

    def validate(self, response: Dict[str, Any], expected_level: str) -> Tuple[bool, List[str]]:
        violations = []
        actual_level = response.get("advice_level")

        # SR-01: LLM must not downgrade or alter advice_level
        if actual_level != expected_level:
            violations.append(f"SR-01 violation: Advice level altered from {expected_level} to {actual_level}")

        # SR-05: Never say outdoor activity is safe when level >= HIGH
        if expected_level in ["HIGH", "SEVERE", "EMERGENCY"]:
            full_text = (response.get("headline", "") + " " + response.get("summary", "")).lower()
            for action in response.get("actions", []):
                full_text += " " + action.get("title", "").lower() + " " + action.get("why", "").lower()
            
            for phrase in self.banned_phrases:
                if phrase in full_text:
                    violations.append(f"SR-05 violation: High-severity response contains forbidden phrase '{phrase}'")

        # SR-03: No medication names or dosages
        full_text = (response.get("headline", "") + " " + response.get("summary", "")).lower()
        for med in self.medication_denylist:
            if re.search(r"\b" + re.escape(med) + r"\b", full_text):
                violations.append(f"SR-03 violation: Medical/dosage term '{med}' detected in non-clinical advice")

        # SR-07: Disclaimer must be present
        if not response.get("disclaimer"):
            violations.append("SR-07 violation: Missing mandatory health disclaimer")

        return len(violations) == 0, violations
