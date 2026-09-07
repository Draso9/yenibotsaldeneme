# Detailed Analysis context continuity — 2026-09-06

> Integration update — 2026-09-07: PR #146 has merged into develop. Its original pending steps below are historical,
> not instructions to reopen this package.
> See `IZFIN_MASTER_STATUS.md`, Latest verified handoff, for current next work.

Status: implementation and local verification complete; draft PR, exact-HEAD CI and authenticated preview acceptance must be checked before merge review. This is not a release or full browser acceptance.

## Scope and branch

- Branch: `fix/detail-context-continuity` from accepted develop `5ef3ca33094b8dc8686e4ce5a5b7ec5af3eaac2a`.
- Main/develop and production are unchanged. Legal rendering PR #145 remains separate; this package does not depend on its code or repeat it.
- Streamlit reference: `izfin_ui/scan_results.py::detay_secimi_hazirla` preserves a valid pending/current selection; web retains its existing stock route and owner-scoped scan snapshot model. A URL-specified stock is never silently replaced by another stock.

## Root cause and changes

- AppShell's contextual link used pathname alone, dropping the explicit job query. `StockDetailNavLink` preserves the current query under a local Suspense boundary.
- StockDetailPage previously rejected an absent job outright and persisted explicit job/ticker before the API accepted them. It now waits for per-user context hydration, resolves missing jobs from authenticated completed history, and validates the exact stock through the existing detail endpoint before persisting.
- An explicit job never falls back to another scan on error. Missing queries prefer an owned remembered completed scan, otherwise the latest completed scan. A recovered route receives a canonical job query for refresh.
- A deterministic review regression test caught background provider history retargeting a pending recovery. The remembered candidate is now captured once per route attempt.
- Result display is keyed by user/route; late responses cannot replace a newer route. Token acquisition failure yields a guided error instead of indefinite loading.
- API ownership/status/stock checks already exist; backend production code did not need modification. Seven direct endpoint regression cases cover authentication, foreign/unknown jobs, unfinished jobs and missing stocks.
- Actual React DOM, AnalysisContextProvider/localStorage and API client behavior are exercised with jsdom (development-only dependency). Firebase session, Next router and network responses are test boundaries, not live acceptance.

## Local evidence

- Before implementation: 6 of 9 behavior cases failed for the expected defects; existing deep-link and late-response behavior was preserved.
- After implementation: 23 web tests pass, including 13 detailed-context lifecycle cases.
- 91 related Python endpoint/service/Streamlit/context checks pass on Python 3.14.6.
- Typecheck and production build pass; lint 0 errors / 25 warnings (previous baseline 26); diff check passes.
- Three obsolete exact-source assertions were replaced by real rendered/persistence coverage, while the rest of their existing contracts remain.

## Pending acceptance and next package

1. Verify the draft PR's exact head against both Python and Web Quality Gates.
2. Open that head's READY preview, authenticate through the supported secure browser flow, and use a completed scan with a non-first selected stock.
3. Verify detail sidebar re-entry, refresh, missing-query recovery, projection round trip and scan return. Check that the same stock/job stays selected; do not mutate financial algorithms or unrelated recovery logic to finish this test.
4. Record CI/deployment IDs and actual browser evidence in the PR. Do not describe mocked DOM tests as browser QA.
5. Only after this package is accepted, revisit the already-deferred Smart Scan selection restoration issue if a real reproduction remains. KVKK publication data and old PR #43 remain separate work.
