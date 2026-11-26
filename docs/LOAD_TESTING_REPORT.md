# Load Testing Report

## Framework & Workloads
- **Tool**: Locust (`backend/tests/locustfile.py`).
- **Workloads**: `CleairB2CUser` exercising `/v1/session`, `/v1/air/current`, `/v1/air/forecast`, and `/v1/health`.

## Status
- Locust workload script is installed and ready for execution against an isolated staging environment with live PostgreSQL and Redis.
- Multi-worker capacity benchmarks (50, 100, 250, 500 VUs) must be executed against the target staging cluster before claiming production capacity.
