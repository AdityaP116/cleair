from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.modules.air_quality.service import AirQualityService

client = TestClient(app)


def test_readiness_healthy():
    res = client.get("/v1/ready")
    assert res.status_code == 200
    assert res.json()["database"] is True


def test_readiness_db_unavailable():
    with patch("app.main.check_db_health", return_value=False):
        res = client.get("/v1/ready")
        assert res.status_code == 503
        assert res.json()["status"] == "not_ready"


def test_redis_rate_limit_fail_open_and_closed():
    mock_redis = MagicMock()
    mock_redis.pipeline.side_effect = ConnectionError("Redis down")
    with patch("app.main.get_redis_client", return_value=mock_redis):
        with patch.object(settings, "RATE_LIMIT_FAIL_OPEN", True):
            res = client.get("/v1/health")
            assert res.status_code == 200
        with patch.object(settings, "RATE_LIMIT_FAIL_OPEN", False):
            res = client.get("/v1/health")
            assert res.status_code == 503


def test_air_quality_open_meteo_timeout_fallback():
    svc = AirQualityService()
    with patch.object(svc, "_fetch_open_meteo", return_value=None):
        data = svc.get_current(19.0760, 72.8777)
        assert data["aqi"] > 0
        assert "Demo" in data.get("source", "") or data.get("is_demo", True)
