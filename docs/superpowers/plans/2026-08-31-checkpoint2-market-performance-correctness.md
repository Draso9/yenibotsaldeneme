# Checkpoint 2 — Market & Performance Correctness Implementation Plan

## Goal
Complete Web Completion Program Checkpoint 2 without entering Checkpoint 3+ scope. Piyasa Merkezi must keep market-strip data truthfully fresh while the page remains open, and Performans refresh must execute a real owner-scoped Python server mutation instead of merely refetching unchanged GET state.

## Canonical references
- `docs/superpowers/specs/2026-08-31-web-completion-program-design.md`
- `IZFIN_MASTER_STATUS.md`
- Streamlit behavior in `app2.py`
- `izfin_ui/performance_view.py`
- existing calculations in `izfin_services/performance_refresh.py`

## Architecture
### Market strip
Keep the existing public same-origin API. The Next.js client revalidates on mount, every 60 seconds, browser focus, and `online`. A local clock advances displayed freshness between successful snapshots. Failed revalidation preserves the last valid snapshot and marks it stale; only an initial failure with no snapshot shows unavailable state.

### Performance refresh
Expose authenticated `POST /api/v1/performance/refresh`. Owner identity comes only from the verified Firebase bearer token; the client never submits an owner email/UID. The endpoint invokes an injected Python refresher that reuses existing price/P&L and frozen-horizon services. Canonical horizons are `1/5/10/20/45` trading days. React performs no financial calculation.

Mutation outcomes distinguish updated, already-current/no-op, in-progress/single-flight, and source-error. Existing history is never removed on provider failure.

### Concurrency / idempotency
Use a per-owner single-flight guard so duplicate concurrent refreshes for one user do not execute twice. Different users remain independent. Frozen horizon results remain immutable and unchanged price/P&L state must not write solely because a refresh was requested.

## Constraints
- Never touch `main`.
- Feature branch -> PR -> `develop` only.
- Checkpoint 2 only.
- Preserve auth recovery and same-origin API proxy.
- Keep Streamlit operational.
- Financial calculations stay in Python.
- TDD RED -> GREEN for every behavior slice.
- ESLint 9 flat config belongs to Checkpoint 7; do not add it here.

## Task 1 — Market-strip freshness and stale retention
### RED
Add focused regression tests requiring 60-second revalidation, `focus`/`online` listeners, progressive freshness, last-valid-snapshot stale retention, and continued absence of Piyasa Merkezi score/risk sort controls while service ordering remains intact.
### GREEN
Update `web/components/market-strip.tsx` and minimal related CSS only. Keep public API contract unchanged.

## Task 2 — Owner-scoped performance mutation
### RED
Require authenticated `POST /api/v1/performance/refresh`, token-derived owner identity, no owner override, safe unavailable runtime, per-owner single-flight behavior, source-error history preservation, no-op idempotency, and newly eligible frozen `1/5/10/20/45` measurements.
### GREEN
Add the smallest runtime dependency, API route/response and Python orchestration necessary, composing existing providers in the environment runtime.

## Task 3 — Performance web UX + canonical horizons
### RED
Require horizon buttons exactly `1,5,10,20,45`; refresh POST before GET reload; disabled refreshing button; explicit refreshing/current/already-current/source-error states; and preservation of rendered history on refresh failure.
### GREEN
Add typed mutation helper in `web/lib/performance.ts` and minimally update `web/components/performance-page.tsx`.

## Task 4 — Verification
Run focused Checkpoint 2 tests, complete Python tests, Next.js typecheck, Next.js production build, and lint preflight. If lint is blocked only by the known missing ESLint flat config, record that limitation and do not fix it in this checkpoint. Review diff for Checkpoint 2-only scope; merge only with Python + Web CI green, then verify post-merge `develop` CI and Vercel production at the merge SHA.

## Live acceptance
1. Leave Piyasa Merkezi open >60s; freshness advances and data revalidates.
2. Focus/reconnect triggers revalidation without losing last valid data on transient failure.
3. No `Sonuç sırası` / Risk sort control returns; service-defined signal order remains.
4. Performans horizons are `1G/5G/10G/20G/45G`.
5. `Verileri yenile` shows refreshing then updated or already-current truthfully.
6. Provider error preserves existing history and shows source-error state.
7. Authenticated owner isolation prevents refreshing another user's records.
