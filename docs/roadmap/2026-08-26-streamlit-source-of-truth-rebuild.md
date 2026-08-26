# IZFIN Streamlit source-of-truth rebuild

_Created: 2026-08-26 · source inspected: `app2.py`, `styles/izfin.css`, and `izfin_ui/*`_

## Non-negotiable rule

The existing Streamlit product is the functional and visual source of truth. The web client must reproduce its workflows with the existing FastAPI/Firebase contracts; it must not replace a missing port with a new score, prediction, comparison, or trading feature.

## Product language to preserve

- Deep navy surfaces, cyan/blue signature actions, teal positive states, amber caution, and red risk states.
- Dense but legible decision-support cards: heading, KPI row, explanation, risk/limitations, then a concrete next action.
- The approved IZFIN mark, `ANALYZE · PREDICT · INVEST` brand language, Turkish product copy, and explicit investment-risk disclosures.
- Responsive layouts must preserve hierarchy rather than reduce the product to a generic form.

## Source-screen inventory

| Streamlit source | Required web outcome | Current audit status |
| --- | --- | --- |
| Auth, registration, captcha, consent gate, Google, reset, email verification | Dedicated entry routes and explicit legal flow | Contract present; visual parity and Google first-run consent must be accepted-tested. |
| Sidebar brand, navigation, user/status, logout | Shared responsive shell with approved logo and the same six user areas | Routes present; visual language must be rebuilt from source tokens. |
| Market bar, decision centre, top signals, movers, best setup, scan CTA | A real home decision centre driven only by existing market/scan responses | APIs exist; web presentation is materially shallower than the Streamlit source. |
| Personal-list search/autocomplete, add/remove, preset profile, active universe, selection summary, scan overlay | Full Smart Scan workspace with search, persistent list, profile, progress, filters and results | Core jobs and list are present; autocomplete, richer selection UX, focus table mode, decision explainers and result-detail parity remain. |
| Result KPIs, four filters, sortable wide table, skipped-data notes, score/decision detail | Result-first scan experience and job-scoped detail without invented calculations | Table/filter/detail route exists; source reading aids and wide-table behaviour require porting. |
| 45-day ATR/historical-volatility projection, primary/secondary metrics, direction scenarios and disclosure | Same scenario model and explicit limitations | Existing projection API/UI is the source; compare response fields during acceptance. |
| Active positions, refresh, history maintenance, closed positions, scorecard horizons and small-sample warning | Same performance lifecycle and visible data states | Read views exist; source actions and table/detail parity must be contract-tested. |
| Daily Core backtest, ticker search, 3/5/10y selector, KPI, summary/detail tables and reading notes | Same strategy-lab lifecycle, not a different backtest | Core endpoint/UI exists; external ticker/search and reading-table acceptance remain. |
| Privacy, terms, consent, export, deletion and admin health | Existing protected operations with clear states | Contracts/routes exist; signed-in acceptance remains required. |

## Rebuild order

1. **Shared source design system and shell** — port cyan/blue token hierarchy, brand placement, card/table/action language; remove generic dashboard treatment.
2. **Market Centre + Smart Scan parity** — make the primary workflow visually and functionally match the Streamlit source, including source-backed missing interactions.
3. **Detail + Projection parity** — preserve all returned decision, score, risk and scenario explanation fields.
4. **Performance + Strategy parity** — port source lifecycle actions, tables, maintenance/warning disclosures and results reading.
5. **Identity + Account acceptance** — exercise registration, legal consent, Google first-run handling, export and deletion against FastAPI/Firebase.
6. **Release acceptance** — signed-in and signed-out desktop/mobile journeys against Cloud Run; every unavailable state remains explicit.

## Completion evidence required for each package

- A source-to-web mapping in tests or a contract test; no fabricated market output.
- Focused tests, full pytest, TypeScript check, production build, Python compile and diff check.
- GitHub PR CI green before merge and `develop` CI green after merge.
- Main is never a target.

