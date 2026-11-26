# CLEAIR — Clearer Air. Smarter Living.

CLEAIR is an AI-powered environmental intelligence platform that helps individuals, families, communities, and institutions understand air-quality conditions and make better environmental decisions.

**Core Workflow:** `DISCOVER → UNDERSTAND → DECIDE → ACT → MEASURE`

---

## Platform Dimensions

### 1. B2C — Family & Community Environmental Intelligence
- **Public Landing & 5-Step Onboarding**: Personalized household profile setup.
- **Location-Aware Dashboard**: Live local AQI, pollutant breakdown (`PM2.5`, `PM10`, `NO2`, `O3`), and health guidance.
- **Air-Quality Intelligence & Forecasts**: Hourly forecasts and exposure trends.
- **AI Environmental Assistant**: Context-aware guidance powered by `GeminiLLMProvider` with deterministic rules-based fallback.
- **Daily Routines, Indoor Air & Planner**: Actionable low-emission routines and commute/ventilation windows.
- **Sustainability Calculator & Community Insights**: Track completed actions and estimated environmental impact.

### 2. B2B — Institutional Air Quality Operations Platform
- **Multi-Tenant Organization & Site Hierarchy**: Organization, site, block, floor, and zone management with strict tenant isolation.
- **Role-Based Access Control (RBAC)**: Enforced `ADMIN`, `FACILITY_STAFF`, and `VIEWER` roles.
- **IoT Sensor Authentication & Telemetry**: 256-bit sensor keys, constant-time verification, and composite idempotency.
- **Operational Alerts & Work Orders**: Configurable threshold rules, alert lifecycle, and before/after verification.
- **Compliance Reporting**: Automated site summaries and CSV/JSON exports.

---

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy 2.x, Pydantic Settings, SQLite / PostgreSQL
- **Frontend**: Vanilla ES6 JavaScript, Tailwind CSS (CDN), custom CSS design tokens (`apps/web/`)
- **Integrations**: Open-Meteo Air Quality & Weather APIs (with 15-minute cache), optional Google Gemini API
- **Deployment**: Docker, Uvicorn

---

## Quick Start

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in your values (never commit `.env` or real API keys):

```bash
cp .env.example .env
```

### 2. Run Locally
```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Start the API + Web Frontend
set PYTHONPATH=backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser. API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Run with Docker
```bash
docker build -t cleair .
docker run -p 8000:8000 --env-file .env cleair
```

---

## Running Tests

```bash
# Backend & institutional suite (71 tests)
set PYTHONPATH=backend
python -m pytest backend/tests -q

# Legacy B2C suite (11 tests)
set PYTHONPATH=apps/api
python -m pytest apps/api/app/tests -q
```

---

## Security & Production Features
- **Security Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Strict-Transport-Security` (production).
- **Rate Limiting**: Sliding-window IP rate limiting (120 req/min).
- **Privacy & Compliance**: Cookie consent banner with granular preferences, user profile/session deletion, `robots.txt`, `sitemap.xml`, and custom `404.html`.
