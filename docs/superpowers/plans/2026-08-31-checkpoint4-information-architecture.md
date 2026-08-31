# Checkpoint 4 Information Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the stock-specific Decision Motor the single central decision surface, remove repeated decision prose from Detailed Analysis, align Advanced Score bands to the approved canonical thresholds, and keep guidance strictly page-specific.

**Architecture:** Keep the existing shared analysis context and Python-owned financial contracts unchanged. The scan surface owns directional decision language; the detail surface consumes the same job/ticker but only expands score mechanics, technical indicators, levels, targets, and algorithmic technical commentary. `UsageGuide` remains a single route-aware component, but its copy and route mapping must exactly match the Checkpoint 4 surface responsibilities.

**Tech Stack:** Next.js App Router, React/TypeScript, existing IZFIN shared analysis context, CSS, Python pytest source-contract tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-web-completion-program-design.md` — Section 7, Checkpoint 4.

## Global Constraints

- `main` is never touched.
- Base is the current `develop` merge SHA `a4df8ef8051f302a16ed7bd11e35010e1714eb31`.
- No Checkpoint 5 visual-system rewrite is pulled forward.
- No financial calculation or decision logic is moved from Python services into React.
- Existing auth recovery, same-origin API proxy, job ownership, scan recovery, durable readiness, selected-job/ticker context, and Checkpoint 3 selection fix must not regress.
- Streamlit remains the canonical product/design reference.
- Every behavior change follows TDD RED → GREEN.
- ESLint flat config is Checkpoint 7 scope and is not added here; existing typecheck/build and repository tests are mandatory.
- `main` remains untouched; merge target is `develop` only after both GitHub CI gates are green.

---

### Task 1: Decision Motor becomes the single directional decision surface

**Files:**
- Modify: `web/components/scan-decision-card.tsx`
- Modify: `web/app/scan.css`
- Test: `tests/test_checkpoint4_information_architecture.py`
- Test: `tests/test_web_scan_detail_flow_contract.py`

**Interfaces:**
- Consumes: `StockDetailResponse`, `useAnalysisContext()`, `onTickerChange(ticker: string)`.
- Produces: one scan Decision Motor whose central verdict and balanced positive/risk reasons are primary; confidence, entry quality, MTF, risk, and technical levels remain secondary; table row and dropdown continue using the same shared ticker owner.

- [ ] **Step 1: Write RED contracts**

Add tests asserting that the scan card contains the central decision block before secondary KPI/level sections, preserves both reason panels, keeps selector ownership on `sharedSelectedTicker`, and does not reintroduce any `setSelectedTicker(detail.ticker)` write-back.

```python
def test_checkpoint4_scan_decision_motor_is_the_single_primary_decision_surface():
    card = _read("web/components/scan-decision-card.tsx")
    assert card.index("scan-decision-verdict") < card.index("scan-decision-kpis")
    assert card.index("scan-decision-verdict") < card.index("scan-decision-levels")
    assert "Neden alınabilir?" in card
    assert "Neden beklenmeli / alınmamalı?" in card
    assert "selectedTicker: sharedSelectedTicker" in card
    assert "setSelectedTicker(detail.ticker)" not in card
```

- [ ] **Step 2: Run RED test**

Run the new Checkpoint 4 test in CI. It must fail only where current information hierarchy/copy does not yet satisfy the exact contract.

- [ ] **Step 3: Apply the minimal scan-card hierarchy change**

Keep the selector and shared state unchanged. Make the central verdict the strongest semantic block, keep positive and risk reasons balanced, and move confidence / entry quality / MTF / risk / technical levels into secondary sections without creating a second decision model.

- [ ] **Step 4: GREEN the focused tests**

Run the new Checkpoint 4 tests plus `tests/test_web_scan_detail_flow_contract.py` and confirm the selection stabilization contract remains green.

- [ ] **Step 5: Commit**

Commit as `fix(checkpoint4): centralize scan decision hierarchy`.

---

### Task 2: Detailed Analysis removes decision duplication and uses canonical score bands

**Files:**
- Modify: `web/components/stock-detail-page.tsx`
- Modify: `web/app/stock-detail.css`
- Test: `tests/test_checkpoint4_information_architecture.py`
- Align only stale expectations in: `tests/test_web_scan_detail_flow_contract.py`, `tests/test_web_design_system.py`

**Interfaces:**
- Consumes: the same `StockDetailResponse` and job/ticker route context.
- Produces: a detail screen containing short context summary, Advanced Score mechanics, indicators, trend/momentum, support/resistance, multi-timeframe entry context, stop/targets through the structured technical/panel data, algorithmic technical commentary, and Projection handoff — but no long central-decision explanation or duplicated positive/risk prose.

- [ ] **Step 1: Write RED contracts for deduplication and score bands**

```python
def test_checkpoint4_detail_uses_canonical_score_bands_and_no_decision_duplication():
    detail = _read("web/components/stock-detail-page.tsx")
    assert "parsed < 50" in detail
    assert "parsed < 70" in detail
    assert "Cezalı" in detail
    assert "Nötr" in detail
    assert "Güçlü" in detail
    for obsolete in ("Zayıf", "Dengeli", "Olumlu", "Çok Güçlü"):
        assert obsolete not in detail
    assert "80 puan, %80 başarı ihtimali anlamına gelmez" in detail
    assert "risk" in detail.lower()
    assert "merkezi" in detail.lower()
```

Add source contracts ensuring Detailed Analysis does not render the Decision Motor’s long positive/risk explanation components and retains `TechnicalOverview`, `ScoreBreakdown`, and `projectionHref`.

- [ ] **Step 2: Run RED test**

Expected failure: the current score bands are `<30 Cezalı`, `<50 Zayıf`, `<65 Dengeli`, `<80 Olumlu`, `<90 Güçlü`, otherwise `Çok Güçlü`.

- [ ] **Step 3: Implement canonical score semantics**

Use exactly:

```ts
if (parsed < 50) return { label: "Cezalı", ... };
if (parsed < 70) return { label: "Nötr", ... };
return { label: "Güçlü", ... };
```

The explanations must explicitly state that score is not an automatic `AL`, not a success probability, and can be limited by risk and the central Decision Motor.

- [ ] **Step 4: Simplify detail copy without deleting technical depth**

Retain the concise hero context, price/score summary, Projection CTA, score breakdown (old score, bonuses, penalties, final score, per-item reasons), technical indicators, trend/momentum, support/resistance, multi-timeframe entry context, targets and algorithmic commentary. Do not add directional recommendation prose.

- [ ] **Step 5: Adjust only touched CSS semantics**

Collapse score-band styling to three semantic states (`penalized`, `neutral`, `strong`) without a Checkpoint 5 token/refactor sweep.

- [ ] **Step 6: GREEN focused tests and commit**

Run the new Checkpoint 4 tests and existing detail/design contracts. Commit as `fix(checkpoint4): simplify detail and canonicalize score bands`.

---

### Task 3: Route-aware page-specific guidance matches Checkpoint 4

**Files:**
- Modify: `web/components/usage-guide.tsx`
- Test: `tests/test_checkpoint4_information_architecture.py`
- Align only stale expectations in: `tests/test_web_scan_detail_flow_contract.py`, `tests/test_web_design_system.py`

**Interfaces:**
- Consumes: `usePathname()`.
- Produces: guidance only for Market Center, Smart Scan, Detailed Analysis, Projection, Performance and Strategy Lab; no financial guide for Account, Auth, legal, or Admin QA surfaces.

- [ ] **Step 1: Write RED route/copy contracts**

Assert exact surface routing and responsibilities:
- Market: market mode + highlighted names.
- Scan: universe + central decision + confirmation + risk.
- Detail: score + indicators + technical levels.
- Projection: bands + conditional scenarios.
- Performance: active/closed positions + scorecard interpretation.
- Strategy Lab: backtest + sample size + table interpretation.
- `/account`, `/admin`, `/auth`, `/legal/*`: no `UsageGuideSurface` mapping.

- [ ] **Step 2: Run RED test**

Expected failures must correspond only to copy/responsibility mismatches, not route rendering regressions.

- [ ] **Step 3: Update guide copy**

Keep the existing closed-by-default `<details className="usage-guide">` interaction. Remove any wording that teaches obsolete score bands or duplicates directional decision interpretation on Detailed Analysis. Ensure `Account` and `Admin QA` remain unmapped.

- [ ] **Step 4: GREEN guide contracts and commit**

Commit as `fix(checkpoint4): align page specific usage guides`.

---

### Task 4: Checkpoint 4 integration gates, PR, merge and live acceptance

**Files:**
- Test: complete repository test suite and web quality gate.
- No unrelated production files.

**Interfaces:**
- Produces: one independently reviewable Checkpoint 4 PR targeting `develop`.

- [ ] **Step 1: Run full Python suite**

Run `python -m pytest -q` through GitHub CI and require zero failures.

- [ ] **Step 2: Run web gates**

Require `pnpm typecheck` and `pnpm build` success. If lint remains blocked by the pre-existing ESLint 9 flat-config absence, report it explicitly and do not add Checkpoint 7 configuration here.

- [ ] **Step 3: Review diff scope**

Changed production files must be limited to Checkpoint 4 information-architecture surfaces plus narrowly necessary tests/docs. Verify there are no auth, API, backend financial logic, Checkpoint 5 visual-system, or Checkpoint 6 mobile-navigation changes.

- [ ] **Step 4: Open PR to `develop`**

PR body records RED run, GREEN run, canonical score thresholds, deduplication boundaries, and no-regression guarantees for selected ticker state.

- [ ] **Step 5: Merge only after both CI gates are green**

Use expected head SHA; never target `main`.

- [ ] **Step 6: Verify post-merge `develop` CI**

Require both Python and Web jobs to finish `success` on the merge SHA.

- [ ] **Step 7: Verify Vercel production deployment**

Require the production deployment to be `READY`, branch `develop`, and Git SHA equal to the merge SHA. Smoke-test `/scan` and a public/protected shell route without fabricating authentication.

- [ ] **Step 8: User live acceptance**

Acceptance checklist:
1. Scan Decision Motor is the obvious central decision surface.
2. Changing table/dropdown ticker still changes the analyzed stock.
3. Detailed Analysis no longer repeats long decision reasons.
4. Score bands show only `<50 Cezalı`, `50–69 Nötr`, `>=70 Güçlü`.
5. Score explanation states it is not an automatic buy or success probability.
6. Each supported page shows only its own closed-by-default guide; Account/Admin show no financial guide.

## Self-review

- Spec coverage: all Checkpoint 4 subsections are assigned to Tasks 1–3; integration/live acceptance is Task 4.
- Placeholder scan: no TBD/TODO/future implementation placeholders.
- Type consistency: existing `StockDetailResponse`, `useAnalysisContext`, `UsageGuideSurface`, and route ownership are preserved; no new backend contract is introduced.
- Scope check: Checkpoint 5 typography/token cleanup and Checkpoint 6 responsive redesign are explicitly excluded.