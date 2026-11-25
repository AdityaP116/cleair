# Cleair (UAQA) — Institutional Air Quality Operations & Intelligence Platform

**Cleair** (Urban Air Quality Assistant) is an enterprise-ready air quality operations and environmental intelligence platform built for schools, campuses, and commercial facilities in the **Mumbai Metropolitan Region (MMR)**.

It implements the complete institutional operational lifecycle:

$$\text{MEASURE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{DECIDE} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY}$$

---

## Key Capabilities

- **Institutional Facility Hierarchy:** Multi-tier modeling (`Organization → Site → Building → Floor → Zone`) with non-cascading soft deletion to preserve historical telemetry.
- **Authenticated IoT Telemetry Ingestion:** Cryptographic sensor keys (256-bit entropy, salted SHA-256, constant-time verification), composite idempotency, physical boundary classification (`VALID`, `SUSPECT`, `OUT_OF_RANGE`, `INVALID`), and UTC freshness tracking (`ONLINE`, `STALE`, `OFFLINE`).
- **Mumbai Ambient Context:** Live outdoor air quality integration via Open-Meteo / CAMS with resilient regional baseline fallbacks.
- **Configurable Operational Alert Engine:** Deterministic threshold evaluation for $PM_{2.5}$ and $CO_2$, alert deduplication, and lifecycle management (`OPEN → ACKNOWLEDGED → RESOLVED`).
- **Corrective Work Orders & Interventions:** Auditable task dispatch (`WorkOrder`, `WorkOrderEvent`, `InterventionRecord`) with automatic alert resolution on completion.
- **Before/After Intervention Verification:** Empirical $T_{-60\text{min}}$ vs. $T_{+60\text{min}}$ telemetry comparison with explicit epistemic integrity disclaimers (*"Observed change — not proof of causation"*).
- **Compliance & Reporting:** 7-day institutional operations summary and RFC 4180 CSV telemetry export.
- **Zero-NPM Enterprise Web Dashboard:** Responsive Vanilla ES6 + Tailwind PWA with `Manrope` / `JetBrains Mono` typography and full API integration.

---

## Repository Structure

```text
cleair/
├── apps/
│   ├── web/                   # Zero-npm Vanilla ES6 + Tailwind PWA dashboard
│   └── api/                   # Legacy B2C service layer & regression test suite
├── backend/                   # FastAPI institutional operations backend
│   ├── app/
│   │   ├── api/               # Routes (telemetry, facilities, alerts, work_orders, reports, chat)
│   │   ├── core/              # Security utilities (256-bit keygen, constant-time compare)
│   │   ├── db/                # SQLAlchemy 2.x session & Base
│   │   ├── models/            # ORM models (institutional, telemetry, alerts, work_orders)
│   │   ├── modules/           # Domain modules (ingestion, alerts, operations, safety, impact)
│   │   ├── repositories/      # Data access layer
│   │   └── schemas/           # Pydantic request/response schemas
│   ├── migrations/            # Alembic migration environment
│   ├── tests/                 # Institutional unit & integration test suite (18 tests)
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   └── seed_pilot.py          # Synthetic pilot data generator
├── data/kb/                   # Knowledge base starter JSON
├── eval/                      # Golden set evaluation benchmarks
├── packages/shared/           # OpenAPI specification & shared TypeScript types
├── docs/                      # Architecture decisions, stage reports, and technical audits
├── .gitignore
└── README.md
```

---

## Quickstart (Local Development)

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Seed Pilot Data (Optional)
```powershell
$env:PYTHONPATH="backend"
python backend/seed_pilot.py
```

### 3. Start the Unified Server (Backend + Web Dashboard)
```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **Dashboard UI:** `http://127.0.0.1:8000/`
- **Interactive API Docs (Swagger):** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/v1/health`

---

## Running Tests

### Institutional Backend Suite (18 Tests)
```cmd
set PYTHONPATH=backend && python -m pytest backend/tests -v
```

### Legacy B2C Regression Suite (11 Tests)
```cmd
set PYTHONPATH=apps/api && python -m pytest apps/api/app/tests -v
```

---

## Security & Data Integrity

- **No Client-Side Secrets:** Hardware ingestion keys are never exposed in browser JavaScript; the UI simulator uses a dedicated server-side `/v1/telemetry/simulate` endpoint.
- **Rate Limiting:** Sliding-window HTTP rate-limiting middleware (`120 req/min` per IP).
- **Provenance Separation:** All readings explicitly distinguish `MEASURED`, `SIMULATED`, and `ESTIMATED` data.
- **Historical Preservation:** Soft-deleting zones or sensors sets foreign keys on `sensor_readings` to `NULL` without purging historical baseline records.
