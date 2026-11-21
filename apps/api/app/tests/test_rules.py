import pytest
from app.services.rules_service import RuleEngine

@pytest.fixture
def rule_engine():
    return RuleEngine()

def test_aqi_category_mapping(rule_engine):
    assert rule_engine.get_category_for_aqi(45) == "Good"
    assert rule_engine.get_category_for_aqi(85) == "Satisfactory"
    assert rule_engine.get_category_for_aqi(150) == "Moderate"
    assert rule_engine.get_category_for_aqi(250) == "Poor"
    assert rule_engine.get_category_for_aqi(350) == "Very Poor"
    assert rule_engine.get_category_for_aqi(450) == "Severe"

def test_rule_matrix_full_cells(rule_engine):
    general_profile = {"has_child": False, "has_respiratory_condition": False}
    sensitive_profile = {"has_child": True, "has_respiratory_condition": True}

    # Good / Satisfactory -> NORMAL for both
    assert rule_engine.evaluate(40, general_profile)["advice_level"] == "NORMAL"
    assert rule_engine.evaluate(40, sensitive_profile)["advice_level"] == "NORMAL"

    # Moderate (101-200) -> GENERAL: NORMAL, SENSITIVE: CAUTION
    assert rule_engine.evaluate(150, general_profile)["advice_level"] == "NORMAL"
    assert rule_engine.evaluate(150, sensitive_profile)["advice_level"] == "CAUTION"

    # Poor (201-300) -> GENERAL: CAUTION, SENSITIVE: HIGH
    assert rule_engine.evaluate(250, general_profile)["advice_level"] == "CAUTION"
    assert rule_engine.evaluate(250, sensitive_profile)["advice_level"] == "HIGH"

    # Very Poor (301-400) -> GENERAL: HIGH, SENSITIVE: SEVERE
    assert rule_engine.evaluate(350, general_profile)["advice_level"] == "HIGH"
    assert rule_engine.evaluate(350, sensitive_profile)["advice_level"] == "SEVERE"

    # Severe (401-500) -> GENERAL: SEVERE, SENSITIVE: EMERGENCY
    assert rule_engine.evaluate(450, general_profile)["advice_level"] == "SEVERE"
    assert rule_engine.evaluate(450, sensitive_profile)["advice_level"] == "EMERGENCY"

def test_symptom_escalation(rule_engine):
    has_sym, msg = rule_engine.check_symptom_escalation("My child has severe wheeze and chest pain")
    assert has_sym is True
    assert "EMERGENCY HEALTH WARNING" in msg

    # Hindi symptom check
    has_sym_hi, msg_hi = rule_engine.check_symptom_escalation("मुझे सांस लेने में तकलीफ हो रही है", lang="hi")
    assert has_sym_hi is True
    assert "आपातकालीन स्वास्थ्य चेतावनी" in msg_hi

    # Non-symptom query
    has_sym_norm, _ = rule_engine.check_symptom_escalation("What time is best for a morning walk?")
    assert has_sym_norm is False
