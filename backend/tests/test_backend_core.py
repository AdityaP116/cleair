import pytest
from app.modules.safety.rules import safety_engine
from app.modules.impact.interventions import interventions_calc
from app.modules.impact.purifier import purifier_model
from app.modules.safety.validator import output_validator

def test_safety_rule_matrix_full():
    general = {"has_child": False, "has_respiratory_condition": False}
    sensitive = {"has_child": True, "has_respiratory_condition": True}

    assert safety_engine.evaluate(45, general)["advice_level"] == "NORMAL"
    assert safety_engine.evaluate(150, sensitive)["advice_level"] == "CAUTION"
    assert safety_engine.evaluate(250, sensitive)["advice_level"] == "HIGH"
    assert safety_engine.evaluate(350, sensitive)["advice_level"] == "SEVERE"
    assert safety_engine.evaluate(450, sensitive)["advice_level"] == "EMERGENCY"

def test_symptom_escalation_detection():
    has_sym, msg = safety_engine.check_symptom_escalation("Patient is struggling to breathe with severe wheeze")
    assert has_sym is True
    assert "EMERGENCY HEALTH WARNING" in msg

def test_impact_calculations():
    mask = interventions_calc.calc_mask_impact(200.0, "n95_good")
    assert mask["reduction_pct"] == 75.0
    assert mask["formula_id"] == "IMP-MASK-01"

    purifier = purifier_model.calculate_steady_state(200.0, 20.0, 300.0)
    assert purifier["reduction_pct"] > 70.0
    assert purifier["formula_id"] == "IMP-PURIFIER-01"

    commute = interventions_calc.calc_commute_switch(15.0, "petrol_car", "metro")
    assert commute["value"] > 0
    assert commute["formula_id"] == "IMP-COMMUTE-01"

def test_guardrail_enforcement():
    bad = {
        "advice_level": "NORMAL",
        "headline": "Safe air",
        "summary": "Outdoor is completely safe to go out.",
        "disclaimer": "General guidance"
    }
    valid, violations = output_validator.validate(bad, expected_level="HIGH")
    assert valid is False
    assert any("SR-01" in v or "SR-05" in v for v in violations)
