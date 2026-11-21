import pytest
import json
from pathlib import Path
from app.services.rules_service import RuleEngine

# Project root eval directory
GOLDEN_SET_PATH = Path(__file__).resolve().parents[4] / "eval" / "golden_set.json"

@pytest.fixture
def rule_engine():
    return RuleEngine()

def test_golden_set_benchmarks(rule_engine):
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    scenarios = data.get("scenarios", [])
    assert len(scenarios) > 0

    for sc in scenarios:
        res = rule_engine.evaluate(worst_aqi=sc["worst_aqi"], profile=sc["profile"])
        assert res["advice_level"] == sc["expected_advice_level"], f"Failed scenario {sc['id']}"
