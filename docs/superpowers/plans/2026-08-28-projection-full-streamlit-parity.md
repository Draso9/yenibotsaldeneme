# Projection Full Streamlit Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Projection functional-parity checkpoint by making the Next.js Projection experience preserve the complete Streamlit 45-day model content and information hierarchy while keeping the existing authenticated context-recovery behavior.

**Architecture:** Keep all projection calculations in Python (`izfin_core`, `izfin_ui`, `izfin_services`) and the existing FastAPI contract. `ProjectionPage` remains responsible for authenticated job/ticker context resolution and data fetching; a focused renderer component owns the real projection presentation. Do not add fake data or duplicate projection calculations in React.

**Tech Stack:** Python 3.14, FastAPI, pytest, Next.js App Router, React, TypeScript, existing CSS design system.

**Spec:** `docs/superpowers/specs/2026-08-27-streamlit-full-parity-migration-design.md`

## Global Constraints

- Never touch `main`.
- Base work on `develop`; merge only through a feature branch PR targeting `develop`.
- Python and Web CI gates must both be green before merge.
- Streamlit remains operational and is the product specification.
- TDD RED -> GREEN for new parity behavior.
- No fake/decorative financial values.
- React must not reproduce ATR, volatility, confidence, scenario, or signal calculations.
- Preserve auth recovery, scan recovery, same-origin API proxy, deep links, and latest-completed-scan context behavior.
- The previously noted scan decision-card return-to-first-row behavior is intentionally out of scope for this checkpoint.

---

### Task 1: Lock the Projection parity surface with failing contracts

**Files:**
- Create: `tests/test_web_projection_full_parity.py`
- Read only: `izfin_ui/projection_view.py`
- Read only: `web/components/projection-page.tsx`

**Interfaces:**
- Consumes: the approved Streamlit content model in `projection_view.py`.
- Produces: executable source contracts for the required Next.js projection surface.

- [ ] **Step 1: Write the failing tests**

Add tests that require the web Projection implementation to expose the Streamlit product hierarchy, including the exact concepts below:

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_projection_web_preserves_streamlit_lab_chrome_and_model_note():
    page = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    renderer_path = ROOT / "web" / "components" / "projection-model-view.tsx"
    assert renderer_path.exists(), "Projection presentation is still mixed into the context resolver"
    renderer = renderer_path.read_text(encoding="utf-8")
    assert "IZFIN PROJECTION LAB" in renderer
    assert "Projeksiyon & Senaryo Analizi" in renderer
    assert "45G MODEL" in renderer
    assert "ATR + Tarihsel Volatilite" in renderer
    assert "45 günlük karma fiyat hareket bandı" in renderer
    assert "ProjectionModelView" in page


def test_projection_web_renders_every_streamlit_model_dimension_from_api_data():
    renderer = (ROOT / "web" / "components" / "projection-model-view.tsx").read_text(encoding="utf-8")
    for label in (
        "Güncel Fiyat",
        "ATR Modeli",
        "Volatilite Modeli",
        "Karma Model",
        "45G Karma Bant",
        "Geniş Risk Bandı",
        "Model Güven Skoru",
        "Model Karşılaştırması",
        "Teknik Senaryolar",
        "Algoritmik Yön Özeti",
    ):
        assert label in renderer
    assert "projection.metrics.birincil" in renderer
    assert "projection.metrics.ikincil" in renderer
    assert "projection.technical_scenarios.up" in renderer
    assert "projection.technical_scenarios.down" in renderer
    assert "projection.scenario.model_yorumu" in renderer
    assert "dangerouslySetInnerHTML" not in renderer


def test_projection_web_keeps_context_resolution_outside_the_renderer():
    page = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    renderer = (ROOT / "web" / "components" / "projection-model-view.tsx").read_text(encoding="utf-8")
    assert "fetchScanJobContext" in page
    assert "refreshLatestCompletedScan" in page
    assert "fetchProjection" in page
    assert "fetchScanJobContext" not in renderer
    assert "fetchProjection" not in renderer
    assert "getIdToken" not in renderer
```

- [ ] **Step 2: Run the focused test and verify RED**

Run through CI or locally:

```bash
python -m pytest -q tests/test_web_projection_full_parity.py
```

Expected: FAIL because `projection-model-view.tsx` does not yet exist and the complete Streamlit lab chrome is not represented in a focused renderer.

- [ ] **Step 3: Commit the RED contract**

```bash
git add tests/test_web_projection_full_parity.py
git commit -m "test(web): require full Streamlit projection parity"
```

---

### Task 2: Separate context resolution from projection presentation

**Files:**
- Create: `web/components/projection-model-view.tsx`
- Modify: `web/components/projection-page.tsx`
- Modify: `web/app/projection.css`
- Test: `tests/test_web_projection_full_parity.py`

**Interfaces:**
- Consumes: `ProjectionResponse` from `web/lib/projection.ts`, resolved ticker and available ticker list from `ProjectionPage`.
- Produces: `ProjectionModelView({ projection, ticker, availableTickers, onTickerChange, backHref })`.

- [ ] **Step 1: Create the renderer component with a typed boundary**

Use this public shape:

```ts
type ProjectionModelViewProps = Readonly<{
  projection: ProjectionResponse;
  ticker: string;
  availableTickers: string[];
  onTickerChange: (ticker: string) => void;
  backHref: string;
}>;

export function ProjectionModelView(props: ProjectionModelViewProps) { /* render only */ }
```

The component must not call auth, scan-history, or API functions.

- [ ] **Step 2: Move the current real-data projection renderer into the component**

Preserve all currently working fields:

- ticker selector
- current price
- combined movement
- confidence
- downside/base/upside bands
- positive scenario
- negative scenario
- 45-day range
- algorithmic direction
- primary/secondary model metrics
- technical levels
- disclaimer

No calculation should be moved from Python into React. Formatting and range-position display math may remain presentation-only.

- [ ] **Step 3: Make `ProjectionPage` render `ProjectionModelView` only after context + API data resolve**

`ProjectionPage` continues to own:

```ts
fetchScanJobContext(...)
refreshLatestCompletedScan(...)
fetchProjection(...)
resolveTicker(...)
```

and passes the resolved data into the renderer.

- [ ] **Step 4: Run the focused parity test**

```bash
python -m pytest -q tests/test_web_projection_full_parity.py
```

Expected: some assertions may still fail until Task 3 adds the final Streamlit hierarchy/copy.

- [ ] **Step 5: Run TypeScript/build validation**

```bash
pnpm --dir web typecheck
pnpm --dir web build
```

Expected: PASS.

---

### Task 3: Restore the Streamlit Projection information hierarchy

**Files:**
- Modify: `web/components/projection-model-view.tsx`
- Modify: `web/app/projection.css`
- Test: `tests/test_web_projection_full_parity.py`

**Interfaces:**
- Consumes: existing `ProjectionResponse` fields only.
- Produces: a projection page whose visible hierarchy matches `izfin_ui/projection_view.py` while using the approved dark web shell.

- [ ] **Step 1: Add the Streamlit-style lab intro and model note**

The page must visibly include:

```text
IZFIN PROJECTION LAB
Projeksiyon & Senaryo Analizi
45G MODEL
ATR + Tarihsel Volatilite
45 günlük karma fiyat hareket bandı
```

The intro explains that the selected ticker is evaluated over an approximately 45-day movement band, model agreement, and positive/negative technical scenarios.

- [ ] **Step 2: Make Model Comparison the primary analytical block**

Render the API-owned primary rows (`projection.metrics.birincil`) and secondary rows (`projection.metrics.ikincil`) with their source labels. Preserve the semantic labels generated by Python:

```text
Güncel Fiyat
ATR Modeli
Volatilite Modeli
Karma Model
45G Karma Bant
Geniş Risk Bandı
Model Güven Skoru
```

- [ ] **Step 3: Preserve the full band and scenario story**

Keep three model bands and two technical scenario cards. Group them under an explicit `Teknik Senaryolar` heading, and retain support/resistance/stop/TP/model-difference context.

- [ ] **Step 4: Promote algorithmic direction to an explicit summary block**

Use `projection.scenario.yon_title`, `projection.scenario.yon`, `projection.scenario.sinyal`, `projection.scenario.model_yorumu`, `projection.model.guven_skoru`, and `projection.model.model_uyumu`. Label the block `Algoritmik Yön Özeti`.

- [ ] **Step 5: Keep the disclaimer and uncertainty framing**

State that the output is a model band / scenario analysis rather than a target-price promise or investment advice. Do not add probability claims not present in the Python model.

- [ ] **Step 6: Run focused tests and web build**

```bash
python -m pytest -q tests/test_web_projection_full_parity.py tests/test_web_projection_context_recovery.py tests/test_api_projection.py tests/test_projection_service.py tests/test_projection_view.py
pnpm --dir web typecheck
pnpm --dir web build
```

Expected: PASS.

---

### Task 4: Checkpoint documentation and merge gate

**Files:**
- Modify: `IZFIN_MASTER_STATUS.md`
- Test: full CI

**Interfaces:**
- Consumes: merged implementation evidence and live deploy status.
- Produces: canonical cross-device state for the next checkpoint.

- [ ] **Step 1: Update the master status**

Record:

- SMART SCAN + DETAILED ANALYSIS live acceptance passed on 2026-08-28.
- The scan decision-card first-row reset on page revisit is intentionally deferred because the selector keeps the flow usable.
- Current checkpoint becomes `PROJECTION FULL STREAMLIT PARITY — IMPLEMENTED, LIVE ACCEPTANCE PENDING` only after implementation/CI succeeds.
- Next checkpoint after user live acceptance: Performans parity.

- [ ] **Step 2: Open a PR to `develop`**

Use one checkpoint PR; do not touch `main`.

- [ ] **Step 3: Require both CI gates**

Fresh evidence required:

- `IZFIN Quality Gate` = success
- `IZFIN Web Quality Gate` = success

Do not merge on partial/old evidence.

- [ ] **Step 4: Merge and verify Vercel `develop` deployment**

Verify the deployment commit matches the merge commit and reaches `READY`.

- [ ] **Step 5: User live acceptance checklist**

On the canonical develop URL:

1. Open Projection from the sidebar after a completed scan.
2. Confirm real ticker resolution/selection.
3. Confirm `Projeksiyon & Senaryo Analizi`, `45G MODEL`, and `ATR + Tarihsel Volatilite` are visible.
4. Confirm current price, ATR, volatility, combined movement, 45G band, wider risk band, confidence, agreement, positive/negative scenario, and algorithmic direction are populated with real data.
5. Switch ticker and confirm the model updates without leaving Projection.
6. Refresh and confirm context recovers.

Only after live acceptance advance the canonical checkpoint to **Performans parity**.
