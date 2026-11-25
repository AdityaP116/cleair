# UAQA SECOND-PASS AUDIT VALIDATION & EVIDENCE CHALLENGE
**Document Version:** 2.0-CHALLENGE  
**Date:** 2026-11-21  
**Assessment Type:** Adversarial Second-Pass Codebase & Empirical Evidence Audit  
**Target:** Urban Air Quality Assistant (UAQA)  

---

## 1. Executive Summary & Challenge Verdict

This second-pass audit was conducted to challenge the claims made in `UAQA_COMPLETE_TECHNICAL_AUDIT.md`. Rather than accepting previous findings at face value, every claim regarding test coverage, authentication, sensor security, database guarantees, and performance was subjected to empirical testing and adversarial probing.

### Verdict Revision:
- **Previous Verdict:** `READY FOR CONTROLLED PILOT`
- **Revised Verdict:** **`CONDITIONALLY READY — PILOT BLOCKED ON TWO REMEDIATIONS`**

### Summary of Challenged Claims:
1. **RBAC & Authorization Claim (CONTRADICTED):** The previous audit described the security posture as *"Medium (Conditional)"*. In reality, empirical probing revealed that **all institutional administrative mutations (`POST /v1/work-orders`, `POST /v1/alerts/rules`, status updates, and intervention recordings) can be executed completely unauthenticated (`HTTP 200/201 OK`) with zero credentials or session tokens.** Institutional RBAC (`InstitutionalUser`, `InstitutionalMembership`, and `RoleEnum`) exists in database models but is completely bypassed in route handlers.
2. **Exposed Simulator Credential (CONTRADICTED):** The previous audit classified the hardcoded key in `apps/web/app.js` as *"Low Severity Demo Key"*. Empirical verification revealed that **this key is an active, unrevoked live production credential in `cleair_dev.db` bound to sensor `c219888b-...` (`SN-PILOT-4B`)**. Anyone inspecting client-side source code can transmit arbitrary telemetry directly into the pilot school's database via `curl` or Python scripts.
3. **Database Idempotency with Nullable Sensor ID (CONTRADICTED):** The previous claim that composite uniqueness guarantees idempotency is structurally flawed when `sensor_id` is `NULL`. By SQL standard (and SQLite/PostgreSQL specification), `NULL != NULL`. If a sensor is decommissioned and its readings' `sensor_id` is set to `NULL`, the `UNIQUE(sensor_id, idempotency_key)` constraint ceases to prevent duplicate rows.
4. **Sub-Millisecond Query Latency Claim (NOT VERIFIED / REFUTED):** The previous audit asserted *"sub-millisecond query latency"*. Actual empirical measurements of the running Uvicorn server over local loopback revealed latencies between **$19.04\text{ ms}$ and $86.40\text{ ms}$**, an order of magnitude higher than claimed. No formal load benchmark exists.
5. **PostgreSQL Compatibility Claim (NOT VERIFIED):** PostgreSQL portability has never been executed or tested in CI. The project has only run on SQLite with in-memory test engines.

---

## 2. Test Suite Validation & Verification

### 2.1 Backend Test Suite Rerun (`backend/tests`)
- **Command:** `cmd.exe /c "set PYTHONPATH=backend && python -m pytest backend/tests -v --cov=app --cov-report=term-missing"`
- **Environment:** Windows, Python 3.14.6, pytest-9.1.1, pluggy-1.6.0.
- **Discovered:** 18 tests.
- **Passed:** 18 (100%).
- **Failed:** 0.
- **Skipped:** 0.
- **Execution Duration:** 10.93 seconds.
- **Overall Statement Coverage:** **84%** (1,557 statements, 244 missed).

#### Critical Module Coverage Gaps Identified:
While overall coverage is 84%, several core modules have dangerously low coverage:
- `backend/app/api/dependencies.py`: **31% coverage** (Lines 7–19 unexercised in production configuration; auth logic unverified).
- `backend/app/modules/air_quality/calculator.py`: **12% coverage** (23 lines missed; CPCB multi-pollutant sub-index math largely untested in backend directory).
- `backend/app/modules/air_quality/quality_checker.py`: **17% coverage** (15 lines missed; data QA routines untested).
- `backend/app/repositories/memory.py`: **37% coverage** (27 lines missed; in-memory user repository unverified).
- `backend/app/modules/ai/orchestrator.py`: **38% coverage** (AI fallback routines untested).

### 2.2 Legacy B2C Test Suite Rerun (`apps/api/app/tests`)
- **Command:** `cmd.exe /c "set PYTHONPATH=apps/api && python -m pytest apps/api/app/tests --cov=apps/api/app --cov-report=term-missing"`
- **Discovered:** 11 tests.
- **Passed:** 11 (100%).
- **Failed:** 0.
- **Execution Duration:** 0.90 seconds.
- **Overall Coverage:** **60%** (369 statements, 147 missed).
- **Core Coverage:** `guardrail_service.py` (93%), `impact_service.py` (93%), `rules_service.py` (92%).

---

## 3. Authentication & RBAC Investigation

### 3.1 Empirical Probing Findings
An adversarial probe was conducted against the running application without providing any authorization header, cookie, or session token:

1. **Probe 1: Unauthenticated Alert Rule Creation**
   - **Request:** `POST http://127.0.0.1:8000/v1/alerts/rules` with `{ name: "Malicious Unauth Rule", measurement_type: "PM2.5", threshold_value: 1.0 }`.
   - **Result:** **`HTTP 200 OK`**. The backend accepted and committed the operational alert rule without requiring user authentication.
2. **Probe 2: Unauthenticated Work Order Dispatch**
   - **Request:** `POST http://127.0.0.1:8000/v1/work-orders` with `{ title: "Unauthenticated Mutation Probe", priority: "HIGH" }`.
   - **Result:** **`HTTP 201 Created`**. The work order was assigned and recorded in the database.
3. **Probe 3: Unauthenticated Report & Telemetry Dump**
   - **Request:** `GET http://127.0.0.1:8000/v1/reports/site/9fa57ccf-89a3-4f44-bae2-625cb3a6c317/export/csv`.
   - **Result:** **`HTTP 200 OK`**. Entire raw historical sensor reading dump exported with no credentials.

### 3.2 Root Cause Analysis
In `backend/app/api/dependencies.py`:
```python
async def get_current_user_id(x_session_token: Optional[str] = Header(None)) -> str:
    if not x_session_token:
        # Default anonymous test user
        token = "default-session"
        user_id = "default-user"
        if not repo.get_user_id_by_token(token):
            repo.create_session(token, user_id)
        return user_id
```
- **Finding:** Any client omitting `x_session_token` is silently granted identity `default-user`.
- **Finding:** In `work_orders.py`, `alerts.py`, and `facilities.py`, route functions take `db: Session = Depends(get_db)` but **do not inject `get_current_user_id` or any role validator**.
- **Impact:** **CRITICAL**. Role-Based Access Control (`ADMIN`, `FACILITY_STAFF`, `VIEWER`) is non-existent at the API boundary. The UI presents role tags (`Operator (Role: ADMIN)`), but backend routes enforce zero role checks.

---

## 4. Exposed Sensor Credential Investigation

### 4.1 Repository Evidence
In `apps/web/app.js` (Lines 333–338):
```javascript
const res = await fetch(`${API_BASE}/telemetry/ingest`, {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "x-sensor-key": "sq_live_fbac4e84_..." // [REDACTED SECRET]
    },
    body: JSON.stringify(payload)
});
```

### 4.2 Database Cross-Check
Querying `cleair_dev.db`:
- Active sensor: `SN-PILOT-4B` (`c219888b-ab35-400c-8eeb-ee3a042bd533`).
- Credential record: `key_prefix = 'fbac4e84'`, `is_active = 1`, `is_revoked = 0`.
- **Empirical Probe:** Executing `POST /v1/telemetry/ingest` with the client-side credential and a payload with `PM2.5 = 99.9` returned:
  ```json
  HTTP 200 OK: {"success": true, "sensor_id": "c219888b-ab35-400c-8eeb-ee3a042bd533", "readings_recorded": 1}
  ```
- **Finding:** **CRITICAL**. The credential embedded in `app.js` is a live, valid authentication secret for Classroom 4B's sensor. Any visitor to the website can extract this key from client source code and inject arbitrary false telemetry into the school's historical records.

---

## 5. Database & Data Integrity Claims Challenge

| Audit Claim | Claimed Status | Empirical Finding | Corrected Classification |
|---|---|---|---|
| **Idempotency Guarantee** | Complete | Composite unique constraint `(sensor_id, idempotency_key)` works when `sensor_id` is populated. Resubmitting duplicate packet returned `was_duplicate: true`. | **PARTIALLY CONFIRMED** |
| **Idempotency with Nullable Sensor ID** | Complete | **FAILED**. When a sensor is deleted and `sensor_id` is set to `NULL`, SQLite and PostgreSQL allow infinite rows with `(NULL, "key-01")`. Uniqueness is broken for unlinked/historical readings. | **CONTRADICTED** |
| **Soft Deletion Preserves Data** | Complete | Confirmed via `test_soft_delete_preserves_telemetry`. Deleting sites/zones leaves `sensor_readings` intact with `NULL` foreign keys. | **CONFIRMED** |
| **PostgreSQL Compatibility** | Verified | **No PostgreSQL instance has ever been tested.** `asyncpg` was rejected earlier due to Python 3.14 greenlet issues. Portability is theoretical. | **NOT VERIFIED** |

---

## 6. Environmental Logic & Thresholds Audit

### 6.1 Hardcoded vs. Configurable Thresholds
- **Alert Rules (`alert_rules` table):** Configurable. Thresholds ($PM_{2.5} > 60$, $CO_2 > 1000$) are persisted as rows and can be adjusted per site or zone.
- **Frontend Hardcoded Strings:** In `index.html` and `app.js`, several target benchmarks are hardcoded in template cards (`Target ≤ 60 µg/m³`, `Target ≤ 1000 ppm`), meaning if an administrator adjusts a rule to $80\ \mu\text{g/m}^3$, the UI metric cards will still display `Target ≤ 60`.
- **Pollutant Independence:** Verified. $PM_{2.5}$ (particulate matter) and $CO_2$ (ventilation/metabolic exhalation) are treated as strictly distinct parameters.
- **CPCB Regulatory AQI Separation:** Verified. Outdoor CPCB AQI breakpoints are separated from instantaneous indoor microclimate monitoring.

---

## 7. Performance & Latency Claims Challenge

### 7.1 Empirical Latency Benchmarks
The previous audit claimed:
> *"SQLite generates < 2 MB/month of telemetry with sub-millisecond query latency."*

### 7.2 Empirical Evidence
Repeated HTTP requests to `GET /v1/facilities/sites/9fa57ccf-89a3-4f44-bae2-625cb3a6c317/zones` on localhost measured:
- Run 1: **$86.40\text{ ms}$**
- Run 2: **$27.24\text{ ms}$**
- Run 3: **$19.04\text{ ms}$**
- Run 4: **$24.69\text{ ms}$**
- Run 5: **$23.96\text{ ms}$**
- **Finding:** The claim of *"sub-millisecond query latency"* is **REFUTED / CONTRADICTED**. Real-world request-response latency on the development machine is between $20\text{ ms}$ and $86\text{ ms}$. No load-testing benchmarks exist for concurrent write throughput.

---

## 8. Second-Pass Findings Register & Remediation Matrix

| Finding ID | Previous Severity | Revised Severity | Status | Problem Statement & Impact | Required Remediation |
|---|---|---|---|---|---|
| **AUD2-SEC-01** | Medium | **CRITICAL** | **CONTRADICTED** | Administrative routes (`work-orders`, `alerts/rules`) have no authentication dependency. Any anonymous user can dispatch work orders, acknowledge alerts, or alter threshold rules. | Remove anonymous fallback; implement strict `Depends(require_institutional_user)` and enforce `RoleEnum` checks. |
| **AUD2-SEC-02** | Low | **HIGH** | **CONTRADICTED** | Live sensor secret is hardcoded in client-side `apps/web/app.js`. Anyone can forge Classroom 4B telemetry packets. | Revoke key `sq_live_fbac4e84_...`. Move simulator to dedicated `/v1/telemetry/simulate` backend endpoint that does not expose hardware ingestion keys. |
| **AUD2-DB-01** | Pass | **MEDIUM** | **CONTRADICTED** | Unique constraint `(sensor_id, idempotency_key)` fails to enforce uniqueness when `sensor_id IS NULL`. | Add a non-nullable synthetic ingestion token or enforce site-level idempotency key uniqueness `UNIQUE(site_id, idempotency_key)`. |
| **AUD2-PERF-01** | Pass | **LOW** | **REFUTED** | Unverified sub-millisecond latency claims. | Retract unverified performance claims; benchmark under simulated concurrent sensor writes. |
| **AUD2-COV-01** | Pass | **MEDIUM** | **PARTIALLY CONFIRMED** | `calculator.py` (12%) and `dependencies.py` (31%) have critical coverage gaps. | Add unit tests specifically exercising CPCB sub-index math and authentication dependency branches. |

---

## 9. Revised Engineering Verdict

### **`CONDITIONALLY READY — PILOT BLOCKED ON TWO REMEDIATIONS`**

**Grounds for Blocking:**
While the core domain algorithms, database soft-deletion, and user interface workflows are genuinely functional, the pilot **cannot be deployed to a real institution in its current state** due to two immediate operational risks:

1. **Unauthenticated Mutations:** Any student or visitor on the school network could issue `POST /v1/alerts/rules` or `POST /v1/work-orders` and tamper with campus operational records.
2. **Exposed Hardware Credential:** The simulator client leaks Classroom 4B's active secret key in plaintext JavaScript.

### Mandatory Pre-Pilot Gate:
To unblock pilot deployment, the following two tasks must be completed and verified:
1. Enforce authentication on all institutional mutation endpoints.
2. Revoke the exposed sensor credential and replace client-side key transmission with a sandboxed backend simulation route.
