# IZFIN — Master Project Status

> Canonical project handoff/status file for ChatGPT, Codex, and cross-device continuation.
> Read this file before making new changes.

## 1. Product Goal

IZFIN is being migrated from the mature Streamlit product to a Next.js + FastAPI web application.

**Approved direction:** Streamlit Full Parity Migration.

The existing Streamlit implementation is the product specification. Do **not** redesign the product from scratch. The new web application must systematically preserve the useful Streamlit behavior, information hierarchy, and visual structure while using the new architecture.

Primary product references:

- `app2.py`
- `izfin_ui/`
- existing framework-neutral/domain logic in `izfin_services/`, `izfin_core/`, repositories

Approved product title/tagline (2026-08-28):

**IZFIN | Akıllı Piyasa Kararları**

Do not reintroduce the old `Akıllı BIST Analizi` browser/product tagline.

## 2. Non-Negotiable Rules

- Never touch `main`.
- Base feature work on `develop`.
- Use feature branch -> PR -> `develop`.
- Do not merge unless relevant Python and Web CI gates are green.
- Keep Streamlit working in parallel until web parity is complete.
- Use TDD RED -> GREEN for fixes/features.
- Do not replace real financial data with mock/decorative data.
- Do not reimplement Python business calculations in React.
- Preserve existing production-readiness behavior: auth recovery, retry boundaries, scan recovery, durable readiness, same-origin API proxy.
- Avoid repo-wide rescans unless genuinely necessary.
- Group related 2-4 changes into meaningful checkpoint-sized work.
- Avoid micro-PR/status spam. User-facing progress should be checkpoint-based.

## 3. Current Architecture

### Frontend

- `web/` — Next.js App Router web client
- Vercel hosts the web frontend only

### API / Services

- `izfin_api/` — FastAPI boundary
- `izfin_services/` — service layer
- `izfin_core/` — shared domain/core logic
- repositories / Firebase / Firestore where already established
- Cloud Run hosts the FastAPI backend

### Legacy Product Reference

- `app2.py` — Streamlit application still operational
- `izfin_ui/` — Streamlit/product presentation modules and parity reference

## 4. Current Checkpoint

# SMART SCAN + DETAILED ANALYSIS — IMPLEMENTATION COMPLETE, LIVE ACCEPTANCE PENDING

Recovery was accepted for parity continuation on 2026-08-27 after the user
reported that Projection shows the real ticker selector and loads the selected
ticker. The user then explicitly approved continuing the Streamlit parity plan.

The SMART SCAN + DETAILED ANALYSIS implementation checkpoint now contains:

- no separate visible scan-history module; durable recovery stays internal
- no duplicate Piyasa Merkezi summaries under Akıllı Tarama
- selected-stock decision motor directly below the real scan result table
- explicit result ticker selector synchronized with the decision card
- why-buy / why-wait reasons, confidence, risk, MTF, entry quality, technical profile, and trade-plan levels
- structured Detailed Analysis sections from Python: indicators, trend/momentum, support/resistance, MTF entry motor, targets, and algorithmic interpretation
- no persisted verbal-analysis HTML in the web client
- selected ticker is now published into shared analysis context from the decision motor
- direct Detailed Analysis routes publish both job and ticker into shared context
- Detailed Analysis returns to `/scan#scan-result`, allowing server-backed scan recovery to restore the result flow
- browser/product title uses `IZFIN | Akıllı Piyasa Kararları`

Status rule:

Do not call this checkpoint fully accepted until the user verifies the deployed
`develop` journey live. If live verification passes, move to **Projection full Streamlit parity**.

## 5. Current Verified / User-Reported Live Issues

### A. Projection core recovery is accepted for continuation

After PR #98, the user verified live that direct Projection navigation resolves
the completed scan, presents the real ticker selector, and loads the selected
ticker. Refresh/deep-link/new-account variants remain part of the final full
authenticated journey recheck, but there is no currently reported Projection
blocker.

Do not claim Projection continuity is complete based only on CI.

### B. Piyasa Merkezi responsibility cleanup landed in PR #98

`web/app/page.tsx` no longer renders the scan banner, watchlist editor,
auth/account block, or roadmap/tool-launch block as primary Piyasa Merkezi
modules. The page remains decision-oriented.

Approved placement rule:

**Piyasa Merkezi = decision summary page, not list-management/scan-configuration page.**

Keep there:

- market/scan pulse
- trend
- momentum
- money flow
- risk
- system interpretation
- top signals / notable names
- focused security summary
- movers
- links into detailed analysis

Move out:

- primary watchlist editing
- universe construction
- scan configuration
- account-management blocks

These belong mainly in Akıllı Tarama / Hesap.

### C. SMART SCAN + DETAILED ANALYSIS live acceptance is pending

Implementation and CI are expected to be complete in the current checkpoint PR,
but user acceptance must verify:

- revisiting `/scan` restores the latest completed result
- selecting a different result ticker changes the decision motor
- opening Detailed Analysis keeps that same ticker/job
- returning to Akıllı Tarama restores the result flow
- using sidebar/CTA Projection after selecting a ticker keeps the intended context
- structured technical sections display real data without HTML fallback artifacts

## 6. Latest Relevant Merges

### PR #95 — Analysis continuity

Merge commit:

`6892be7c8a96e9b86e9dd000534e6f38b26430c8`

Added typed scan context helpers, authenticated analysis context, scan -> shared
context publication, Projection recovery attempts, and guided no-scan state.

### PR #96 — stale cached analysis job recovery

Merge commit:

`d9dcc62cee1a5e7aecfb13c0232f2a72962586f9`

Validated cached active scan context against authoritative server history.

### PR #98 — Projection recovery root fix + Piyasa Merkezi cleanup

Merge commit:

`d06a8a1`

Added authoritative projectable ticker recovery, real Projection ticker selection,
and removed misplaced Piyasa Merkezi controls/modules.

### PR #99 — Streamlit smart scan decision flow

Added the per-stock decision motor below scan results, removed visible scan history,
kept recovery internal, removed raw verbal-analysis HTML, and retained job-scoped
Detail/Projection navigation.

### PR #100 — Akıllı Tarama decision focus

Removed duplicated Piyasa Merkezi content from scan, strengthened decision-card
hierarchy, and restored completed scan results when returning to `/scan`.

### PR #101 — decision ticker selector

Added the real scan-result ticker selector and synchronized it with row selection.

### PR #102 — structured Detailed Analysis parity

Added Python-owned structured technical analysis: indicators, trend/momentum,
support/resistance, MTF entry quality, targets, algorithmic interpretation, and
safe sparse-panel fallback behavior.

### PR #103 — SMART SCAN + DETAILED ANALYSIS checkpoint close candidate

Pending merge/live acceptance at the time of this status update.

Adds shared selected-ticker publication, Detailed Analysis job/ticker context
publication, return-to-scan continuity, and the approved product title
`IZFIN | Akıllı Piyasa Kararları`.

## 7. Develop Preview

Stable develop branch URL:

`https://izfin-web-git-develop-adopcin-7216.vercel.app`

Do not use a one-off deployment URL as the canonical link unless debugging a specific deployment.

## 8. RECOVERY Acceptance Criteria

Recovery behaviors remain in the final authenticated journey checklist:

1. User completes or opens a completed scan.
2. User clicks **Projeksiyon** from the sidebar.
3. Projection automatically resolves a valid completed scan.
4. If one valid ticker exists, Projection opens directly.
5. If multiple valid tickers exist and none is selected, a real ticker selector is shown.
6. Refreshing Projection preserves/reconstructs valid context.
7. Explicit `job_id` + `ticker` deep links override recovered context when valid.
8. A genuinely new account with no completed scan gets a guided `/scan` empty state.
9. No stale browser cache can block authoritative server history.
10. Piyasa Merkezi no longer contains scan/list/account-management clutter.
11. User verifies the above on the Vercel `develop` deployment.

The user’s 2026-08-27 live verification accepted the core Recovery path for
parity continuation. Recheck refresh, explicit deep links, and new-account
empty state before Stage 5 close; treat a new live failure as a Recovery
regression, not as permission to stack a workaround.

## 9. Work Order After Recovery

Do not change this order without an explicit user decision.

1. Piyasa Merkezi functional parity
2. Detaylı Analiz functional parity
3. Projeksiyon full Streamlit parity
4. Performans parity
5. Strategy Lab parity
6. Account/Admin parity audit
7. Visual parity / responsive Streamlit-to-web translation
8. Full authenticated user journey / Stage 5 close
9. Stage 6 Mobile only after Stage 5 is accepted

## 10. Streamlit Full Parity Target by Screen

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
- featured ticker/security
- movers
- decision-oriented hierarchy
- no primary watchlist editing or scan configuration

### Akıllı Tarama

Current state: functional parity checkpoint candidate, pending live acceptance.

Target:

- BIST 30
- BIST 100
- Kendi Listem
- symbol search/add/remove
- launch scan
- progress/recovery
- internal durable scan recovery; no separate visible history module
- results table
- selected ticker decision motor below the table: why buy / why wait, confidence, risk, MTF, entry quality, technical profile, and levels
- continuity into Detailed Analysis / Projection
- structured Detailed Analysis sections owned by Python: indicators, trend/momentum,
  support/resistance, MTF entry motor, targets, and algorithmic interpretation;
  no persisted verbal-analysis HTML in the web client

### Detaylı Analiz

Reference: `izfin_ui/detail_analysis.py`, `izfin_ui/analysis_views.py`

Target:

- full indicator/textual analysis
- confidence score
- technical sections
- signal context
- risk context
- realistic TP / stop information
- navigation into Projection
- shared job/ticker continuity back to Akıllı Tarama and onward to Projection

### Projeksiyon

Reference: `izfin_ui/projection_view.py`

Target content model:

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

## 11. Technical Debt Snapshot

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
- Vercel/Cloud Run deployment split

### High debt / current risk

Web product layer currently has meaningful debt:

- incomplete Streamlit functional parity outside the completed/current checkpoints
- generic/stacked CSS convergence layers
- final authenticated journey still needs one comprehensive acceptance pass
- some route/context coupling remains until all analysis surfaces use the same shared context consistently

Debt reduced in the SMART SCAN + DETAILED ANALYSIS checkpoint by:

- removing duplicate visible responsibilities
- eliminating a local-only selected-ticker handoff at the decision/detail boundary
- keeping business calculations in Python
- replacing raw HTML dependencies with structured contracts
- making return navigation rely on server-backed scan recovery instead of duplicated client state

### Technical debt policy from now on

- no unnecessary decorative features before functional parity
- no additional CSS polish before functional parity
- remove duplicate responsibilities instead of layering more UI
- prefer authoritative server state over browser-only state
- keep business calculations in Python
- each checkpoint should reduce, not increase, product-layer debt

## 12. Working Style / Communication

The user does not want to track dozens of PR numbers or micro-steps.

At the end of each checkpoint, report only:

### What works

Concrete, live-verified behaviors.

### What is missing

Remaining product gaps only.

### What the user should test live

Exact Vercel journey/actions.

### Technical debt trend

State whether debt increased, decreased, or stayed flat, and why.

Internally, PRs/tests/commits are still required, but do not make them the main user-facing progress model.

## 13. Codex Efficiency Rules

- Do not repeatedly scan the whole repository.
- Start from this file, the approved parity spec, and the files directly relevant to the current checkpoint.
- Work checkpoint-by-checkpoint and read only the Streamlit/web/API files needed for the active surface.
- Trace real data flow before applying fixes.
- If a fix fails repeatedly, stop and reassess the architecture rather than stacking another workaround.

## 14. Canonical Next Action

**Live-verify SMART SCAN + DETAILED ANALYSIS on Vercel `develop`.**

Acceptance journey:

1. Open Akıllı Tarama and recover or complete a real scan.
2. Select a ticker from the result table or decision selector.
3. Confirm the Hisseye Özel Karar Motoru changes to that ticker.
4. Open Detaylı Analiz and confirm the same ticker/job, structured indicators,
   trend/momentum, support/resistance, MTF entry motor, targets, and algorithmic comment.
5. Use `← Akıllı Tarama` and confirm the completed result is restored.
6. From the selected ticker, open Projection and confirm context is preserved.
7. Confirm browser title is `IZFIN | Akıllı Piyasa Kararları`.

If the user accepts this journey, mark SMART SCAN + DETAILED ANALYSIS complete and
start **Projection full Streamlit parity** next. Do not begin Projection full parity
before recording the live acceptance unless the user explicitly asks to proceed anyway.
