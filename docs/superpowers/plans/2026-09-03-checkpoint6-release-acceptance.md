# Checkpoint 6 Release Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Checkpoint 6 real-browser release acceptance gates without changing financial calculations, API contracts, auth semantics, scan semantics, projection semantics, or Streamlit behavior.

**Architecture:** Run the production Next.js application in a real Chromium browser at the three canonical viewports, exercise public and authenticated UI paths, and verify keyboard/focus/modal behavior from the rendered DOM. Any confirmed defect is fixed at the smallest presentation/accessibility boundary and guarded by a focused regression test. Release evidence is recorded in the existing CP6 review document.

**Tech Stack:** Next.js App Router, React, native `<dialog>`, CSS responsive layers, Firebase Auth, Playwright/Chromium for acceptance, existing Node component behavior tests, GitHub Actions, Vercel.

**Spec:** `docs/superpowers/reviews/2026-09-01-checkpoint6-release-check.md`

## Global Constraints

- Work from `develop`; never modify `main`.
- Preserve Streamlit behavior and existing Next.js/FastAPI contracts.
- Do not change financial calculations, provider request logic, scan/recovery semantics, projection semantics, auth/legal semantics, or API response shapes.
- Use TDD RED → GREEN for every code defect fixed.
- Both IZFIN Python and Web Quality Gates must be green before merge.
- Verify the exact post-merge `develop` SHA in Vercel production and run a live health smoke check.

---

### Task 1: Production viewport acceptance

**Files:**
- Modify after verification: `docs/superpowers/reviews/2026-09-01-checkpoint6-release-check.md`
- Inspect only unless a defect is confirmed: `web/app/responsive.css`, `web/app/globals.css`, `web/components/mobile-navigation.tsx`, route-specific CSS files.

**Interfaces:**
- Consumes: production `https://izfin-web.vercel.app`, current responsive CSS and navigation components.
- Produces: pass/fail evidence for 390×844, 768×1024, and 1440×900.

- [ ] **Step 1: Run 390×844 acceptance**

Use real Chromium to inspect the auth/public surfaces and authenticated workspace. Verify no horizontal overflow, no clipped primary actions, mobile navigation does not cover content, legal text remains readable, and interactive controls remain at least practically tappable.

- [ ] **Step 2: Run 768×1024 acceptance**

Verify tablet layout, navigation transition, cards/tables, guide content, legal pages, and primary actions without horizontal clipping or overlapping fixed navigation.

- [ ] **Step 3: Run 1440×900 acceptance**

Verify desktop sidebar/topbar/content geometry, result tables, projection/performance panels, and legal/auth surfaces without unexpected overflow or layout collisions.

- [ ] **Step 4: Record evidence**

Append the tested viewport matrix, routes exercised, and concrete pass/fail observations to `docs/superpowers/reviews/2026-09-01-checkpoint6-release-check.md`.

### Task 2: Keyboard, modal, and focus acceptance

**Files:**
- Inspect/fix if needed: `web/components/modal-surface.tsx`
- Inspect/fix if needed: `web/components/scan-workspace.tsx`
- Inspect/fix if needed: `web/components/auth-page.tsx`
- Inspect/fix if needed: `web/components/usage-guide.tsx`
- Test if a defect is found: `web/tests/*.test.mjs` or the nearest existing component behavior test file.

**Interfaces:**
- Consumes: native `<dialog>` behavior, existing `data-modal-focus` convention, form error focus behavior, skip-link/main-content focus target.
- Produces: verified Escape close, background isolation, focus entry/return, keyboard-reachable controls, and form-error focus relationships.

- [ ] **Step 1: Verify modal keyboard behavior**

Open the scan progress/result modal from keyboard-accessible controls, confirm focus moves inside, `Escape` triggers dismiss when dismissible, the page behind the modal is inert to keyboard interaction, and focus returns to the invoking element or `#main-content` fallback.

- [ ] **Step 2: Verify auth form errors**

Submit login/register/reset forms with invalid input using keyboard only. Confirm the error summary receives focus, invalid controls expose `aria-invalid`, and the error relation is exposed through `aria-describedby`.

- [ ] **Step 3: Verify guides and legal navigation**

Open/close the route usage guide and navigate the public legal pages using keyboard only. Confirm visible focus remains usable and no fixed layer hides the focused control.

- [ ] **Step 4: Record evidence**

Update the CP6 review document with the keyboard/focus matrix and any known limitation.

### Task 3: Minimal remediation for confirmed defects

**Files:**
- Modify only the exact component/CSS file responsible for a reproduced defect.
- Add or update one focused regression test per defect.

**Interfaces:**
- Consumes: a reproducible browser failure from Task 1 or Task 2.
- Produces: smallest behavior-preserving fix plus RED → GREEN regression evidence.

- [ ] **Step 1: Add failing regression test**

Encode the reproduced defect at the nearest existing component-contract layer. The test must fail for the same reason observed in Chromium.

- [ ] **Step 2: Run the focused test and confirm RED**

Run only the new/changed test first and confirm the expected failure.

- [ ] **Step 3: Implement minimal fix**

Change only presentation/accessibility code required to satisfy the reproduced case. Do not broaden scope into redesign or refactor.

- [ ] **Step 4: Run focused and relevant regression tests**

Confirm GREEN for the defect test and nearest related component behavior tests.

### Task 4: Release verification and closure

**Files:**
- Finalize: `docs/superpowers/reviews/2026-09-01-checkpoint6-release-check.md`

**Interfaces:**
- Consumes: final branch head, browser acceptance evidence, focused tests.
- Produces: PR → `develop`, exact merge SHA, post-merge CI proof, production Vercel SHA proof, live health smoke.

- [ ] **Step 1: Run final branch verification**

Require the complete IZFIN Python Quality Gate and Web Quality Gate to pass on the final PR head; Web must include lint, typecheck, component behavior tests, and production build.

- [ ] **Step 2: Review the final diff**

Confirm only CP6 acceptance documentation, focused tests, and confirmed presentation/accessibility fixes are present.

- [ ] **Step 3: Squash merge to `develop`**

Merge only after both gates are green and the browser acceptance matrix has no unresolved release blocker.

- [ ] **Step 4: Verify post-merge release state**

Confirm `develop` points to the merge SHA, post-merge Python/Web CI is green, Vercel production is READY on that exact SHA, and `/izfin-api/api/v1/health` returns HTTP 200 with `status=ok`.
