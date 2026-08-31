# Checkpoint 5 Design System & Visual Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the web client onto the approved IZFIN visual system without changing financial behavior: one canonical brand asset, readable typography, shared design tokens/card geometry, and visible keyboard focus.

**Architecture:** Keep the existing Next.js component structure and the existing Streamlit-derived dark visual language. Strengthen `globals.css` as the token/focus baseline, keep `/brand/izfin-logo.png` as the only brand image, and migrate only the high-value surfaces touched by this checkpoint rather than rewriting all CSS. Financial/API/auth behavior is out of scope.

**Tech Stack:** Next.js, React, CSS, pytest source-contract tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-web-completion-program-design.md` — Checkpoint 5.

## Global Constraints

- `main` is never modified.
- Base is the latest `develop` commit.
- No financial calculations move to React.
- No fake/mock financial data is introduced.
- No Checkpoint 6 mobile navigation redesign is pulled forward.
- No Checkpoint 7 ESLint flat-config work is pulled forward.
- CSS migration is incremental; no repo-wide one-shot rewrite.
- Streamlit remains the canonical product/brand reference.

---

### Task 1: Shared token, typography, card and focus baseline

**Files:**
- Modify: `web/app/globals.css`
- Test: `tests/test_checkpoint5_design_system_parity.py`

**Interfaces:**
- Produces shared CSS variables for background/elevated surfaces, line, primary/secondary text, positive, warning, risk, information, card padding/radius and focus ring.
- Produces shared heading/text size variables used by touched surfaces.

- [ ] **Step 1: Write failing contracts** requiring the shared semantic tokens, 30–44px page-title scale, 20–28px section-title scale, >=13px normal body token, and `:focus-visible` coverage for links, buttons, inputs, selects, textareas and summaries.
- [ ] **Step 2: Run the Checkpoint 5 contract tests** and verify the new assertions fail on the current branch.
- [ ] **Step 3: Add the minimal token/focus baseline** to `globals.css`, reusing existing IZFIN colors instead of inventing a second palette.
- [ ] **Step 4: Re-run the contracts** and keep only the intended remaining RED items for later tasks.

### Task 2: Canonical brand parity

**Files:**
- Modify: `web/app/brand-scan-visibility.css`
- Modify: `web/components/home-decision-center.tsx`
- Verify: `web/components/izfin-brand-mark.tsx`
- Verify: `web/app/layout.tsx`
- Verify: `web/components/app-shell.tsx`
- Verify: `web/components/auth-page.tsx` / auth gate surfaces that use `IzfinBrandMark`
- Test: `tests/test_checkpoint5_design_system_parity.py`

**Interfaces:**
- Canonical asset remains `/brand/izfin-logo.png`.
- `IzfinBrandMark` remains the shared React brand component.

- [ ] **Step 1: Add RED assertions** that the shared mark and metadata use `/brand/izfin-logo.png`, the mark is circular with a substantial ring, context sizes remain centered, and the Market Center page title is `Piyasa Merkezi` rather than a textual IZ/IZFIN prefix.
- [ ] **Step 2: Run RED contracts.**
- [ ] **Step 3: Implement minimal brand CSS and title copy changes.** Keep the same image asset; do not introduce a second logo.
- [ ] **Step 4: Run the contracts GREEN.**

### Task 3: Readability and card hierarchy on primary surfaces

**Files:**
- Modify: `web/app/globals.css`
- Modify: `web/app/market-center.css`
- Modify: `web/app/auth-legal-gate.css`
- Modify as required by RED findings: `web/app/scan.css`, `web/app/stock-detail.css`
- Test: `tests/test_checkpoint5_design_system_parity.py`

**Interfaces:**
- High-value surface labels use shared semantic text colors and card variables.
- User-facing 7–8px text is removed from the touched surfaces.
- Critical positive/warning/risk states retain textual labels/font emphasis in addition to color.

- [ ] **Step 1: Add RED assertions** that touched primary CSS does not use 7px/8px user-facing typography and that primary cards consume the shared radius/padding/line/surface tokens.
- [ ] **Step 2: Run RED contracts.**
- [ ] **Step 3: Increase microcopy to readable label/body sizes, standardize card padding/radius, and replace duplicated touched-surface colors with semantic tokens where behavior is unchanged.**
- [ ] **Step 4: Re-run Checkpoint 5 contracts GREEN.**

### Task 4: Full verification, PR and production acceptance

**Files:**
- No new product scope.

- [ ] **Step 1: Run the complete Python suite.**
- [ ] **Step 2: Run Next.js typecheck and production build through the Web Quality Gate.**
- [ ] **Step 3: Treat `pnpm lint` only as a preflight.** If blocked by missing ESLint 9 flat config, record it as the already-planned Checkpoint 7 item; do not add config here.
- [ ] **Step 4: Inspect PR changed files** and reject Checkpoint 6/7 scope leakage.
- [ ] **Step 5: Merge only after both CI gates are green, using expected head SHA.**
- [ ] **Step 6: Verify post-merge `develop` CI.**
- [ ] **Step 7: Verify Vercel production is READY on the exact merge SHA and smoke-test the stable URL.**
- [ ] **Step 8: Live acceptance:** check Market Center, Smart Scan, Detailed Analysis and auth/legal surfaces for logo consistency, readable type hierarchy, card consistency, contrast and keyboard focus.
