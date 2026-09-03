# IZFIN — Master Project Status

> Canonical project handoff/status file for ChatGPT, Codex, and cross-device continuation.
> Read this file before making new changes.

## 1. Product Direction

IZFIN is the Next.js + FastAPI web evolution of the mature Streamlit product.

Approved product title:

**IZFIN | Akıllı Piyasa Kararları**

The Streamlit application remains the behavioral/product reference while public-release finalization is still open. Do not redesign the product from scratch and do not reintroduce `Akıllı BIST Analizi`.

Primary references:

- `app2.py`
- `izfin_ui/`
- `izfin_services/`
- `izfin_core/`
- repositories / Firebase / Firestore boundaries

## 2. Non-Negotiable Engineering Rules

- Never touch `main` unless the user explicitly changes the release workflow.
- Base work on the latest accepted `develop`.
- Feature/fix branch → PR → `develop`.
- Relevant Python and Web CI gates must be green before merge.
- Verify post-merge `develop` CI and production deployment identity for code checkpoints.
- Use TDD RED → GREEN for behavioral/copy fixes.
- Financial/business calculations remain Python-owned; React is presentation/orchestration.
- Do not replace real financial data with mock/decorative data.
- Preserve auth refresh/retry, scan recovery, durable readiness, same-origin API proxy and ticker continuity unless a reproduced defect requires a bounded change.
- Avoid repo-wide repeated scans and broad CSS refactors.
- Keep checkpoint-sized changes and user-facing checkpoint summaries.

## 3. Current Architecture

### Frontend

- `web/` — Next.js App Router
- hosted on Vercel
- canonical production alias: `https://izfin-web.vercel.app`
- canonical develop alias: `https://izfin-web-git-develop-adopcin-7216.vercel.app`

### Backend

- `izfin_api/` — FastAPI boundary
- `izfin_services/` — service/orchestration layer
- `izfin_core/` — financial/domain logic
- Firebase/Firestore repositories where established
- backend hosted on Cloud Run behind the same-origin web proxy

## 4. Current Release State — Final Product Polish Complete

The approved CP0 → CP6 final-polish program is **technically complete**.

Current accepted `develop` SHA:

**`265346151af1c64350281c894014b06b462a2995`**

Current production deployment:

**`dpl_E2nFdzXsAkVtHTk7KvKejKq6vnqg`**

Production state:

- target: `production`
- git ref: `develop`
- exact SHA: `265346151af1c64350281c894014b06b462a2995`
- state: `READY`

Post-merge CI:

- run **33787173807**
- IZFIN Quality Gate: SUCCESS
- IZFIN Web Quality Gate: SUCCESS
- Web sequence: ESLint → typecheck → component behavior tests → production build

Live smoke after the merge:

- `/izfin-api/api/v1/health` → HTTP 200, `status=ok`
- `/izfin-api/api/v1/health/ready/durable` → HTTP 200
- `ready=true`
- `authentication=true`
- `user_repository=true`
- `signal_repository=true`
- `scan_runner=true`
- `scan_job_store=true`
- `scan_job_persistence=true`

## 5. Completed Final-Polish Checkpoints

### CP0 — Canonical Status Reset

PR #136

Merge SHA: `92cf5526b475cffd82bddcc5454dea9274a8fac6`

- reset canonical project state to post-PR-135 reality
- established the CP0 → CP6 release-polish work order
- documentation only

### CP1 — Copy and Semantic Consistency

PR #137

Merge SHA: `835b691f027e8a5b0b46c254cb7c659ffbc9058f`

- Performance copy aligned to `1 / 5 / 10 / 20 / 45G`
- Projection confidence standardized as a `/100` model-confidence score, not a probability
- Piyasa Merkezi freshness language changed to latest-completed-scan semantics
- removed ordinary-user FastAPI / Next.js / Firebase token / UID jargon
- standardized ordinary product naming on `Strateji Lab`
- no financial calculations or API behavior changed

### CP2 — Smart Scan Preset Layout Polish

PR #138

Merge SHA: `f1998eca3a48128631266bb88cf0dae621e0327d`

Quick-universe layout:

- desktop: 4 balanced cards
- tablet: 2 × 2
- mobile: 1 column

Scan behavior, Decision Motor, filters, result table and financial logic were unchanged.

### CP3 — Projection Decision-First Simplification

PR #139

Merge SHA: `9a45a02c03ff88358e7a61cd770d7c384438d73d`

Default-visible Projection hierarchy now prioritizes:

- ticker / current price
- Model güven skoru `/100`
- 45G movement band
- algorithmic direction summary
- positive scenario
- negative scenario

Repeated/secondary model comparison and technical-level details moved into disclosures. `izfin_core/projection_engine.py` calculations were unchanged.

### CP4 — ESLint Quality Gate

PR #140

Merge SHA: `ff8ed1d3b1d89c4712c21b6946840261fd4742f2`

- ESLint 9 flat config made operational
- Web CI now runs lint before typecheck/component tests/build
- lint gate currently passes with **0 errors**
- approximately **26 known warnings** remain visible, mainly legacy `set-state-in-effect` patterns and a few scan-progress dependency warnings
- these warnings were deliberately not converted into a risky auth/recovery/scan refactor during release polish

### CP5 — Starlette TestClient Deprecation Cleanup

PR #141

Merge SHA: `909fe1feceecea801b7396b47f3b3b8c0dc1acee`

- existing `httpx==0.28.1` retained where required
- supported Starlette test transport dependencies added (`httpx2`, `httpcore2`, `truststore`)
- import-time TestClient deprecation regression added
- old `StarletteDeprecationWarning` removed without API/runtime behavior change

### CP6 — Real Viewport, Keyboard and Release Acceptance

PR #142

Merge SHA: `265346151af1c64350281c894014b06b462a2995`

Real Chromium acceptance covered canonical viewports:

- 390 × 844
- 768 × 1024
- 1440 × 900

Critical public/authenticated surfaces included:

- Auth
- Terms
- KVKK/privacy
- Piyasa Merkezi
- Akıllı Tarama
- Projeksiyon
- Performans
- Strateji Lab
- Hesap

Verified:

- no release-blocking horizontal overflow / clipped primary controls in the tested matrix
- mobile navigation and `Diğer` behavior
- usage-guide keyboard interaction
- auth invalid-submit focus and ARIA error relationships
- Performance keyboard period interaction
- native scan modal focus ownership

A real browser regression was found during CP6: after a completed scan, focus could fall to `BODY` when the original launch control remained connected but became hidden inside collapsed scan controls.

Permanent fix in `web/components/modal-surface.tsx`:

- reject hidden return-focus targets using `getClientRects().length > 0`
- defer restoration until native dialog close processing completes
- restore to the valid opener or `#main-content` fallback

Permanent regression:

- `tests/test_checkpoint6_modal_focus_return.py`

TDD RED evidence:

- run `33780810313`

Post-merge production browser evidence:

- QA-only run **33787610230** against `https://izfin-web.vercel.app`
- native scan modal: `isModal=true`
- focus entered the modal
- after scan completion: `inMain=true`
- final focused element: `DIV#main-content.app-content`
- temporary QA account cleanup: `deleted`

Therefore the **technical CP6 release acceptance is closed**.

## 6. Current User-Facing Product Shape

### Piyasa Merkezi

Purpose: latest completed scan decision summary, not watchlist editing or scan configuration.

It provides market/pulse summary, decision distribution, featured scan result and navigation into analysis depth. Freshness language must continue to describe latest scan state rather than imply a continuously live feed.

### Akıllı Tarama

Quick universes:

- Kendi Listem
- BIST 30
- BIST 100
- ABD Büyük Teknoloji

Canonical result hierarchy:

**summary metrics → Hisseye Özel Karar Motoru → filters → result table**

Decision Motor default-visible content:

- Merkezi Karar
- Neden alınabilir?
- Neden beklenmeli / alınmamalı?
- STOP / ZARAR KES

Secondary detail remains collapsed and includes confidence, entry quality, MTF, risk, technical profile, signal explanation and levels.

### Detaylı Analiz

Technical-depth companion to the Decision Motor. It should not duplicate the full central decision reasoning.

Canonical Gelişmiş Skor bands:

- `<50` — Cezalı
- `50–69` — Nötr
- `>=70` — Güçlü

A high score is not an automatic AL decision and is not a success probability.

### Projeksiyon

Python-owned approximately 45-day scenario/model surface. Confidence is a `/100` heuristic model-confidence score, never a measured success probability.

### Performans

Current web scorecard horizons:

**1 / 5 / 10 / 20 / 45G**

### Strateji Lab

Advanced historical replay / strategy-analysis surface. Ordinary user-facing name: **Strateji Lab**.

### Hesap / Legal / Admin QA

Account lifecycle, export, deletion and versioned legal documents are implemented. Admin QA remains the correct place for technical infrastructure/release wording.

## 7. Explicitly Deferred Final Public-Release Step — KVKK

Technical release acceptance is complete, but **final public legal publication readiness is intentionally not closed yet**.

Production currently has these deployment values unset:

- `IZFIN_DATA_CONTROLLER_NAME`
- `IZFIN_CONTACT_EMAIL`
- `IZFIN_DATA_CONTROLLER_ADDRESS`

The user explicitly chose to fill them at the final publication step. Do not invent or infer these values.

Before final public launch:

1. obtain the real data-controller name/title,
2. obtain the public contact email,
3. obtain the appropriate public application/service address,
4. set the production runtime values,
5. verify `/api/v1/legal/privacy` no longer displays placeholder/warning text,
6. perform a final legal-content review.

Also review stale infrastructure wording in the privacy text (for example legacy `Streamlit Secrets` / `Streamlit Cloud` references) against the current Vercel + Cloud Run architecture during that legal-finalization step.

Until those steps are done, describe IZFIN as **technically release-ready / technically acceptance-complete, with legal publication finalization pending** — not fully public-release complete.

## 8. Known Non-Blocking Technical Debt

These items are not current release-polish blockers:

- ESLint passes with 0 errors but ~26 known warnings, mainly effect-state/recovery patterns and a few scan-progress dependency warnings.
- CSS remains split across multiple global/layer files. Do not consolidate immediately before launch; make it a separate maintenance project after real-user feedback.
- revisiting Smart Scan can sometimes select the first result rather than the previously selected ticker; the explicit ticker selector keeps the flow usable and the user previously deferred this behavior.
- exact backend release SHA is not exposed in public health output; optional future observability improvement.

## 9. Next Product Phase

Do **not** start adding decorative features just because CP0–CP6 are complete.

Recommended sequence:

1. keep the current technically accepted build stable,
2. complete the deferred KVKK/publication configuration when the user is ready,
3. release to real users,
4. collect real usage/feedback,
5. prioritize the next product work from evidence rather than adding more information density.

Any new functional milestone should begin from current `develop`, define a bounded spec, and preserve the decision-first product hierarchy.

## 10. Communication / Handoff Rule

At the end of future checkpoints report:

- what changed,
- what was verified,
- exact PR / merge SHA where relevant,
- production identity where relevant,
- remaining real blockers/debt.

Do not reopen completed CP0–CP6 work unless a reproduced regression or explicit user request requires it.
