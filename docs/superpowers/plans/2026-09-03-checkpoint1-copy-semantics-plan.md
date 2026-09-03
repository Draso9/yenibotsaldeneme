# Checkpoint 1 Copy and Semantic Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make user-facing copy truthful and internally consistent across Performance, Projection, Piyasa Merkezi, account/auth surfaces, and Strategy Lab without changing any product calculation or workflow behavior.

**Architecture:** This checkpoint is presentation-only. Existing React components keep their data flow and interactions; only visible labels/help/error copy change. A focused source-contract test is written first so the old wording produces an intentional RED before production strings are changed.

**Tech Stack:** Next.js 16, React 19, TypeScript, Python/pytest source-contract tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md`

## Global Constraints

- Never touch `main`.
- Base CP1 on `develop` at `92cf5526b475cffd82bddcc5454dea9274a8fac6`.
- No financial calculations or central decision rules change.
- No API payload, auth behavior, recovery, scan, readiness, or ticker-continuity behavior change.
- Do not modify `izfin_core/projection_engine.py`.
- Admin QA may retain technical implementation terminology; ordinary user surfaces should not expose framework/provider internals unnecessarily.
- Standard ordinary product naming: `Strateji Lab`.

---

### Task 1: Add the CP1 semantic copy contract

**Files:**
- Create: `tests/test_final_polish_copy_contract.py`

**Interfaces:**
- Consumes: literal user-facing source strings from current web components.
- Produces: regression contract for truthful horizons, confidence semantics, latest-scan wording, and user-safe product language.

- [ ] **Step 1: Write the failing contract**

Create tests that require:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_performance_horizon_copy_matches_actual_selector():
    source = read("web/components/performance-view.tsx")
    assert "1 / 5 / 10 / 20 / 45G" in source
    assert "20G / 60G / 120G" not in source


def test_projection_confidence_is_a_score_not_probability_like_percent():
    source = read("web/components/projection-model-view.tsx")
    guide = read("web/components/usage-guide.tsx")
    assert "Model güven skoru" in source or "Model Güven Skoru" in source
    assert "Güven %" not in source
    assert "Model güveni %" not in source
    assert "Olasılık, merkez yol" not in guide


def test_market_center_copy_truthfully_refers_to_latest_scan():
    source = read("web/components/market-center.tsx")
    assert "Son taramada dikkat çekenler" in source
    assert "SON TARAMADA ÖNE ÇIKAN" in source
    assert "BUGÜNÜN ÖNE ÇIKAN HİSSESİ" not in source
    assert "<b>LIVE</b>" not in source


def test_ordinary_user_surfaces_hide_stack_and_provider_jargon():
    shell = read("web/components/app-shell.tsx")
    account = read("web/components/account-page.tsx")
    auth = read("web/components/auth-page.tsx")
    strategy = read("web/components/strategy-lab-page.tsx")
    assert "FastAPI · Next.js" not in shell
    assert '"Strateji Laboratuvarı"' not in shell
    assert "Firebase hesabın" not in account
    assert "Firebase ID token" not in account
    assert "UID ve e-postasıyla" not in account
    assert "Firebase Auth · kişisel veri alanı" not in auth
    assert "Firebase ayarlarını kontrol etmelisin" not in auth
    assert "STRATEJİ LABORATUVARI" not in strategy
```

- [ ] **Step 2: Verify RED**

Run the focused pytest contract in CI or locally:

```bash
python -m pytest tests/test_final_polish_copy_contract.py -q
```

Expected result: FAIL because the old Performance horizon, Projection `%` wording, Piyasa Merkezi `LIVE`/today wording, stack/provider jargon, and Strategy Lab naming are still present.

### Task 2: Correct Performance and Projection semantics

**Files:**
- Modify: `web/components/performance-view.tsx`
- Modify: `web/components/projection-model-view.tsx`
- Modify: `web/components/usage-guide.tsx`
- Test: `tests/test_final_polish_copy_contract.py`

**Interfaces:**
- Consumes: existing `scorecard.gun` and `projection.model.guven_skoru` values unchanged.
- Produces: truthful visible copy only.

- [ ] **Step 1: Align Performance copy**

Replace the obsolete explanatory horizon text with:

```text
1 / 5 / 10 / 20 / 45G seçimi yalnızca sinyal sonrası ölçüm ufkunu değiştirir.
```

Do not alter selector constants, API calls, or scorecard calculations.

- [ ] **Step 2: Standardize Projection confidence**

Keep the existing hero label `Model Güven Skoru` and `/100` presentation. Replace secondary percent-like forms with `/100`, for example:

```text
Model güven skoru 78/100
```

Do not alter `guven_skoru` calculation or `model_uyumu` percentage.

- [ ] **Step 3: Remove probability-like guide wording**

Replace the Projection note beginning `Olasılık, merkez yol...` with wording centered on the model path, bands, and conditional scenarios.

- [ ] **Step 4: Re-run focused contract**

Expected: the Performance/Projection assertions are GREEN; other CP1 assertions may still fail until later tasks are implemented.

### Task 3: Make Piyasa Merkezi freshness language truthful

**Files:**
- Modify: `web/components/market-center.tsx`
- Test: `tests/test_final_polish_copy_contract.py`

**Interfaces:**
- Consumes: latest-completed-scan market center data exactly as today.
- Produces: copy that describes the actual data source without implying live/today freshness.

- [ ] **Step 1: Rename comparison list**

Use `Son taramada dikkat çekenler` for the subsection label and corresponding aria label.

- [ ] **Step 2: Rename featured result**

Use `SON TARAMADA ÖNE ÇIKAN` and remove the misleading `LIVE` badge. If the layout needs a badge placeholder, `SON TARAMA` is acceptable because it describes provenance rather than freshness.

- [ ] **Step 3: Re-run focused contract**

Expected: Piyasa Merkezi assertions GREEN.

### Task 4: Remove implementation jargon from ordinary user surfaces and standardize Strategy Lab

**Files:**
- Modify: `web/components/app-shell.tsx`
- Modify: `web/components/account-page.tsx`
- Modify: `web/components/auth-page.tsx`
- Modify: `web/components/strategy-lab-page.tsx`
- Test: `tests/test_final_polish_copy_contract.py`

**Interfaces:**
- Consumes: existing Firebase auth implementation and system readiness behavior unchanged.
- Produces: user-oriented product language; technical internals remain internal/Admin QA.

- [ ] **Step 1: App shell**

Use `Strateji Lab` for the strategy route page label and replace `FastAPI · Next.js · güvenli oturum` with user-facing system/session language such as `Güvenli oturum · sistem bağlantısı`.

- [ ] **Step 2: Account page**

Use `IZFIN hesabın` instead of `Firebase hesabın`. Rewrite the security explanation so it says account actions are protected by secure identity verification and deletion applies only to the verified user's own account/email, without exposing token/UID implementation language.

- [ ] **Step 3: Auth page**

Keep internal Firebase imports/functions untouched. Rewrite visible setup/error/footer messages so users receive actionable guidance without Firebase provider/configuration jargon.

Preserve the stable fallback host guidance for unauthorized Google-domain errors.

- [ ] **Step 4: Strategy Lab page**

Use `STRATEJİ LAB` / `IZFIN Strateji Lab` on ordinary user-facing headings/aria copy instead of `STRATEJİ LABORATUVARI`.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
python -m pytest tests/test_final_polish_copy_contract.py -q
```

Expected: PASS.

### Task 5: Full regression, PR, merge, and release verification

**Files:**
- Verify all CP1 files only.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: merged CP1 with no behavior changes outside user-facing semantics.

- [ ] **Step 1: Run complete project tests through CI**

Required gates:

```text
IZFIN Quality Gate
IZFIN Web Quality Gate
```

Web gate must still pass typecheck, component behavior tests, and production build.

- [ ] **Step 2: Review changed-file scope**

Expected production files are limited to the seven user-facing components above plus the focused test and this plan. No Python financial/core/service files should change.

- [ ] **Step 3: Open PR to `develop`**

Title:

```text
fix(copy): align final product semantics
```

- [ ] **Step 4: Merge only after both PR gates are green**

Use squash merge; verify the exact merge SHA is the new `develop` head.

- [ ] **Step 5: Verify post-merge CI and Vercel production exact SHA**

Because CP1 changes deployed web code, verify both post-merge CI gates and the production deployment metadata/alias for the exact merge SHA before declaring CP1 closed.

- [ ] **Step 6: Continue to CP2**

Next checkpoint:

```text
CP2 — Smart Scan Preset Layout Polish
```
