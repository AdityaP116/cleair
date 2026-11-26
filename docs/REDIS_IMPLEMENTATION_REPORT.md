# Redis Implementation Report

## 1. Distributed Rate Limiting (`backend/app/main.py`)
- Uses atomic Redis `INCR` + `EXPIRE` pipeline per `(client_ip, window_bucket)`.
- Extracts client IP from `X-Forwarded-For` only when the direct peer is in `TRUSTED_PROXIES`.
- Configurable via `RATE_LIMIT_MAX_REQUESTS` (default `120`) and `RATE_LIMIT_WINDOW_SEC` (default `60`).
- **Degradation Policy**: Controlled by `RATE_LIMIT_FAIL_OPEN` (`True` logs warning and allows traffic; `False` returns `503 Service Unavailable`).

## 2. Distributed Air-Quality Caching (`backend/app/modules/air_quality/service.py`)
- Cache key: `air_quality:v1:{lat:.4f}:{lon:.4f}` with `CACHE_TTL_SEC = 900` (15 minutes).
- Falls back to process-local cache and demo city baselines if Redis and Open-Meteo are unavailable.
