# Stage 1 Report: Frontend & Core Safety Engine

## Summary
Completed full architecture scaffolding, contract-first OpenAPI 3.0 specification (`/packages/shared/openapi.yaml`), complete mobile-first responsive PWA frontend (`/apps/web`), and verified deterministic rule engine, impact calculator, RAG starter knowledge base, and safety guardrails. All 11 unit & golden benchmark tests passed with 100% success.

## What was built
- **FR-ING-01..09, FR-RUL-01..04 (SRS B8):** Deterministic safety rule engine mapping CPCB AQI categories x vulnerability flags to advice levels (`NORMAL`, `CAUTION`, `HIGH`, `SEVERE`, `EMERGENCY`). Mandatory action templates pre-translated in `en`, `hi`, `mr`.
- **FR-IMP-01..05 (SRS B9):** Pure, deterministic Impact Calculator implementing `IMP-MASK-01`, `IMP-PURIFIER-01` (single-zone mass balance), `IMP-COMMUTE-01`, `IMP-CIG-01` (Berkeley Earth equivalence with mandatory disclaimer), and `calc_clean_air_score` (FR-DSH-02).
- **SR-01..07 (SRS B12):** Output guardrail blocking severity downgrades, banned "safe to go out" phrases at `level >= HIGH`, and medication/dosage mentions. Immediate symptom escalation trigger for respiratory distress.
- **FR-RAG-01..04 (SRS B10):** Starter curated corpus with official WHO, CPCB, CAQM/GRAP, and EPA sources.
- **FR-PRO-01..05, FR-PRV-01..04 (SRS B4.2, B4.10):** Profile onboarding with vulnerability checkboxes, coarse location by default, data export, and one-tap delete.
- **Frontend PWA (F1-F6):** Mobile-first responsive interface with live AQI risk card, 3 actionable recommendations, interactive scenario switcher (5 demo states), daily timeline, AI assistant chat, and impact analytics dashboard.

## Exit gate results
- [x] Monorepo directories created (`/apps/web`, `/apps/api`, `/packages/shared`, `/data/kb`, `/eval`, `/docs`).
- [x] OpenAPI 3.0 YAML spec covering all SRS B7 endpoints and B11.4 agent schemas written in `/packages/shared/openapi.yaml`.
- [x] TypeScript interfaces defined in `/packages/shared/types.ts`.
- [x] Full UI screens implemented in `/apps/web` (Home, Daily Plan, Assistant Chat, Impact Dashboard, Profile Onboarding, Privacy Center).
- [x] Scenario switcher supports all 5 key AQI and vulnerability states.
- [x] 11/11 pytest test cases pass cleanly (Rules, Impact monotonicity, Guardrail enforcement, Golden set benchmarks).

## Deviations from spec
- Logged in `docs/DECISIONS.md`: Built zero-external-npm client bundle to ensure 100% offline reliability in restricted build environments while strictly honoring WCAG AA and responsive PWA standards.

## Unverified items (TODO(verify))
- Listed in `docs/OPEN_ITEMS.md`: Inhalation rates, mask real-world fit factors, Berkeley Earth cigarette equivalence heuristic, and commute emission factors.

## Commands to run, test, and demo
1. **Run tests:**
   ```powershell
   $env:PYTHONPATH="apps/api"; python -m pytest apps/api/app/tests -v
   ```
2. **Start API:**
   ```powershell
   $env:PYTHONPATH="apps/api"; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. **Open UI:** Open `apps/web/index.html` in any web browser.

## Hand-off notes for the next stage
Core contracts and services are validated and in place. Ready to proceed to Stage 2 backend hardening or Stage 3 live integration as requested.
