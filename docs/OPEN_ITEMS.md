# Open Items & Unverified Constants (UAQA)

All constants and assumptions listed below are initialized with baseline literature heuristics and flagged with `TODO(verify)` per SRS B9 and B15 working rules.

| Item ID | Component | Current Value / Heuristic | Source / Reference | Verification Needed |
|---|---|---|---|---|
| VERIFY-01 | Inhalation rates (m3/h) | Adult rest: 0.5, light: 1.0, exercise: 2.0; Child rest: 0.3, light: 0.6, exercise: 1.2 | EPA Exposure Factors Handbook | Medical & epidemiological review for Indian context |
| VERIFY-02 | Mask effective reduction | N95 good fit: 75%, N95 poor: 40%, Surgical: 30%, Cloth: 15% | Literature heuristic on real-world fit | Clinical fit factor validation |
| VERIFY-03 | Cigarette equivalence | 22 µg/m³ PM2.5 24h avg ≈ 1 cigarette/day | Berkeley Earth | Labelled prominently as intuition comparison only |
| VERIFY-04 | Commute Emission factors | Petrol car: 0.17 kg CO2/km, 2W: 0.04, Bus: 0.07, Metro: 0.03 | ARAI / CPCB averages | Transit authority emission benchmarks |
| VERIFY-05 | CPCB Sub-index Breakpoints | CPCB standard 6-tier breakpoints | Central Pollution Control Board standard | Official gazette review |
| VERIFY-06 | Natural ventilation & CADR heuristic | ACH natural: 0.5 closed, 2.0 open; CADR heuristic 2/3 floor area | EPA / ASHRAE indoor air guidance | Building science peer check |
