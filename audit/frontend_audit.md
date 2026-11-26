# Cleair (UAQA) — Frontend Design & UX Audit Report

## 1. Executive Summary
- **Honest Diagnosis:** The frontend (`apps/web/index.html`) looks like an **AI-generated SaaS admin template** because it drops a first-time family user straight into a dense institutional sidebar + KPI grid with **no dedicated landing page**, uses generic `Manrope` + `JetBrains Mono` + `Material Symbols` styling, relies on uniform `rounded-xl border border-border-subtle shadow-sm` cards, and buries the product's core differentiator (*"what should my family do today and why?"*) behind institutional jargon (*"Operational Target"*, *"Pilot Node Live"*, *"Diurnal Pattern"*).
- **Top 5 Issues:**
  1. **`FE-001` (P0):** No landing page exists—`/` immediately loads the institutional dashboard.
  2. **`FE-002` (P1):** Runtime dependency on `https://cdn.tailwindcss.com` (slow on mid-range Android / Slow 4G, unpurged).
  3. **`FE-003` (P1):** Institutional vs. Family identity split—the UI speaks like a facility compliance tool (*"St. Xavier's Academic Complex"*, *"Work Orders"*) rather than a warm, calm family smog assistant.
  4. **`FE-004` (P1):** No visible family-profile onboarding or per-person guidance (child, elderly, asthma, commute) on the main screen.
  5. **`FE-005` (P2):** Chart (`#trendSvgCanvas`) is a static SVG with hardcoded points (`08:00 AM` to `Current`) and no real data binding or annotations.
- **Verdicts:** **Landing Page:** `0/10` (Missing). **Dashboard:** `5.5/10` (Functional institutional layout, but generic and poorly tailored for non-technical families).

---

## 2. Baseline
- **Pages / Views in `apps/web/index.html`:** Single-page app with 8 hashless tab views (`facility`, `zones`, `alerts`, `workorders`, `telemetry`, `chat`, `outdoor`, `privacy`).
- **Screenshots & Lighthouse:** *Not measured* (`playwright` / `lighthouse` CLI not installed in this environment).
- **Actual Design Tokens in Use (`apps/web/index.html:10-46`):**
  - **Fonts:** `Manrope` (400–800), `JetBrains Mono` (400–600).
  - **Colors:** `#0E3B36` (deep-teal), `#2DD4BF` (mint-green), `#0F766E` (mint-dark), `#F4F8F6` (ground-soft), `#E2ECE7` (border-subtle), `#102A26` (text-primary), `#425E59` (text-secondary), `#D97706` (aqi-moderate), `#EA580C` (aqi-poor), `#DC2626` (aqi-very-poor).
  - **Radii & Shadows:** Uniform `rounded-xl` / `rounded-lg` + `shadow-sm` on almost every container.

---

## 3. "AI-Generated Look" Diagnosis

| Tell | Status | Evidence | Severity |
|---|---|---|---|
| **Uniform rounded cards on soft grey** | **Present** | Every section in `index.html` uses `bg-light-surface rounded-xl p-6 border border-border-subtle shadow-sm` | **High** |
| **Dashboard = identical KPI grid + 1 chart + sidebar** | **Present** | `w-64` sidebar + 4-col KPI box + 1 SVG chart + 4-col zone cards (`index.html:180-265`) | **High** |
| **Corporate/AI buzzword copy** | **Present** | `"Operational Guidance"`, `"Diurnal Pattern"`, `"Classroom Microclimate Trajectory"` | **High** |
| **Static/unannotated chart** | **Present** | `renderTrendChart()` in `app.js` plots hardcoded coordinates, not live history | **Med** |
| **Generic stock icon set** | **Present** | `Material Symbols Outlined` used decoratively in every card header | **Med** |

---

## 4. Landing Page Scorecard (2.1–2.7) — **0 / 10 (Missing)**
There is **no landing page** at `/`. A stranger visiting `/` sees an internal facility dashboard (`St. Xavier's Academic Complex`, `Work Orders`, `IoT Sensor Feed`).

### 5 Rewritten Copy Lines (Human, Smog-Specific, Honest)
1. **Hero Headline:** *"Smog is bad today. Here is what your family should actually do."*
2. **Subhead:** *"Live local AQI, honest indoor air hacks, and commute protection tailored to your home, kids, and budget—without the panic."*
3. **Primary CTA:** *"Check Today's Plan for My Area"*
4. **Feature Line:** *"No purifier? Get free and low-cost ways to cut indoor dust and smoke by sealing peak-hour drafts and timing ventilation."*
5. **Footer Tagline:** *"Built for Indian cities. Grounded in CPCB/Open-Meteo data and transparent math—never medical advice."*

---

## 5. Dashboard Scorecard (3.1–3.7)
- **3.1 Hierarchy (5/10):** The eye lands on 4 equal-weight numbers (`38.4`, `720`, `58.5`, `1 / 4`) before seeing *what to do*. Action should be #1.
- **3.2 Information Design (5/10):** `provenance` is shown, but the trend chart is hardcoded and lacks annotations.
- **3.3 Personalisation (3/10):** No visible family profile strip (child/elderly/asthma/commute) on the main dashboard; chat is in a separate tab.
- **3.4 Layout & Components (6/10):** Consistent Stitch palette, but monotonous card grid.
- **3.5 Emotional & Safety Design (6/10):** Calm teal palette avoids panic, but 112 emergency guidance is not surfaced on the main view.
- **3.6–3.7 Mobile & Community (4/10):** Desktop-first sidebar (`w-64`); no apartment-society/community mode tab yet.

---

## 6. Prioritised Findings List
- **`FE-001` (P0, Landing, L):** No landing page at `/`. Fix: Create a focused, action-first landing section above or before the dashboard with instant city lookup.
- **`FE-002` (P1, Global, M):** `cdn.tailwindcss.com` runtime script (`index.html:9`) slows mobile load. Fix: Replace with pre-built/purged CSS.
- **`FE-003` (P1, Dashboard, M):** Action is secondary to KPI numbers. Fix: Put *"Today's 3 Actions for Your Family"* at the top of the viewport.
- **`FE-004` (P1, Dashboard, M):** No family profile selector or community mode tab. Fix: Add a compact *"Who's at home?"* strip + Community Checklist tab.
- **`FE-005` (P2, Dashboard, S):** Hardcoded trend chart in `app.js`. Fix: Bind to `/v1/air/forecast` or label clearly as illustrative.

---

## 7. Three Redesign Directions (Pick One)

### Direction A: **"Morning Weather Bulletin" (Editorial / Calm Utility)**
- **Concept:** Looks like a crisp, high-contrast daily air bulletin (inspired by *The Hindu* / *NYT Weather*), not a SaaS admin panel.
- **Typography:** `Fraunces` (editorial serif for headlines) + `Plus Jakarta Sans` (body) + `Noto Sans Devanagari`.
- **Palette:** Warm paper `#FAF8F5`, deep ink `#14211E`, terracotta alert `#C2410C`, sage safe `#15803D`.
- **Signature Element:** *"Today's Safe Window"* timeline bar showing exact hours to open windows or walk outside.

### Direction B: **"Haze & Horizon" (Atmospheric / Visual Storytelling)**
- **Concept:** A subtle atmospheric header whose visual clarity/haze shifts with local AQI, paired with a *"What changes → By how much"* impact ledger.
- **Typography:** `Instrument Serif` + `Inter` + `Noto Sans Devanagari`.
- **Palette:** Slate sky `#F1F5F9`, deep navy `#0F172A`, amber haze `#D97706`.
- **Signature Element:** Side-by-side *"Outdoor vs. Inside Your Home"* visual comparison card.

### Direction C: **"Family Health Card" (Mobile-First Action Deck)**
- **Concept:** Built for 375px Android phones first—large, thumb-friendly action cards grouped by family member (*Kids*, *Elderly*, *Commuter*), zero sidebar.
- **Typography:** `Plus Jakarta Sans` + `JetBrains Mono` + `Noto Sans Devanagari`.
- **Palette:** Crisp white `#FFFFFF`, deep teal `#0E3B36`, warm sand `#F5F2EB`.
- **Signature Element:** Per-person guidance strip at the top of the screen.

**Recommendation:** **Combine Direction A + Direction C** — adopt the calm, editorial *"Morning Bulletin"* hierarchy and typography from **A** with the mobile-first, per-person family action cards from **C**, keeping the existing `#0E3B36` deep teal + `#F4F8F6` palette.

---

## 8. Quick Wins (< 2 Hours)
1. Replace generic card headers (*"Operational Guidance"*, *"Diurnal Pattern"*) with plain human language (*"What to do today"*, *"Best hours to step outside"*).
2. Add a 1-click **"Check My City"** bar + **3-card Family Action Strip** at the top of the Overview.
3. Surface the **112 Emergency & Doctor Disclaimer** cleanly in the footer/header.
