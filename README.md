# Urban Air Quality Assistant (UAQA / Cleair)

**Institutional Air Quality Operations & Intelligence Platform (Mumbai Pilot)**

Operational workflow: `MEASURE → UNDERSTAND → DECIDE → ACT → VERIFY`

---

## Repository Structure

- `backend/` — FastAPI institutional operations backend (telemetry ingestion, alerts, work orders, verification, reporting)
- `apps/web/` — Zero-npm Vanilla ES6 + CSS PWA dashboard
- `apps/api/` — Legacy B2C service layer and regression test suite
- `data/` — Knowledge base data (`kb_starter.json`)
- `eval/` — Golden set evaluation data (`golden_set.json`)
- `packages/shared/` — OpenAPI spec and shared TypeScript types
- `docs/` — Architecture decisions, stage reports, and technical audits (`docs/audits/`)

---

## Quickstart (Local Development)

### 1. Start the Unified Server (Backend + Web Dashboard)
```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- **Dashboard UI:** `http://127.0.0.1:8000/`
- **API Docs (Swagger):** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/v1/health`

### 2. Run Test Suites
**Institutional Backend Tests (18 tests):**
```cmd
set PYTHONPATH=backend && python -m pytest backend/tests -v
```

**Legacy B2C Regression Tests (11 tests):**
```cmd
set PYTHONPATH=apps/api && python -m pytest apps/api/app/tests -v
```
