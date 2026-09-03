# Checkpoint 3 Projection Decision-First Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce default-visible Projection information density while keeping every existing projection output, data source, and Python calculation intact.

**Architecture:** Keep `ProjectionPage` as the existing auth/context/data-fetch boundary and change only the presentation renderer plus narrowly scoped Projection CSS. The first glance becomes ticker/current price + 45G range + confidence + direction + positive/negative scenarios; model comparison, full band cards, and repeated technical levels remain available inside native disclosures.

**Tech Stack:** Next.js 16, React, TypeScript, CSS, Python source-contract tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md`

## Global Constraints

- Never touch `main`.
- Base on accepted `develop` SHA `f1998eca3a48128631266bb88cf0dae621e0327d`.
- Do not modify `izfin_core/projection_engine.py`, projection API payload semantics, auth/context recovery, or the 45-day model.
- Preserve all existing projection outputs; move secondary/repeated outputs rather than removing them.
- Use native `<details>/<summary>` disclosures; no broad CSS refactor.
- TDD RED -> GREEN and both Python/Web quality gates must pass before merge.

---

### Task 1: Define the decision-first presentation contract

**Files:**
- Create: `tests/test_projection_decision_first_contract.py`

**Interfaces:**
- Consumes: source structure of `web/components/projection-model-view.tsx`.
- Produces: a bounded contract that requires the primary information to precede secondary disclosures and proves secondary outputs remain present.

- [ ] **Step 1: Write failing source-contract tests**

Require named primary wrappers for hero, range, direction, and scenarios; require those wrappers to appear before disclosures; require disclosure labels `Model karşılaştırması ve fiyat bantları` and `Teknik seviyeler ve model ayrıntıları`; require model metrics/bands and technical-level fields to remain represented.

- [ ] **Step 2: Run RED verification**

Run the repository Python test suite in GitHub Actions. Expected: only the new CP3 contract fails because the current renderer has no CP3 primary wrappers/disclosures.

### Task 2: Recompose Projection first glance

**Files:**
- Modify: `web/components/projection-model-view.tsx`

**Interfaces:**
- Consumes: unchanged `ProjectionResponse` and existing renderer props.
- Produces: decision-first presentation with all current model data preserved.

- [ ] **Step 1: Keep one compact primary hero**

Retain the existing lab identity strings, selected ticker/switcher, current price, 45G model context, and `Model Güven Skoru X/100` without maintaining a separate introductory panel.

- [ ] **Step 2: Put the 45G movement band immediately after the hero**

Use the existing range track and values; keep `Karma Model` movement visible as secondary context but do not duplicate the entire band-card set here.

- [ ] **Step 3: Keep algorithmic direction next**

Render `projection.scenario.yon`, `yon_title`, and `model_yorumu` as the next primary decision surface while retaining signal/confidence/model-agreement context.

- [ ] **Step 4: Keep positive and negative scenarios default-visible**

Positive: trigger, technical targets, upper model bands, risk invalidation. Negative: trigger, lower model bands, invalidation.

- [ ] **Step 5: Move secondary outputs into disclosures**

Disclosure 1 contains Model Comparison, `projection.metrics.birincil`, `projection.metrics.ikincil`, full `projection.bands`, and volatility explanation. Disclosure 2 contains support, resistance, stop, TP1, TP2, and model difference.

- [ ] **Step 6: Keep model-scope disclaimer visible**

Preserve the no-guarantee / not-investment-advice language.

### Task 3: Add narrow disclosure/primary-layout styling

**Files:**
- Modify: `web/app/projection.css`

**Interfaces:**
- Consumes: new renderer wrapper/disclosure class names.
- Produces: compact desktop/mobile presentation using existing visual tokens.

- [ ] **Step 1: Style primary wrappers using existing Projection cards**

Avoid new visual system concepts; only spacing/layout adjustments needed for the new source order.

- [ ] **Step 2: Style native disclosures**

Give summary controls keyboard-visible focus, at least a comfortable click target, and collapsed-by-default presentation. Ensure inner grids retain existing responsive behavior.

### Task 4: GREEN and release verification

**Files:**
- Verify only; no model/API edits expected.

**Interfaces:**
- Produces: verified CP3 PR suitable for `develop`.

- [ ] **Step 1: Run full Python/Web CI**

Expected: complete Python suite, Next.js typecheck, component behavior checks, and production build pass.

- [ ] **Step 2: Confirm PR diff boundaries**

Expected changed implementation files: renderer + Projection CSS, plus CP3 test/plan. `izfin_core/projection_engine.py`, projection routes/contracts, and context resolver remain unchanged.

- [ ] **Step 3: Merge to `develop` only after green gates**

Use squash merge with expected head SHA.

- [ ] **Step 4: Verify post-merge `develop` CI and Vercel production exact SHA**

Checkpoint is complete only when both CI gates pass on the merge SHA and the production deployment reports that exact SHA as READY.
