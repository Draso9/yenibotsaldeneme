# IZFIN Final Product Polish Checkpoints — Design

## Goal

Bring the current Next.js + FastAPI IZFIN web product from feature-complete parity into a consistent release-candidate state without changing financial calculations, decision rules, API payload semantics, auth/recovery boundaries, or the protected `main` branch.

## Baseline

This program starts from `develop` after PR #135, merge SHA `d04705ca6b9d9632d311409f6fa4f1091a1b63aa`.

The current product already has the major user journeys in place:

- Piyasa Merkezi
- Akıllı Tarama
- Hisseye Özel Karar Motoru
- Detaylı Analiz
- Projeksiyon
- Performans
- Strateji Lab
- Hesap / yasal işlemler
- Admin QA / readiness
- responsive/mobile presentation foundations

The objective is polish and release closure, not feature expansion.

## Global Constraints

- Never touch `main`.
- Base each checkpoint on the latest accepted `develop`.
- Use a dedicated feature branch and PR per checkpoint.
- TDD RED -> GREEN for behavior/copy contracts where code changes are involved.
- Merge only after relevant Python and Web CI gates are green.
- Verify post-merge `develop` CI and production deployment identity.
- Keep Streamlit operational.
- Keep business and financial calculations in Python.
- Do not change central decision rules, scan API payload semantics, auth recovery, retry boundaries, scan recovery, durable readiness, or shared ticker continuity unless a checkpoint explicitly identifies a real defect in one of those boundaries.
- Do not introduce fake or decorative financial values.
- Avoid broad CSS refactors during this release-polish program.

## Checkpoint Order

### CP0 — Canonical Status Reset

Update `IZFIN_MASTER_STATUS.md` to the actual product state after PRs #132–#135 and record this checkpoint program as the canonical continuation order.

Required corrections:

- Decision Motor is above result filters/tables, not below the table.
- `ABD Büyük Teknoloji` is a first-class Smart Scan quick universe.
- Detailed Analysis uses the decision-first simplified hierarchy and does not duplicate the full Decision Motor.
- Account/Admin, Strategy Lab, responsive/mobile foundations, and recent simplification work are no longer described as future implementation work.
- Open debt is narrowed to final copy/semantics, scan preset layout polish, Projection simplification, ESLint gate, Starlette/httpx deprecation handling, and real viewport/keyboard acceptance.

CP0 changes documentation only.

### CP1 — Copy and Semantic Consistency

Correct user-facing copy without changing calculations or behavior.

- Performance horizon copy must match the actual selectable `1 / 5 / 10 / 20 / 45G` horizons.
- Projection confidence must be presented as a model confidence score `/100`, never as a measured probability or `%` success likelihood.
- Piyasa Merkezi must describe the featured security and comparison list as coming from the latest completed scan, not as a generic `LIVE`/today claim.
- Remove implementation-stack jargon such as FastAPI, Next.js, Firebase token, or UID from ordinary user-facing product copy while keeping Admin QA technically explicit.
- Standardize ordinary navigation/product naming on `Strateji Lab`.

### CP2 — Smart Scan Preset Layout Polish

Keep the current Smart Scan behavior and hierarchy intact while fixing the visual balance of four quick universe cards.

- Desktop: four balanced quick-preset cards in one row when space allows.
- Tablet: 2 x 2.
- Mobile: safe responsive stacking without overflow.
- Preserve Decision Motor -> filters -> result table order.
- Preserve scan settings collapse/reopen behavior and symbol-list controls.

After CP2, Smart Scan is considered design-closed unless a real defect appears in acceptance.

### CP3 — Projection Decision-First Simplification

Reduce visible information density while preserving every existing model output and Python calculation.

Default-visible content should prioritize:

- selected ticker and current price
- 45G movement band
- model confidence score `/100`
- algorithmic direction summary
- positive scenario trigger/target/risk invalidation
- negative scenario trigger/downside/invalidation

Move secondary model-comparison detail and repeated technical levels into disclosures. Do not modify `projection_engine.py` calculations or the 45-day model.

### CP4 — ESLint Quality Gate

Make the existing `pnpm --dir web lint` script operational under ESLint 9 / Next.js 16 and add it to the Web CI gate before typecheck/tests/build.

Use minimal fixes only; no unrelated refactor.

### CP5 — TestClient Deprecation Cleanup

Investigate the current Starlette/httpx TestClient deprecation warning and apply a safe dependency/test migration only if the supported path is clear and behavior-preserving.

If a safe migration is not currently available, keep behavior unchanged and record the remaining debt explicitly instead of forcing a risky dependency change.

### CP6 — Real Viewport, Keyboard, and Release Acceptance

Run the final authenticated product journey at:

- 390 x 844
- 768 x 1024
- 1440 x 900

Verify:

- no horizontal overflow or clipped copy
- mobile navigation and `Diğer` menu
- disclosure controls
- modal Escape/focus return
- auth form focus/error behavior
- Smart Scan Decision Motor/filter/table hierarchy
- ticker continuity into Detailed Analysis and Projection
- Performance mobile cards and period controls
- Account export/delete surfaces without performing routine destructive deletion
- latest-scan language in Piyasa Merkezi

Any real defect found in CP6 should be fixed in a narrowly scoped `fix/final-acceptance-*` PR rather than accumulating unrelated changes in one acceptance branch.

Final release closure requires green CI, production exact-SHA verification, durable readiness, runtime error check, and final canonical status update.

## Explicitly Out of Scope

- new financial indicators
- new scan universes beyond the existing supported profiles
- changes to central decision logic
- new Projection model mathematics
- full CSS architecture refactor
- mobile-native application work
- broad product redesign
- speculative feature expansion before real-user feedback

## Completion Definition

When CP0 through CP6 are closed, the Next.js/FastAPI web product is considered **IZFIN web v1 user-acceptance ready**. Subsequent work should prioritize observed real-user feedback over adding more surface area by default.
