# CLEAIR Distributed Architecture

## Current Architecture
- **API**: FastAPI (`backend/app/main.py`) with Uvicorn workers.
- **Database**: SQLAlchemy 2.x (`backend/app/db/session.py`) supporting SQLite for local dev and PostgreSQL (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`) for production.
- **Shared State**: Redis (`backend/app/core/redis_client.py`) for distributed rate limiting and air-quality caching.
- **Readiness**: `GET /v1/ready` verifies database and Redis connectivity.

## Proposed Production Topology
- Multiple stateless Uvicorn/Gunicorn workers behind a trusted reverse proxy (`TRUSTED_PROXIES`).
- Managed PostgreSQL primary with automated backups and connection pooling.
- Managed Redis instance for shared rate-limit counters and 15-minute Open-Meteo cache.
