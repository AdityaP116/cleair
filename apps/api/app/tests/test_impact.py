import pytest
from app.services.impact_service import ImpactCalculator

@pytest.fixture
def calc():
    return ImpactCalculator()

def test_mask_impact_monotonicity(calc):
    # Good N95 vs poor N95 vs surgical vs cloth
    n95_g = calc.calc_mask_impact(200.0, mask_type="n95_good")
    n95_p = calc.calc_mask_impact(200.0, mask_type="n95_poor")
    surg = calc.calc_mask_impact(200.0, mask_type="surgical")
    cloth = calc.calc_mask_impact(200.0, mask_type="cloth")

    assert n95_g["reduction_pct"] > n95_p["reduction_pct"] > surg["reduction_pct"] > cloth["reduction_pct"]
    assert n95_g["after"] < n95_p["after"] < surg["after"] < cloth["after"]
    assert n95_g["formula_id"] == "IMP-MASK-01"

def test_purifier_impact_mass_balance(calc):
    # Higher CADR must lower steady-state PM2.5
    low_cadr = calc.calc_purifier_impact(ambient_pm25=200.0, cadr_m3h=150.0)
    high_cadr = calc.calc_purifier_impact(ambient_pm25=200.0, cadr_m3h=400.0)

    assert high_cadr["after"] < low_cadr["after"]
    assert high_cadr["reduction_pct"] > low_cadr["reduction_pct"]
    assert high_cadr["formula_id"] == "IMP-PURIFIER-01"

def test_commute_switch_savings(calc):
    # Car to Metro saves CO2
    res = calc.calc_commute_switch(distance_km=20.0, baseline_mode="petrol_car", new_mode="metro")
    assert res["value"] > 0
    assert res["reduction_pct"] > 70
    assert res["formula_id"] == "IMP-COMMUTE-01"

def test_clean_air_score(calc):
    score_high = calc.calc_clean_air_score(80.0, 90.0, 4.5)
    score_low = calc.calc_clean_air_score(10.0, 20.0, 0.5)
    assert 0 <= score_low < score_high <= 100
