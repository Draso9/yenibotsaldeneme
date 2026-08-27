# Streamlit Full Parity Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deployable IZFIN web product that preserves the mature Streamlit product’s real behavior, information hierarchy, and command-center visual language; begin mobile only after the web parity acceptance journey is complete.

**Architecture:** `app2.py` and `izfin_ui/` are the product specification. Next.js renders the same screen responsibilities and calls FastAPI only for authenticated, real data; FastAPI remains the only place for Python business calculations. Work progresses in complete vertical screen slices, not infrastructure or decorative-feature slices.

**Tech Stack:** Streamlit reference (`app2.py`, `izfin_ui/`), Next.js App Router/TypeScript, FastAPI/Python, Firebase auth, Firestore-backed scan state, Cloud Run, Vercel.

**Spec:** `IZFIN_MASTER_STATUS.md`

## Global Constraints

- Never touch `main`; every implementation checkpoint starts from `develop` and lands through a PR.
- Streamlit stays operational and is the canonical behavior and visual reference until web parity is accepted.
- Do not create new product features, mock financial data, or React copies of Python calculations.
- Each task follows TDD RED → GREEN, runs focused tests first, then the relevant Python and web gates before merge.
- Keep PRs checkpoint-sized: a coherent screen slice with its directly required API contract, not unrelated cleanup.
- Recovery continuation was accepted by the user on 2026-08-27 after the stable `develop` preview showed the real Projection ticker selector and loaded the selected ticker; retain refresh/deep-link/new-account variants in the final authenticated journey recheck.
- Mobile work starts only after the authenticated web journey is accepted; reuse the approved web screen contract and API rather than starting a second design effort.

---

## Parity map and checkpoint boundaries

| Checkpoint | Streamlit reference | Web surface | Done only when |
|---|---|---|---|
| 0. Recovery acceptance | `projection_view.py`, `home_dashboard.py` | `/projection`, `/` | User verifies recovery and uncluttered Piyasa Merkezi live. |
| 1. Market Center | `home_dashboard.py`, `market_bar.py` | `/`, `MarketCenterPanel` | A completed scan produces the same decision summary, top signals, featured ticker, movers, and correct empty states. |
| 2. Smart Scan + Detailed Analysis | `scan_page_view.py`, `scan_results.py`, `scan_table.py`, `detail_analysis.py`, `analysis_views.py` | `/scan`, `/stocks/[ticker]` | Universe, internal scan recovery/result table, and full detail decision/technical context connect through real scan jobs; no separate visible history module. |
| 3. Projection + Performance | `projection_view.py`, `performance_view.py` | `/projection`, `/performance` | The existing recovery flow is retained and each Streamlit projection/performance information block is real-data-backed. |
| 4. Strategy + Account/Admin audit | `backtest_view.py`, `backtest_results.py`, `legal_account_view.py`, `qa_view.py` | `/strategy-lab`, `/account`, `/admin/quality` | Every remaining Streamlit user/admin route has a web owner, real data, role protection, and no duplicate responsibility. |
| 5. Visual + responsive acceptance | all referenced screens | all web routes | Desktop and narrow-screen layouts preserve the Streamlit command-center hierarchy; full authenticated web journey is accepted. |
| 6. Mobile release plan | accepted web contracts | mobile client | Separate plan after Checkpoint 5 only. |

## Task 0: Accept the Recovery baseline

**Files:**
- Reference: `IZFIN_MASTER_STATUS.md`
- Verify: stable `develop` preview

**Consumes:** merged Recovery behavior: authoritative completed scan history, `projectable_tickers`, Projection deep links, and uncluttered Piyasa Merkezi.

**Produces:** a user-accepted baseline that permits the next Streamlit parity checkpoint.

- [ ] **Step 1: Run the live accepted-scan journey**

Open `https://izfin-web-git-develop-adopcin-7216.vercel.app`, sign in, open or complete a scan, then use the sidebar’s **Projeksiyon** route.

- [ ] **Step 2: Verify the recovered projection outcome**

For one valid technical-panel ticker, verify Projection opens directly. For multiple valid tickers, verify the selector is populated. Refresh once and verify the valid context reconstructs. For no technical-panel ticker, verify the explicit no-technical-data message rather than a generic context error.

- [ ] **Step 3: Verify the Market Center boundary**

Open `/` and confirm it contains decision summary/market content only; scan configuration, watchlist editing, account/auth blocks, and roadmap launch blocks do not appear there.

- [ ] **Step 4: Record checkpoint-only result**

Report only what works, remaining product gaps, exact next live test, and technical-debt trend. If any live step fails, create a narrowly scoped RED regression test for the failed boundary before changing code.

## Task 1: Finish Piyasa Merkezi functional parity

**Files:**
- Reference: `izfin_ui/home_dashboard.py`, `izfin_ui/market_bar.py`, `app2.py`
- Modify: `web/components/home-decision-center.tsx`
- Modify: `web/components/market-center.tsx`
- Modify only if data is absent: the directly corresponding `izfin_api/` market-center schema/router/service files
- Test: `tests/test_web_market_center_recovery_cleanup.py` and focused market-center API/component contract tests

**Consumes:** latest completed real scan job plus existing market-center API response.

**Produces:** a decision-only Piyasa Merkezi with pulse, trend, momentum, money flow, risk, system comment, top signals, featured ticker, movers, and Streamlit-equivalent loading/empty states.

- [ ] **Step 1: Write failing parity tests**

Add focused assertions for the Streamlit fields that must be present in the web response/render contract: `pulse`, `trend`, `momentum`, `flow`, `risk`, system comment, top signals, featured ticker, and movers. Add an empty-result assertion that contains no watchlist editor or scan configuration.

- [ ] **Step 2: Run only the new market-center tests**

Run the exact new test selectors and confirm the expected missing field/render assertion fails before implementation.

- [ ] **Step 3: Implement the smallest contract/render gap**

Expose a missing value only by adapting the existing Python home-dashboard calculation; render it in `HomeDecisionCenter` or `MarketCenterPanel` with the corresponding Streamlit label and real source disclosure. Do not add a new dashboard, client-side financial calculation, or watchlist control.

- [ ] **Step 4: Verify GREEN and commit the checkpoint slice**

Run focused Python tests, web typecheck, and the Market Center test file; commit only the involved screen/API/tests.

## Task 2: Finish Smart Scan and Detailed Analysis as one real-data flow

**Files:**
- Reference: `izfin_ui/scan_page_view.py`, `izfin_ui/scan_results.py`, `izfin_ui/scan_table.py`, `izfin_ui/detail_analysis.py`, `izfin_ui/analysis_views.py`
- Modify: `web/components/scan-workspace.tsx`
- Modify: `web/components/stock-detail-page.tsx`
- Modify only if needed: `web/lib/scan-context.ts`, `web/lib/stock-detail-route.ts`, direct `izfin_api/` scan/detail router/schema/service files
- Test: focused scan job, scan UI contract, and stock-detail API/component contract tests

**Consumes:** authenticated scan universe/watchlist, durable scan jobs, real `teknik_paneller`, and the current stock detail route.

**Produces:** one coherent route from universe choice → scan progress/recovery → full result table → selected ticker’s full Streamlit decision/technical analysis → Projection link. Durable history remains an internal recovery/context source; the user-approved web surface has no separate visible “Tarama geçmişi” module.

- [ ] **Step 1: Build a Streamlit-to-web field checklist before edits**

For the scan table, list only the actual Streamlit columns used by `scan_table.py`; for detail, list the decision, confidence, signal context, risk context, support/resistance, stop/TP, and textual-analysis blocks from `detail_analysis.py` and `analysis_views.py`. Mark each as already rendered, already returned but hidden, or absent from API.

- [ ] **Step 2: Write failing tests for the first absent real-data field or route link**

Add one API/contract test for each first gap and a UI source/component contract test that proves the selected row links to `/stocks/[ticker]` with the source scan job and that the detail page links to the same job’s Projection route.

- [ ] **Step 3: Run focused tests and confirm RED**

Run only the newly added scan/detail tests. The failure must name the absent contract field or missing route behavior; do not proceed on a generic snapshot failure.

- [ ] **Step 4: Implement the minimal Python-backed field mapping and rendering**

Map fields from existing scan result/technical panel payloads through FastAPI types and render them in the existing web components. Reuse the existing `jobId` route context; never calculate indicator, score, confidence, target, or stop values in React.

- [ ] **Step 5: Verify GREEN and commit**

Run focused scan/detail tests, Python test subset, web typecheck, and a production build; commit only this vertical flow.

## Task 3: Complete Projection and Performance parity

**Files:**
- Reference: `izfin_ui/projection_view.py`, `izfin_ui/performance_view.py`
- Modify: `web/components/projection-page.tsx`
- Modify: `web/components/performance-page.tsx`
- Modify only if needed: direct Projection/Performance `izfin_api/` schemas, routers, and services
- Test: focused Projection API/UI recovery tests and Performance API/UI contract tests

**Consumes:** accepted Projection recovery context, projectable technical panels, and real performance scorecard/position payloads.

**Produces:** Streamlit-equivalent Projection metrics/scenarios/bands and Performance active/closed positions, KPIs, interpretation, horizon scorecards, and small-sample warning.

- [ ] **Step 1: Create exact content checklists from both Streamlit views**

Projection checklist: current price, ATR, historical volatility, combined movement, base/upside/downside/wider bands, confidence, agreement, volatility explanation, positive/negative scenario, and direction summary. Performance checklist: active/closed positions, KPIs, win rate, average/median, duration, best/worst interpretation, 20G/60G/120G scorecard, asset detail, and small-sample warning.

- [ ] **Step 2: Add RED tests for the first missing real response field in each surface**

Use deterministic Python fixture data with a technical panel/position history. Assert the API response contains the source field and the TypeScript component contract includes the matching Turkish label. Do not use invented values.

- [ ] **Step 3: Implement only missing response mapping and rendering**

Extend the existing FastAPI response models from the existing Python view/service data, then render the value in the corresponding existing component. Keep Projection’s accepted authoritative job/ticker recovery unchanged.

- [ ] **Step 4: Verify GREEN and commit**

Run focused Projection/Performance tests, full Python suite, web typecheck, and production build before committing this checkpoint.

## Task 4: Complete Strategy, Account, and Admin route ownership audit

**Files:**
- Reference: `izfin_ui/backtest_view.py`, `izfin_ui/backtest_results.py`, `izfin_ui/legal_account_view.py`, `izfin_ui/qa_view.py`
- Modify: `web/components/strategy-lab-page.tsx`
- Modify: `web/components/account-page.tsx`
- Modify: `web/components/admin-quality-page.tsx`
- Modify only if needed: direct existing FastAPI route/schema/service files
- Test: focused Strategy, Account, and Admin auth/role contract tests

**Consumes:** existing authenticated APIs and role checks.

**Produces:** every remaining Streamlit screen has one web owner, real-data behavior, correct auth/admin gating, and no duplicated home-page responsibility.

- [ ] **Step 1: Make a route-by-route ownership checklist**

List each Streamlit action/result block and map it to exactly one web route. Mark unsupported actions explicitly; do not duplicate the block on Piyasa Merkezi.

- [ ] **Step 2: Add RED tests for unsupported actions or missing role guards**

For each first gap, write a focused API/UI contract test showing the authenticated normal-user, admin-user, and unauthenticated behavior expected from the Streamlit reference.

- [ ] **Step 3: Implement the narrowest route-local parity fix**

Add only the component/API mapping needed by the failing test, preserving existing Firebase and API retry/recovery behavior.

- [ ] **Step 4: Verify GREEN and commit**

Run focused tests plus both complete Python/Web gates; commit only the audited route slice.

## Task 5: Visual parity and authenticated-release acceptance

**Files:**
- Reference: `app2.py`, `izfin_ui/*.py`
- Modify: only stylesheet/component files required by a documented visual mismatch
- Test: existing responsive/source-contract tests plus route-level browser verification where available

**Consumes:** completed functional parity checkpoints.

**Produces:** responsive web layouts that preserve Streamlit’s dark command-center hierarchy without changing data meaning or adding new product features.

- [ ] **Step 1: Compare each completed web route against its Streamlit reference**

Record only concrete mismatches in hierarchy, information ordering, visibility, desktop width behavior, and narrow-screen behavior. Do not start with color-only polish.

- [ ] **Step 2: Add RED responsive/contract coverage for the first mismatch**

Add a focused source or browser test that identifies the required layout rule, label, or rendering order.

- [ ] **Step 3: Implement minimal visual translation**

Change only the relevant component/style declarations. Preserve existing design tokens and never replace real content with decorative placeholders.

- [ ] **Step 4: Verify full authenticated journey and release gates**

From a fresh authenticated session: scan → result → detail → Projection → Performance → Strategy → Account; then run full Python tests, web typecheck, production build, PR CI, and post-merge `develop` deployment verification.

## Task 6: Begin mobile only after web acceptance

**Files:**
- Create: a separate mobile design/spec and implementation plan after Task 5 acceptance

**Consumes:** accepted web route contract, API contract, design tokens, and responsive hierarchy.

**Produces:** a mobile plan that adapts navigation and tables for narrow screens while preserving the approved web/Streamlit product behavior.

- [ ] **Step 1: Confirm web parity acceptance with the user**

Do not create mobile code until the user has tested the complete web journey and accepted the web product as the Streamlit-equivalent release candidate.

## Plan self-review

- Scope coverage: every screen/order in `IZFIN_MASTER_STATUS.md` maps to exactly one checkpoint; Recovery remains an explicit gate.
- No placeholders: every task names its Streamlit reference, web owner, test direction, and completion condition.
- Interface consistency: scan-job context remains `jobId` + real technical-panel data; React remains a renderer while FastAPI/Python owns financial calculations.
