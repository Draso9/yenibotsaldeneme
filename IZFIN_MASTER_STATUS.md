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

# SMART SCAN + DETAILED ANALYSIS

Recovery was accepted for parity continuation on 2026-08-27 after the user
reported that Projection shows the real ticker selector and loads the selected
ticker. The user then explicitly approved continuing the Streamlit parity plan.

Current checkpoint: restore the Streamlit per-stock decision motor directly
below Akıllı Tarama results, remove the separate visible scan-history module,
and retain durable scan recovery/context internally.

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

## 6. Latest Relevant Merges

### PR #95 — Analysis continuity

Merge commit:

`6892be7c8a96e9b86e9dd000534e6f38b26430c8`

Added:

- typed scan context helpers
- authenticated analysis context provider
- scan -> shared context publication
- Projection recovery attempt from explicit/shared/latest scan context
- guided no-scan state

### PR #96 — stale cached analysis job recovery

Merge commit:

`d9dcc62cee1a5e7aecfb13c0232f2a72962586f9`

Purpose:

- validate cached `activeScanJobId` against authoritative server scan history
- replace stale cached scan context with latest completed server scan

Status:

- CI passed
- merged to `develop`
- Vercel deployed
- stale-cache fix alone was insufficient; superseded by the PR #98 root fix below

### PR #98 — Projection recovery root fix + Piyasa Merkezi cleanup

Merge commit:

`d06a8a1`

Added:

- authoritative projectable ticker recovery
- real ticker selection for multi-ticker completed scans
- removal of misplaced Piyasa Merkezi controls/modules

Status:

- both CI gates passed and merged to `develop`
- user verified the real Projection selector and selected-ticker load live
- user explicitly approved continuing parity migration

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

Current state: usable baseline, but still subject to final Streamlit parity.

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

- duplicate UI responsibilities
- modules placed on the wrong page
- fragile shared analysis state
- route/context coupling
- incomplete Streamlit functional parity
- generic/stacked CSS convergence layers
- page existence being mistaken for product completion
- too many small implementation increments obscuring the product-level state

### Technical debt policy from now on

- no new decorative/product features until Recovery is accepted
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
- For Recovery, focus first on:
  - `web/components/analysis-context-provider.tsx`
  - `web/lib/scan-context.ts`
  - `web/components/projection-page.tsx`
  - `web/app/projection/page.tsx`
  - `web/app/page.tsx`
  - `web/components/dashboard.tsx`
  - scan-history/job API contracts in `izfin_api/`
  - existing focused tests around analysis context and Projection
- Trace the real live data flow before applying another Projection patch.
- If a fix fails repeatedly, stop and reassess the architecture rather than stacking another workaround.

## 14. Canonical Next Action

**Complete SMART SCAN + DETAILED ANALYSIS checkpoint.**

First:

1. Keep the separate visible `Tarama geçmişi` module removed.
2. Keep server-backed active-job discovery/polling as internal recovery.
3. Render the selected ticker’s structured Streamlit decision motor directly below results.
4. Preserve job-scoped links into Detailed Analysis and Projection.
5. Do not render persisted verbal-analysis HTML; expose structured Python fields.
6. Run focused tests + full Python/Web gates.
7. Merge only if both CI gates are green.
8. Verify the Akıllı Tarama result-selection/decision journey on Vercel `develop` with the user.
