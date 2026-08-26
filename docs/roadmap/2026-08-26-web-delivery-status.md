# IZFIN Web Product Delivery Roadmap

_Last reconciled: 2026-08-26_

## Source of truth and working rules

- `develop` is the integrated source of truth.
- Every package starts from current `develop`, uses a feature branch, and targets `develop` with a PR.
- A package merges only after GitHub CI is green; the following `develop` CI is checked too.
- `main` is never a target of this workflow.
- This file, its PRs, and merged commits are the shared handoff record across computers and Codex tasks. Local folders and chat history are not the source of truth.

## Completed foundations

- [x] FastAPI foundation and Cloud Run deployment baseline.
- [x] Next.js foundation: Firebase-backed session, watchlist, scan, account surfaces, and web quality CI.
- [x] API/web boundary hardening and responsive web beta groundwork.
- [x] Shared IZFIN design foundation and Market Center redesign (PR #61).
- [x] Akıllı Tarama → job-scoped stock detail handoff plus explicit empty/loading/error states (PR #63).
- [x] Projeksiyon scenario-context, model-state, and disclosure hierarchy (PR #64).
- [x] Performans context plus explicit session/position/scorecard states (PR #65).

## Product delivery order

The earlier “screen polish” list is expanded below. A later phase does not start before its required earlier package is green and merged.

### Phase 1 — Finish shared web surfaces

- [x] **Strateji Lab**: strategy selection/configuration, run lifecycle, parameter validation, result/comparison, empty/error states, mobile layout (PR #67).
- [x] **Hesap, consent, and legal**: account settings, consent/OAuth status, session controls, export and legal disclosures (PR #68).
- [x] **Cross-screen visual consistency**: shared spacing, component states, keyboard focus, desktop/mobile behavior across all six navigation areas. The shared shell now provides a keyboard skip link, active-page semantics, common focus treatment, and responsive page gutters.

### Phase 2 — Make Akıllı Tarama a full product workspace

- [x] **Scan configuration**: server-owned BIST/ABD profiles, persistent personal list, active-universe confirmation, validation, and launch summary.
- [x] **Scan results**: the existing scanner's real returned-result filters, KPI cards, complete sortable decision table, risk/score columns, and direct detail handoff. No new comparison feature was introduced.
- [x] **Scan history**: completed/failed owner-scoped job history, safely reopen a result, plus visible progress states (this package).
- [x] **Decision transparency**: expose every existing Streamlit result-table field, skipped-symbol warning, and job-scoped technical-detail handoff directly from the FastAPI response.

### Phase 3 — Identity, onboarding, and IZFIN brand

- [x] **Dedicated auth routes**: separate Firebase sign-in, sign-up, password reset, email verification, Google sign-in, authenticated return flow, and the existing IZFIN profile/default-watchlist bootstrap.
- [x] **Onboarding**: first-run explanation, consent path, watchlist start, and first-scan guidance. The signed-in scan workspace now reuses the Streamlit 4-step decision-reading guide and lets each user dismiss it locally after the first visit.
- [ ] **Brand system**: approved IZFIN logo asset, favicon/app icons, typography/voice, and empty-state illustrations. Do not invent a final logo; add the approved asset when available.

### Phase 4 — Product depth and trust

- [ ] **Portfolio/Performance depth**: range-aware presentation, understandable KPI definitions, history drill-down, and transparent small-sample warnings.
- [ ] **Projection depth**: scenario comparison, assumptions, historical context, and risk disclosure.
- [ ] **Operational trust**: graceful provider/API outage states, request feedback, observability, and user-safe error language.
- [ ] **Security review**: Firebase rules/session boundaries, secret handling, rate limits, and legal copy review.

### Phase 5 — Visual acceptance and release

- [ ] **Visual acceptance**: signed-in and signed-out desktop/mobile checks for home, scan, detail, projection, performance, strategy, and account.
- [ ] **Automated quality**: API contract/unit tests, architecture/static tests, browser/AppTest regression coverage, full pytest, TypeScript, production build, compile and diff checks.
- [ ] **Staging and Cloud Run**: production-like environment, health/readiness, monitoring, rollback notes, and a deploy checklist.
- [ ] **Public release decision**: domain/custom URL, privacy/legal review, support contact, and launch go/no-go.

### Phase 6 — Mobile application preparation

- [ ] Stabilize the FastAPI contracts and shared design tokens.
- [ ] Decide the mobile client approach after the web release is accepted (React Native/Expo is the likely path).
- [ ] Reuse the same API/auth contracts; do not fork business rules into a mobile-only backend.

## Visual verification process

1. After every UI package, run local Next.js production build and inspect `http://localhost:3000` at desktop and mobile widths.
2. For protected surfaces, the user signs in locally; no password or token is shared with Codex.
3. Each package has explicit signed-out, loading, empty, error, and populated-data checks.
4. Before release, repeat the full flow against the Cloud Run deployment using real permitted data.
5. Visual acceptance findings are fixed in a feature branch and go through the same CI/PR/merge process.

## Invariants

- Streamlit remains operational as the legacy thin shell until the web release is accepted.
- Next.js reuses FastAPI contracts and never duplicates business logic.
- No fabricated market data: unavailable, empty, and loading states remain explicit.
- Preserve Turkish product language and IZFIN identity.
- Every completed package is pushed and merged through GitHub before moving on.

## Next package

Start from current `develop`: add the **approved brand assets** (logo, favicon/app icons and visual direction), then complete release acceptance. The parity audit is recorded in `docs/roadmap/2026-08-26-streamlit-web-parity-audit.md`.




