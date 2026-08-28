# IZFIN — Master Project Status

> Canonical project handoff/status file for ChatGPT, Codex, and cross-device continuation.
> Read this file before making new changes.

## 1. Product Goal

IZFIN is being migrated from the mature Streamlit product to a Next.js + FastAPI web application.

**Approved direction: Streamlit Full Parity Migration.**

The existing Streamlit implementation is the product specification. Do **not** redesign the product from scratch. The web application must systematically preserve the useful Streamlit behavior, information hierarchy, and product meaning while using the new architecture.

Primary product references:

- `app2.py`
- `izfin_ui/`
- framework-neutral/domain logic in `izfin_services/`, `izfin_core/`, repositories

Approved product title/tagline:

**IZFIN | Akıllı Piyasa Kararları**

Do not reintroduce `Akıllı BIST Analizi`.

## 2. Non-Negotiable Rules

- Never touch `main`.
- Base feature work on `develop`.
- Use feature branch -> PR -> `develop`.
- Do not merge unless both relevant Python and Web CI gates are green.
- Keep Streamlit working in parallel until web parity is complete.
- Use TDD RED -> GREEN for fixes/features.
- Do not replace real financial data with mock/decorative financial data.
- Do not reimplement Python business calculations in React.
- Preserve auth recovery, retry boundaries, scan recovery, durable readiness, and the same-origin API proxy.
- Avoid repo-wide rescans unless genuinely necessary.
- Group related work into meaningful checkpoint-sized packages.
- User-facing progress is checkpoint-based, not PR-by-PR narration.

## 3. Current Architecture

### Frontend

- `web/` — Next.js App Router web client
- Vercel hosts the web frontend

### API / Services

- `izfin_api/` — FastAPI boundary
- `izfin_services/` — service layer
- `izfin_core/` — shared domain/core logic
- repositories / Firebase / Firestore where already established
- Cloud Run hosts the FastAPI backend

### Product Reference

- `app2.py` — Streamlit application remains operational
- `izfin_ui/` — Streamlit/product presentation modules and parity reference

## 4. Current Checkpoint

# PERFORMANCE FULL STREAMLIT PARITY — IMPLEMENTED, LIVE ACCEPTANCE PENDING

The user live-accepted **Projection full Streamlit parity** on 2026-08-28 and explicitly approved continuing to Performance.

Performance implementation now preserves the established Streamlit tracking and scorecard model while separating auth/data orchestration from presentation:

- `web/components/performance-page.tsx` owns authentication, period selection, refresh, loading/error state, and API fetching
- `web/components/performance-view.tsx` owns active/closed-position and scorecard presentation
- Python/FastAPI remain the owners of position aggregation, return statistics, target/stop hit calculations, historical interpretation, and scorecard calculations
- `web/lib/performance.ts` exposes the typed presentation contract only; React does not recompute financial metrics

Performance web parity now includes:

- active-position KPI strip and active-position history
- closed-position summary KPIs
- separate closed-period and unique-stock counts
- positive-close rate, average return, median return, median duration, TP1-hit rate, and stop-hit rate
- full closed-position table with entry/close prices, days held, max profit/drawdown, initial stop, initial TP1, and TP1/TP2/TP3/Stop markers
- closed-position drilldown
- most common close-reason summary
- best/worst historical interpretation and Python-owned commentary
- 20G / 60G / 120G scorecard selection
- small-sample warning
- aggregate scorecard metrics
- asset-level scorecard
- collapsible signal-level detail history
- benchmark-relative interpretation

Do **not** call Performance accepted until the user verifies the deployed `develop` journey live.

## 5. User-Reported / Accepted State

### A. Recovery — accepted for parity continuation

Projection can recover a completed scan, expose the real ticker selector, and load selected ticker context. Refresh/deep-link/new-account variants remain part of the final Stage 5 end-to-end recheck.

### B. Piyasa Merkezi responsibility cleanup — accepted

Piyasa Merkezi is a decision-summary page, not a scan/list/account-management page. Primary watchlist editing, universe construction, and scan configuration stay outside it.

### C. SMART SCAN + DETAILED ANALYSIS — live accepted 2026-08-28

The user verified the deployed flow and reported it looked correct overall.

Accepted behaviors include:

- real scan flow
- ticker selection in the decision motor
- Detailed Analysis opening with the selected ticker/job
- contextual Detailed Analysis route instead of Piyasa Merkezi being marked active
- structured technical analysis sections
- compact/collapsed score-depth section
- explicit return to Akıllı Tarama results
- global Streamlit-style `Nasıl Kullanılır?` guide
- browser/product title `IZFIN | Akıllı Piyasa Kararları`

### D. Projection — live accepted 2026-08-28

The user verified the deployed Projection screen and reported it appeared problem-free, then explicitly approved continuing.

Accepted checkpoint includes:

- completed-scan context recovery
- real ticker selector
- Streamlit 45-day model hierarchy
- ATR and historical-volatility model dimensions
- combined and wider risk bands
- confidence / agreement / scenario / direction context
- explicit model-scope disclosure

### E. Deferred low-priority scan selection behavior

When the user leaves Akıllı Tarama and later revisits it, the decision card can still fall back to the first ticker in the result table instead of the previously selected ticker.

**User decision on 2026-08-28: do not touch this now.** The real ticker selector keeps the flow usable, so this is deferred and must not block current parity work.

## 6. Latest Relevant Merges

### PR #95 — Analysis continuity

Merge commit: `6892be7c8a96e9b86e9dd000534e6f38b26430c8`

Typed scan context helpers, authenticated analysis context, scan -> shared-context publication, and Projection recovery foundations.

### PR #96 — stale cached analysis job recovery

Merge commit: `d9dcc62cee1a5e7aecfb13c0232f2a72962586f9`

Validated cached active scan context against authoritative server history.

### PR #98 — Projection recovery root fix + Piyasa Merkezi cleanup

Added authoritative projectable-ticker recovery, real Projection ticker selection, and removed misplaced Piyasa Merkezi controls/modules.

### PR #99–#102 — Smart Scan / Detailed Analysis parity

Added the stock decision motor, decision ticker selector, focused scan responsibility, completed-scan result recovery, and Python-owned structured technical analysis.

### PR #103 — Smart Scan / Detail continuity close

Merge commit: `907375ffd685ce6c6fc6d8ada02584e91d822007`

Added shared selected-ticker publication, Detail job/ticker context publication, return-to-scan continuity, and the approved product title.

### PR #104 — Detail contextual UX + usage guide

Merge commit: `2597f0fb77517eb1cf020fbe40a72e0f0869894e`

Made Detailed Analysis a contextual workspace route, collapsed score-depth by default, restored the Streamlit-style global `Nasıl Kullanılır?` guide, and improved return-context behavior.

### PR #105 — Projection full Streamlit parity

Completed the Projection presentation split and restored the Streamlit 45-day model hierarchy while keeping all financial calculations Python-owned.

### PR #106 — Performance full Streamlit parity

Current checkpoint PR. Restores the complete Streamlit closed-position surface, typed summary contract, focused presentation boundary, and keeps the existing scorecard behavior. Merge only after final CI is green.

## 7. Develop Preview

Canonical develop URL:

`https://izfin-web-git-develop-adopcin-7216.vercel.app`

Do not use one-off deployment URLs as the canonical user link unless debugging a specific deployment.

## 8. Work Order

Do not change this order without an explicit user decision.

1. Piyasa Merkezi functional parity — accepted for continuation
2. Detaylı Analiz functional parity — live accepted
3. Projeksiyon full Streamlit parity — live accepted
4. **Performans parity — current, implementation complete; live acceptance pending**
5. Strategy Lab parity
6. Account/Admin parity audit
7. Visual parity / responsive Streamlit-to-web translation
8. Full authenticated user journey / Stage 5 close
9. Stage 6 Mobile only after Stage 5 is accepted

## 9. Streamlit Full Parity Target by Screen

### Piyasa Merkezi

Reference: `izfin_ui/home_dashboard.py`, `app2.py`

Target:

- pulse / market state
- trend
- momentum
- money flow
- risk
- system comment
- top signals
- featured security
- movers
- decision-oriented hierarchy
- no primary watchlist editing or scan configuration

### Akıllı Tarama

Current state: live accepted for continuation.

Target/current product model:

- BIST 30
- BIST 100
- Kendi Listem
- symbol search/add/remove
- launch scan
- progress/recovery
- internal durable recovery; no separate visible history module
- results table
- selected-ticker decision motor below table
- why buy / why wait
- confidence / risk / MTF / entry quality / technical profile
- support / resistance / stop / targets
- continuity into Detailed Analysis / Projection

### Detaylı Analiz

Reference: `izfin_ui/detail_analysis.py`, `izfin_ui/analysis_views.py`

Current state: live accepted for continuation.

Includes:

- indicator/technical sections
- confidence and signal context
- risk context
- support/resistance
- MTF entry motor
- targets
- algorithmic interpretation
- Projection navigation
- contextual route/breadcrumb
- collapsed score detail

### Projeksiyon

Reference: `izfin_ui/projection_view.py`

Current state: live accepted 2026-08-28.

Includes:

- approximately 45-day model
- current price
- ATR movement
- historical volatility movement
- combined movement
- base / upside / downside bands
- wider risk band
- model confidence
- model agreement
- volatility explanation
- positive technical scenario
- negative technical scenario
- algorithmic direction summary
- no target-price promise / no investment-advice implication

### Performans

Reference: `izfin_ui/performance_view.py`

Current state: implementation complete; user live acceptance pending.

Includes:

- active positions
- closed-position history
- summary KPIs
- win rate / average / median where supported
- median duration
- best/worst interpretation
- most common close reasons
- full closed-position risk/target history
- 20G / 60G / 120G scorecards
- asset-level scorecard
- signal-level detail history
- small-sample warnings

### Strategy Lab

Reference: `izfin_ui/backtest_view.py`, `izfin_ui/backtest_results.py`

Target:

- symbol discovery
- parameter workflow
- historical strategy results
- explanatory context
- no fake data

### Account / Admin

Target:

- profile/legal/export/delete parity
- safe post-delete transition
- admin-only System Health / CI / release / readiness
- common product visual language

## 10. Technical Debt Snapshot

### Strong / relatively mature

- FastAPI boundary
- auth recovery
- 401 refresh/retry semantics
- 403 handling
- API retry/error boundaries
- same-origin API proxy
- scan job recovery foundations
- production readiness checks
- Firestore/durable readiness behavior
- CI gates
- Vercel/Cloud Run split

### Remaining web product debt

- incomplete Streamlit parity in Strategy Lab, Account/Admin, and final visual pass
- Performance live acceptance still pending
- generic/stacked CSS convergence layers
- final authenticated journey still needs one comprehensive acceptance pass
- some route/context coupling remains until all analysis surfaces use the same shared context consistently
- deferred scan decision-card selected-ticker revisit behavior noted above

### Debt reduced by current Performance checkpoint

- separated Performance auth/data orchestration from presentation
- replaced the loose frontend closed-summary shape with a typed presentation contract
- restored Streamlit information without duplicating Python financial calculations
- preserved real-data-only rendering
- kept scorecard and position-history responsibilities clearly separated

### Technical debt policy

- no unnecessary decorative features before functional parity
- no broad CSS polish before functional parity
- remove duplicate responsibilities instead of layering more UI
- prefer authoritative server state over browser-only state
- keep business calculations in Python
- each checkpoint should reduce, not increase, product-layer debt

## 11. Working Style / Communication

At checkpoint end, report only:

- **What works** — concrete verified behavior
- **What is missing** — remaining product gaps
- **What the user should test live** — exact Vercel actions
- **Technical debt trend** — increased / decreased / flat and why

Internally, PRs/tests/commits remain required, but they are not the user-facing progress model.

## 12. Codex Efficiency Rules

- Do not repeatedly scan the whole repository.
- Start from this file, the approved parity spec, and files directly relevant to the current checkpoint.
- Work checkpoint-by-checkpoint.
- Trace real data flow before applying fixes.
- If a fix fails repeatedly, reassess architecture instead of stacking workarounds.
- Preserve the explicit user decision not to spend time on the low-priority scan selection reset yet.

## 13. Canonical Next Action

**Live-verify Performance full Streamlit parity on Vercel `develop`.**

Acceptance journey:

1. Sign in and open **Performans** from the application navigation.
2. Confirm active-position KPIs and the active-position table load from real account data.
3. Confirm the closed-position summary shows separate closed-period and different-stock counts plus positive-close rate, average/median return, median duration, TP1-hit rate, and stop-hit rate.
4. Confirm the closed-position table includes entry and close prices, days held, max profit/drawdown, initial stop, initial TP1, and TP1/TP2/TP3/Stop markers.
5. Open a closed-position detail and confirm the period detail is coherent with the table row.
6. Confirm **En Sık Kapanış Nedenleri** and **IZFIN Geçmiş Performans Özeti** appear when the underlying data supports them.
7. Switch between **20G / 60G / 120G** and confirm scorecard metrics, asset-level table, and signal-level history update without affecting the position-history tables.
8. Confirm the small-sample warning appears when applicable, refresh the page, and verify account performance data recovers cleanly.

If the user accepts this journey, mark Performance complete and begin **Strategy Lab parity**. If live behavior differs from these expectations, treat it as a Performance checkpoint defect and fix it before advancing.
