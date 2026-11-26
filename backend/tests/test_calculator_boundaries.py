from app.modules.air_quality.calculator import calculate_cpcb_subindex, get_aqi_category


def test_cpcb_pm25_breakpoints():
    assert calculate_cpcb_subindex(0.0) == 0
    assert calculate_cpcb_subindex(30.0) == 50
    assert calculate_cpcb_subindex(60.0) == 100
    assert calculate_cpcb_subindex(90.0) == 200
    assert calculate_cpcb_subindex(120.0) == 300
    assert calculate_cpcb_subindex(250.0) == 400
    assert calculate_cpcb_subindex(500.0) >= 400


def test_cpcb_aqi_categories():
    assert get_aqi_category(25) == "Good"
    assert get_aqi_category(75) == "Satisfactory"
    assert get_aqi_category(150) == "Moderate"
    assert get_aqi_category(250) == "Poor"
    assert get_aqi_category(350) == "Very Poor"
    assert get_aqi_category(450) == "Severe"
