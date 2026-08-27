# IZFIN Streamlit Full Parity Migration Design

## Status

Approved direction: treat the existing Streamlit product as the product specification and migrate it systematically to the Next.js + FastAPI web application without losing working behavior, information hierarchy, or useful visual structure.

This design replaces the previously planned generic “final polish” step. Stage 5 closes only after functional and visual parity is demonstrated across the core user journey.

## 1. Goal

The goal is not to redesign IZFIN from scratch. The goal is to make the web client behave and feel like the mature Streamlit product, while keeping the new architecture:

- Next.js web client in `web/`
- FastAPI boundary in `izfin_api/`
- shared domain/service logic in `izfin_services/`, `izfin_core/`, and repositories
- Firebase authentication and Firestore-backed persistence where already established
- Streamlit kept working in parallel until parity is complete

The Streamlit implementation in `app2.py` and the framework-neutral presentation/view-model modules in `izfin_ui/` are the product reference.

## 2. Non-negotiable constraints

- Do not touch `main`.
- Work from `develop` through feature branches and PRs.
- Do not merge unless relevant Python and web CI gates are green.
- Do not break the existing Streamlit app.
- Do not replace real data with mock or decorative financial data.
- Do not remove currently working Next.js/FastAPI production-readiness behavior.
- Preserve existing auth recovery, retry, scan recovery, durable readiness, and same-origin API proxy behavior.
- Migration must be incremental and reversible at PR granularity.

## 3. Product source of truth

Parity decisions follow this priority order:

1. Existing Streamlit behavior that users already rely on.
2. Framework-neutral `izfin_ui` view-model and presentation helpers extracted from Streamlit.
3. Existing service/domain behavior in `izfin_services`, `izfin_core`, and repositories.
4. Existing FastAPI endpoint contracts.
5. Existing Next.js implementation where it already matches the above.

If the current Next.js screen conflicts with working Streamlit behavior, Streamlit wins unless there is a documented production-readiness reason not to copy it literally.

## 4. Current diagnosis

The web migration has a working shell, authentication, scan execution, result recovery, API error handling, and several data endpoints. The remaining problem is product continuity rather than basic infrastructure.

Observed gaps:

- Akıllı Tarama is now usable, but its surrounding product flow still differs from Streamlit.
- Projection and detail flows depend too strongly on route parameters from a specific scan result. Direct navigation can show a technical empty state even after a user has completed a scan.
- Cross-page state is not modeled as a first-class product concept. “Latest completed scan”, “selected ticker”, “active universe”, and “current analysis context” are not consistently shared.
- Some features that existed in Streamlit are missing from the web UI, are visually reduced, or are in the wrong place.
- Piyasa Merkezi currently contains controls that belong to scan/list management rather than market decision summary.
- Performance, Projection, Strategy Lab, Account/Admin, and detail experiences do not yet have proven Streamlit-level parity.
- Generic CSS convergence improved consistency but did not create functional parity.

## 5. Target application model

### 5.1 Shared analysis context

The web app will introduce a durable, user-scoped analysis context with these concepts:

- `latestCompletedScanJobId`
- `activeScanJobId`
- `selectedTicker`
- `activeUniverseProfile`
- `watchlist`
- `lastVisitedAnalysisRoute`

The context is derived from server truth whenever possible, not only browser memory.

Priority for resolving an analysis page:

1. explicit route/query context
2. current active context in the web client
3. newest completed scan in user scan history
4. explicit user selection from available completed scans
5. if none exists, a guided empty state leading to Akıllı Tarama

A user who has completed a scan must not receive “this page must be opened from a completed scan” merely because they entered through the sidebar.

### 5.2 Navigation behavior

- Sidebar navigation stays stable.
- Analysis pages restore the latest valid context automatically.
- A ticker chosen on scan results, Piyasa Merkezi, or detailed analysis becomes the selected ticker for Projection where valid.
- Back-navigation keeps the analysis context instead of resetting the user.
- Empty states are product-oriented, not technical contract messages.

## 6. Streamlit → Web parity matrix

The first implementation milestone will turn this design matrix into executable parity tests and a tracked checklist.

| Product area | Streamlit reference | Current web state | Required parity outcome |
| --- | --- | --- | --- |
| Piyasa Merkezi | `izfin_ui/home_dashboard.py`, `app2.py` | Partially present | Keep decision summary, pulse/trend/momentum/flow/risk, system comment, top signals, featured ticker, movers; remove list-management controls from this page; match Streamlit hierarchy and density |
| Akıllı Tarama | Streamlit scan flow in `app2.py` plus extracted scan services | Usable after PR #93 | Preserve BIST 30 / BIST 100 / Kendi Listem, symbol search/add, scan launch, progress, recovery, history and results; align layout and result table with Streamlit |
| Detaylı Analiz | `izfin_ui/detail_analysis.py`, `izfin_ui/analysis_views.py` | Partial | Restore full indicator/textual analysis, confidence score, technical sections, signal/risk context, target/stop information and navigation to Projection |
| Projeksiyon | `izfin_ui/projection_view.py` | Data exists but route-context dependent | Auto-resolve latest completed scan and ticker; restore 45G model hero, ATR/volatility/combined metrics, model confidence, bands, positive/negative scenarios and algorithmic direction summary |
| Performans | `izfin_ui/performance_view.py` | Partial | Match active positions, closed-position history, summary KPIs, scorecard horizons, best/worst interpretation, drilldown, empty states and table density |
| Strategy Lab | `izfin_ui/backtest_view.py`, `izfin_ui/backtest_results.py` | Partial | Match symbol discovery, parameter workflow, historical strategy result presentation and explanatory context without fake data |
| Account / Legal | `izfin_ui/legal_account_view.py`, `izfin_ui/auth_view.py` | Mostly implemented | Verify parity for profile, legal text, export, delete-account flow and safe post-delete transition; converge visual hierarchy |
| Admin / System Health | `izfin_ui/qa_view.py` plus current admin API | Implemented but visually separate | Preserve admin-only visibility, CI/release/readiness data and align with the common product design language |
| Market strip / navigation | `izfin_ui/market_bar.py`, `izfin_ui/navigation.py` | Present in new shell | Compare labels, information content, active state, mobile behavior and remove redundant navigation/action blocks |

## 7. Migration packages

### Package A — Shared state and analysis continuity

Purpose: stop pages from appearing empty after valid user activity.

Work:

- Add a web analysis-context layer.
- Resolve newest completed scan from authenticated scan history.
- Restore selected ticker from valid latest context.
- Make Projection, Detailed Analysis, and related pages resolve context automatically.
- Add a completed-scan selector where ambiguity exists.
- Replace technical dead-end copy with guided product states.
- Keep explicit `jobId`/ticker links working for deep links.

Acceptance:

- Complete a scan, navigate through sidebar to Projection, and see valid latest-scan content without manually reconstructing the URL.
- Refresh an analysis page and recover the same valid context.
- Open a deep link and preserve the explicit deep-link context.
- A genuinely new account with no completed scan is guided to scan rather than shown a contract error.

### Package B — Functional parity by screen

Purpose: transfer every useful Streamlit function before visual polishing.

Order:

1. Piyasa Merkezi cleanup and parity
2. Detaylı Analiz parity
3. Projeksiyon parity
4. Performans parity
5. Strategy Lab parity
6. Account/Admin parity audit

For each screen:

- compare Streamlit inputs, sections, calculations, actions and empty/error states
- map each behavior to existing service/API support
- expose a new API contract only when required
- port presentation without reimplementing domain calculations in React
- add parity tests before implementation

### Package C — Visual parity and responsive adaptation

Purpose: make the mature Streamlit product the visual reference instead of inventing a second product language.

Rules:

- Preserve the parts of Streamlit that already worked well: section order, information density, result emphasis, confidence/risk prominence, table content, key callouts, scenario cards, decision summaries.
- Translate Streamlit layout into responsive Next.js components rather than copying framework-specific markup.
- Keep the approved dark navy/charcoal IZFIN web shell and brand framing.
- Use green/teal/blue for positive/primary emphasis and orange/red for caution/risk.
- Do not add decorative cards with no real data purpose.
- Reduce duplicate controls and remove modules from pages where they do not belong.
- Mobile behavior must degrade to stacked readable sections without hiding core information.

### Package D — Stage 5 close-out user journey

Purpose: prove the migration as a product, not as isolated pages.

Mandatory journey:

1. sign in
2. choose BIST 30 / BIST 100 / personal list
3. search/add/remove a ticker where applicable
4. start scan
5. observe progress/recovery
6. inspect results
7. open detailed analysis
8. open Projection
9. navigate to Piyasa Merkezi with context preserved
10. navigate to Performance
11. return to Akıllı Tarama and run another scan
12. refresh/reopen pages and confirm context recovery
13. sign out and confirm protected states

This journey must be tested on the Vercel `develop` deployment as well as through automated CI contracts.

## 8. API and domain boundaries

React must not reproduce Streamlit's business calculations.

Preferred layering:

- Python domain/service code computes signals, scores, projection models, performance summaries, strategy results and presentation-ready semantics.
- FastAPI exposes stable authenticated contracts.
- Next.js handles routing, state continuity, interaction, accessibility and rendering.

When an existing `izfin_ui` function contains useful framework-neutral transformation logic, move or reuse that logic in a service/view-model boundary rather than translating it ad hoc to TypeScript.

## 9. Piyasa Merkezi placement rules

Piyasa Merkezi is a decision-summary page, not a list-management page.

Keep:

- market/scan pulse
- trend, momentum, money flow, risk
- system interpretation
- top signals / notable names
- focused security summary
- large movers
- links into detailed analysis

Move out:

- primary watchlist editing
- universe construction controls
- scan configuration controls

Those belong primarily in Akıllı Tarama and, where useful, Account/watchlist management.

## 10. Projection behavior

The Streamlit projection module already defines the intended product model:

- approximately 45-day model
- current price
- ATR model movement
- historical volatility movement
- combined model movement
- 45G combined band
- wider risk band
- model confidence and model agreement
- volatility explanation
- positive technical scenario
- negative technical scenario
- algorithmic direction summary

The web page will preserve this content model.

Direct sidebar behavior:

- if a selected ticker and completed scan are valid, render immediately
- otherwise select the latest completed scan
- if that scan contains multiple tickers and none is selected, show a ticker selector populated from that scan
- only show the “run a scan first” state when no completed scan exists

## 11. Performance behavior

Performance remains account-scoped rather than dependent on a route-specific scan.

Parity includes:

- active positions
- closed positions
- closed-period KPIs
- win rate / average / median outcomes where supported
- median duration
- TP/stop observation metrics where available
- best/worst historical interpretation
- 20G / 60G / 120G scorecard horizons
- asset-level scorecard
- signal-level detail history
- clear small-sample warnings

Missing historical metrics remain `—`; the web client must not fabricate them.

## 12. Test strategy

Every migration PR uses RED → GREEN TDD.

Test layers:

- Python contract tests for API/view-model parity
- web source/component contract tests for required sections and navigation behavior
- Next.js typecheck and production build
- full Python test suite
- integration tests for context resolution and API error paths where practical
- Vercel `develop` smoke checks after merge

For parity work, each screen gets an explicit checklist test covering the expected Streamlit sections and actions before implementation.

## 13. PR strategy

Keep changes reviewable and Codex-efficient.

Recommended PR sequence:

- PR A1: analysis context + latest completed scan resolver
- PR A2: Projection/detail sidebar recovery and selectors
- PR B1: Piyasa Merkezi cleanup + Streamlit parity
- PR B2: Detailed Analysis parity
- PR B3: Projection full content parity
- PR B4: Performance full parity
- PR B5: Strategy Lab parity
- PR B6: Account/Admin parity audit fixes
- PR C1-Cn: visual parity by coherent screen group, not tiny CSS fragments
- PR D1: full user-journey close-out and remaining migration defects

Related 2–4 changes should be grouped when they share the same files and test boundary. Avoid repo-wide rescans after every small PR.

## 14. Stage 5 completion criteria

Stage 5 is complete only when all are true:

- Every Streamlit product area in the parity matrix is classified as parity-complete or intentionally excluded with a documented reason.
- A completed scan can be consumed across pages without route-context loss.
- Projection no longer incorrectly appears empty after a valid completed scan.
- Piyasa Merkezi contains decision information, not misplaced scan/list-management controls.
- Detailed Analysis, Projection, Performance and Strategy Lab match the useful Streamlit information set.
- The visual hierarchy is recognizably the Streamlit product translated into the new web shell.
- No fake market data or decorative placeholder financial content is used.
- Streamlit remains operational.
- `main` remains untouched.
- Relevant CI is green.
- The complete authenticated user journey passes on the Vercel `develop` deployment.

Only after these criteria are satisfied should Stage 6 mobile work begin.

## 15. Immediate next step after design approval

After this design document is reviewed, create the implementation plan beginning with Package A. Do not start Package C visual polish before Packages A and B establish functional parity. Do not close Stage 5 based on page existence alone; close it based on parity and user-journey evidence.
