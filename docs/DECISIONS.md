# Decision Log: Urban Air Quality Assistant (UAQA / SmogSense)

### DEC-001: Project Initial Setup & Dependency Strategy
- **Context:** The environment is Windows with Node.js v24.18.0 and Python 3.14.6 with extensive pre-installed packages (FastAPI 0.141, Pydantic 2.13, SQLAlchemy 2.1, Uvicorn, PyYAML, httpx, fakeredis, etc.). External npm registry access is blocked with 403 Forbidden by environment network policy.
- **Decision:** Build the backend (/apps/api) using the rich local Python environment. For the web client (/apps/web), build a zero-dependency, ultra-lightweight, high-performance vanilla TypeScript/ES module PWA or self-contained Next.js-equivalent client with standard web APIs that requires no external npm downloads, fully compliant with all UI screens, PWA specs, WCAG AA, and SRS B11.4 / B7 requirements.
- **Impact:** Allows instant, offline-capable development and verification without dependency on external npm package downloads.

### DEC-002: Monorepo Structure & Contract-First Design
- **Context:** SRS B16 specifies `/apps/api`, `/apps/web`, `/packages/shared`, `/data/kb`, `/eval`, `/docs`.
- **Decision:** Follow the repo layout strictly. Shared OpenAPI spec in `/packages/shared/openapi.yaml`, with domain configuration in YAML/JSON.
