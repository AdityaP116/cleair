import pytest
from app.services.guardrail_service import OutputGuardrail

@pytest.fixture
def guardrail():
    return OutputGuardrail()

def test_guardrail_blocks_severity_downgrade(guardrail):
    bad_response = {
        "advice_level": "NORMAL", # Mismatched with expected SEVERE
        "headline": "Air is okay",
        "summary": "You can go outside.",
        "disclaimer": "General guidance."
    }
    valid, violations = guardrail.validate(bad_response, expected_level="SEVERE")
    assert valid is False
    assert any("SR-01" in v for v in violations)

def test_guardrail_blocks_banned_safe_phrases_at_high_severity(guardrail):
    unsafe_response = {
        "advice_level": "HIGH",
        "headline": "High Pollution",
        "summary": "It is completely safe to go out for morning exercise.",
        "disclaimer": "General guidance."
    }
    valid, violations = guardrail.validate(unsafe_response, expected_level="HIGH")
    assert valid is False
    assert any("SR-05" in v for v in violations)

def test_guardrail_blocks_medication_dosages(guardrail):
    rx_response = {
        "advice_level": "NORMAL",
        "headline": "Cold advice",
        "summary": "Take 500 mg tablet azithromycin twice daily.",
        "disclaimer": "General guidance."
    }
    valid, violations = guardrail.validate(rx_response, expected_level="NORMAL")
    assert valid is False
    assert any("SR-03" in v for v in violations)
