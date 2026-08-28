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

# PROJECTION FULL STREAMLIT PARITY — IMPLEMENTED, LIVE ACCEPTANCE PENDING

The user live-accepted the **SMART SCAN + DETAILED ANALYSIS** checkpoint on 2026-08-28 and explicitly approved continuing.

Projection implementation now preserves the Streamlit 45-day model content while retaining the existing authenticated context recovery. The presentation is separated from context/auth/data fetching:

- `web/components/projection-page.tsx` owns auth, completed-scan recovery, explicit deep-link precedence, ticker resolution, loading/error states, and `fetchProjection`
- `web/components/projection-model-view.tsx` owns presentation only
- Python/FastAPI remain the owners of ATR, volatility, combined movement, bands, confidence, agreement, scenarios, and direction calculations

Projection web parity now includes:

- `IZFIN PROJECTION LAB`
- `Projeksiyon & Senaryo Analizi`
- `45G MODEL`
- `ATR + Tarihsel Volatilite`
- current price
- ATR model movement
- historical-volatility model movement
- combined movement
- 45G combined band
- wider risk band
- model confidence
- model agreement
- volatility explanation
- downside/base/upside model bands
- positive technical scenario
- negative technical scenario
- algorithmic direction summary
- support / resistance / stop / TP / model-difference context
- explicit model-scope / non-advice disclosure
- real ticker selector for multi-ticker completed scans

Do **not** call Projection accepted until the user verifies the deployed `develop` journey live.

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

### D. Deferred low-priority scan selection behavior

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

## 7. Develop Preview

Canonical develop URL:

`https://izfin-web-git-develop-adopcin-7216.vercel.app`

Do not use one-off deployment URLs as the canonical user link unless debugging a specific deployment.

## 8. Work Order

Do not change this order without an explicit user decision.

1. Piyasa Merkezi functional parity — accepted for continuation
2. Detaylı Analiz functional parity — live accepted
3. **Projeksiyon full Streamlit parity — current, live acceptance pending**
4. Performans parity
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

Current state: implementation complete; user live acceptance pending.

Required model content:

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

Target:

- active positions
- closed-position history
- summary KPIs
- win rate / average / median where supported
- median duration
- best/worst interpretation
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

- incomplete Streamlit parity in Performans, Strategy Lab, Account/Admin, and final visual pass
- generic/stacked CSS convergence layers
- final authenticated journey still needs one comprehensive acceptance pass
- some route/context coupling remains until all analysis surfaces use the same shared context consistently
- deferred scan decision-card selected-ticker revisit behavior noted above

### Debt reduced by current Projection checkpoint

- split auth/context/data resolution from projection presentation
- retained a typed API-owned model boundary
- kept financial calculations in Python
- removed pressure to duplicate ATR/volatility/scenario calculations in React
- made uncertainty/model-scope disclosure explicit
- preserved real-data-only rendering

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

**Live-verify Projection full Streamlit parity on Vercel `develop`.**

Acceptance journey:

1. Have a completed Akıllı Tarama available.
2. Open **Projeksiyon** from the sidebar.
3. Confirm the real completed-scan ticker resolves; if multiple valid tickers exist, switch between them.
4. Confirm `IZFIN PROJECTION LAB`, `Projeksiyon & Senaryo Analizi`, `45G MODEL`, and `ATR + Tarihsel Volatilite` are visible.
5. Confirm real data is populated for current price, ATR model, volatility model, combined movement, 45G combined band, wider risk band, confidence, agreement, model bands, technical scenarios, and algorithmic direction.
6. Switch ticker and confirm the model updates without leaving Projection.
7. Refresh Projection and confirm context is recovered.
8. Confirm the model-scope disclosure is visible and does not imply a guaranteed target price.

If the user accepts this journey, mark Projection complete and begin **Performans parity**. If live behavior differs from these expectations, treat it as a Projection checkpoint defect and fix it before advancing.
