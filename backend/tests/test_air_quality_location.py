from fastapi.testclient import TestClient
from app.main import app
from app.modules.air_quality.service import AirQualityService

client = TestClient(app)


def test_air_current_mumbai_returns_mumbai():
    res = client.get("/v1/air/current?lat=19.0760&lon=72.8777")
    assert res.status_code == 200
    data = res.json()
    assert data["location"]["city"] == "Mumbai"
    assert data["source"] in ("live", "cached", "demo")


def test_air_current_delhi_returns_delhi():
    res = client.get("/v1/air/current?lat=28.6139&lon=77.2090")
    assert res.status_code == 200
    assert res.json()["location"]["city"] == "Delhi-NCR"


def test_air_current_invalid_coordinates_rejected():
    res = client.get("/v1/air/current?lat=999&lon=72.8")
    assert res.status_code == 422


def test_air_provider_failure_falls_back_to_demo_without_500(monkeypatch):
    svc = AirQualityService()
    monkeypatch.setattr(svc, "_fetch_open_meteo", lambda lat, lon: None)
    data = svc.get_current(19.0760, 72.8777)
    assert data["location"]["city"] == "Mumbai"
    assert data["source"] == "demo"
    assert data["stale"] is True
