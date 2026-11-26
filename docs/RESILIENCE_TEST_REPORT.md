# Resilience Test Report

Automated resilience tests in `backend/tests/test_resilience.py` verify:
1. **`/v1/ready` Healthy**: Returns `200 OK` when database is reachable.
2. **Database Unavailable**: Returns `503 Service Unavailable` when `check_db_health()` fails.
3. **Redis Rate-Limit Degradation**:
   - `RATE_LIMIT_FAIL_OPEN=True`: Logs warning and serves `200 OK`.
   - `RATE_LIMIT_FAIL_OPEN=False`: Returns `503 Service Unavailable`.
4. **Open-Meteo Timeout Fallback**: `AirQualityService.get_current()` falls back to demo city baseline without crashing.
