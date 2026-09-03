# IZFIN — Master Project Status

> Canonical project handoff/status file for ChatGPT, Codex, and cross-device continuation.
> Read this file before making new changes.

## 1. Product Goal

IZFIN is the Next.js + FastAPI web evolution of the mature Streamlit product.

**Approved direction: Streamlit Full Parity Migration, followed by controlled release polish.**

The existing Streamlit implementation remains the product reference for behavior and meaning. Do **not** redesign the product from scratch. The web application should preserve useful Streamlit behavior while using the newer architecture and the decision-first hierarchy accepted during the web migration.

Primary product references:

- `app2.py`
- `izfin_ui/`
- framework-neutral/domain logic in `izfin_services/`, `izfin_core/`, repositories

Approved product title/tagline:

**IZFIN | Akıllı Piyasa Kararları**

Do not reintroduce `Akıllı BIST Analizi`.

## 2. Non-Negotiable Rules

- Never touch `main`.
- Base feature/fix work on the latest accepted `develop`.
- Use feature branch -> PR -> `develop`.
- Do not merge unless relevant Python and Web CI gates are green.
- Verify post-merge `develop` CI and the production deployment identity for code checkpoints.
- Keep Streamlit working in parallel until the web release is formally closed.
- Use TDD RED -> GREEN for behavior/copy contracts where code changes are involved.
- Do not replace real financial data with mock/decorative financial data.
- Do not reimplement Python business/financial calculations in React.
- Preserve auth recovery, retry boundaries, scan recovery, durable readiness, same-origin API proxy, and shared analysis/ticker continuity unless a real defect specifically requires a bounded fix.
- Avoid repo-wide rescans unless genuinely necessary.
- Group related work into checkpoint-sized packages.
- User-facing progress is checkpoint-based, not PR-by-PR narration.
- Do not perform broad CSS architecture refactors during the final release-polish program.

## 3. Current Architecture

### Frontend

- `web/` — Next.js App Router web client
- Vercel hosts the web frontend
- React is presentation/orchestration; financial calculations remain Python-owned

### API / Services

- `izfin_api/` — FastAPI boundary
- `izfin_services/` — service layer
- `izfin_core/` — shared domain/core logic
- repositories / Firebase / Firestore where already established
- Cloud Run hosts the FastAPI backend

### Product Reference

- `app2.py` — Streamlit application remains operational
- `izfin_ui/` — Streamlit/product presentation modules and parity reference

## 4. Current Program

# FINAL PRODUCT POLISH / RELEASE CLOSURE — CP0 CANONICAL STATUS RESET

The major web product surfaces are implemented and the latest decision-first simplification is live on `develop`.

Current release-polish baseline:

- Latest product merge: **PR #135**
- `develop` baseline before CP0: `d04705ca6b9d9632d311409f6fa4f1091a1b63aa`
- Latest verified production deployment for that baseline: `dpl_3h6NV2Z4vMVk7Rvm3E7hhLNxVi8T`
- PR #135 and post-merge `develop` CI both passed Python and Web quality gates
- Production durable readiness has been verified healthy after the latest release work

The approved release-polish design is:

`docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md`

Do not return to the stale parity-stage order that previously treated Account/Admin or mobile work as the next implementation milestone.

## 5. Current User-Facing Product State

### A. Piyasa Merkezi

Purpose: last completed scan decision summary, not watchlist editing or scan configuration.

Current behavior:

- scan-derived market/pulse summary
- trend, momentum, money-flow, and risk factors
- decision-distribution KPIs
- system comment
- top/featured scan result
- movers where available
- links into stock analysis
- authoritative readiness messaging in the global shell

Known release-polish issue:

- some copy still overstates freshness (`BUGÜNÜN ÖNE ÇIKAN HİSSESİ`, `LIVE`, `Listende dikkat çekenler`) even though the source is the latest completed scan. This is CP1 copy/semantic scope only.

### B. Akıllı Tarama

Current state: functionally mature and decision-first.

Quick universes:

- Kendi Listem
- BIST 30
- BIST 100
- ABD Büyük Teknoloji

Core flow:

- symbol/company search and personal-list editing
- scan launch
- progress/recovery
- internal durable recovery; no separate visible scan-history module
- result summary metrics
- **Hisseye Özel Karar Motoru**
- result filters: `Tümü / AL Sinyalleri / Trend Adayları / İzle-Bekle`
- mobile/desktop result tables
- continuity into Detailed Analysis and Projection

Canonical result hierarchy after PR #135:

**summary metrics -> Decision Motor -> result filters -> result table**

Decision Motor default-visible hierarchy:

- Merkezi Karar
- Neden alınabilir?
- Neden beklenmeli / alınmamalı?
- STOP / ZARAR KES

Secondary/collapsed decision details retain:

- algorithm confidence score `/100`
- entry quality
- MTF alignment
- risk
- technical profile
- explanation/confirmation context
- support/resistance
- TP1/TP2/TP3

Known release-polish issue:

- four quick universe cards currently sit in a desktop grid originally designed for three columns, creating a visually unbalanced 3+1 layout. CP2 fixes layout only; scan behavior/hierarchy must remain unchanged.

Deferred low-priority behavior remains non-blocking:

- revisiting Akıllı Tarama can sometimes fall back to the first ticker instead of the previously selected ticker. The user explicitly decided not to spend time on this while the real selector keeps the flow usable.

### C. Detaylı Analiz

Current state: simplified technical-depth companion to the Decision Motor.

The page intentionally does **not** duplicate the full Decision Motor.

Current hierarchy:

- selected ticker + current price
- Gelişmiş Skor summary
- compact technical summary
- score explanation in collapsed `Bu skor neden?` / Gelişmiş Skor detail
- collapsed `Göstergeler`
- collapsed `Trend ve momentum özeti`
- collapsed `Destek, direnç ve giriş planı`
- collapsed `Teknik hedefler ve algoritmik yorum`
- Projection navigation
- return/context path to Smart Scan

Canonical Gelişmiş Skor bands:

- `<50` — Cezalı
- `50–69` — Nötr
- `>=70` — Güçlü

A high score is not an automatic AL decision and is not a success probability.

### D. Projeksiyon

Current model is Python-owned and approximately 45 days.

Current capabilities:

- current price
- ATR movement
- historical-volatility movement
- combined movement
- base/upside/downside bands
- wider risk band
- model confidence score
- model agreement
- volatility explanation
- positive technical scenario
- negative technical scenario
- algorithmic direction summary
- explicit model-scope / no-guarantee disclosure

Known release-polish issues:

1. The backend produces a heuristic `guven_skoru` on a `/100` scale, but parts of the UI still render it as `Güven %...` / `Model güveni %...`. CP1 standardizes this as **Model güven skoru X/100** and removes probability-like wording.
2. The page remains the most information-dense user surface. CP3 applies decision-first presentation simplification without changing `izfin_core/projection_engine.py` calculations or removing model outputs.

### E. Performans

Current capabilities:

- active signal/position periods
- closed-position history
- summary KPIs
- win rate / average / median where supported
- median duration
- best/worst interpretation
- common close reasons
- closed-position risk/target history
- asset-level scorecard
- signal-level measurement history
- small-sample warnings
- manual refresh boundary

Current web scorecard horizon selector:

**1 / 5 / 10 / 20 / 45G**

Known release-polish issue:

- an old explanatory card still says `20G / 60G / 120G`, which no longer matches the actual web selector. CP1 fixes the text only; calculation/API behavior is unchanged.

### F. Strateji Lab

Current state: implemented and retained as an advanced historical-analysis surface.

Current capabilities:

- symbol/company discovery
- 3Y / 5Y / 10Y test periods
- Daily Core historical replay
- no-future-information discipline
- summary KPIs
- decision-type tables
- historical test-operation detail disclosure
- explanation/reading notes
- owner-scoped last-ticker continuity
- real-data-only rendering

Ordinary user-facing naming should standardize on **Strateji Lab** during CP1 while technical/internal labels may remain explicit where appropriate.

### G. Hesap / Legal / Admin QA

Implementation is complete and remains part of the final authenticated acceptance journey.

Hesap/legal capabilities:

- profile/account summary
- versioned KVKK/privacy and terms documents
- authenticated personal-data export
- irreversible account deletion boundary
- safe post-delete logout/redirect

Admin QA capabilities:

- admin-only navigation/access boundary
- live durable readiness
- static quality metrics
- release/CI context
- GitHub Actions as explicit CI source-of-truth

Known release-polish issue:

- ordinary user-facing copy still exposes some implementation terms such as FastAPI, Next.js, Firebase token/UID language. CP1 removes that product jargon while keeping Admin QA technically explicit.

## 6. Recent Closing Merges

### PR #132 — Mobile usage, data cards, and accessibility

Merge SHA: `dd7b8a9d568639119748929e0c033b828b67143b`

Added the mobile navigation structure, mobile scan/performance cards, modal/focus behavior, form accessibility improvements, responsive foundations, and real component behavior tests. Real viewport/keyboard acceptance was explicitly deferred to the final release stage.

### PR #133 — Trend Adayı and explainable signals

Merge SHA: `6f22c2ed0d81ce65e90d0a2a302bc758f1a3d2ff`

Renamed the technical candidate profile to `Trend Adayı`, clarified profile vs central decision, aligned AL confirmation explanation with Python decision conditions, and standardized algorithm confidence as a score rather than measured success probability.

### PR #134 — Decision-first UI simplification

Merge SHA: `5b1833105b49035c45d820843aef2f9e0557093a`

Collapsed scan configuration after completed results, moved the Decision Motor ahead of result tables, reduced the default-visible Decision Motor to verdict/reasons/stop, and simplified Detailed Analysis into compact summary plus disclosures.

### PR #135 — Scan result flow, US technology profile, and guide polish

Merge SHA: `d04705ca6b9d9632d311409f6fa4f1091a1b63aa`

Finalized Smart Scan order as Decision Motor -> filters -> result table, restored `ABD Büyük Teknoloji` as a clickable quick profile, removed `JOB TABANLI` from Detailed Analysis, and aligned the Smart Scan usage guide with the actual decision-first flow.

## 7. Develop Preview

Canonical develop URL:

`https://izfin-web-git-develop-adopcin-7216.vercel.app`

Canonical production alias currently used for release verification:

`https://izfin-web.vercel.app`

Do not use one-off deployment URLs as the canonical user link unless debugging a specific deployment.

## 8. Final Product Polish Work Order

Do not change this order without an explicit user decision.

### CP0 — Canonical Status Reset

- update this file to post-PR-135 reality
- record the final-polish design and work order
- documentation only

### CP1 — Copy and Semantic Consistency

- Performance `1 / 5 / 10 / 20 / 45G` copy alignment
- Projection confidence `/100` terminology; remove probability-style wording
- Piyasa Merkezi latest-scan wording; remove `LIVE`/today overclaim
- remove ordinary-user FastAPI/Next.js/Firebase-token/UID jargon
- standardize ordinary product naming on `Strateji Lab`

### CP2 — Smart Scan Preset Layout Polish

- four balanced quick universe cards on desktop
- 2 x 2 tablet layout
- safe mobile layout
- no scan behavior, hierarchy, universe, or decision changes

### CP3 — Projection Decision-First Simplification

Default-visible priority:

- ticker/current price
- 45G movement band
- Model güven skoru `/100`
- algorithmic direction summary
- positive scenario trigger/target/risk invalidation
- negative scenario trigger/downside/invalidation

Move secondary/repeated model detail into disclosures. Preserve all Python-owned model outputs/calculations.

### CP4 — ESLint Quality Gate

- make ESLint 9 / Next.js 16 flat configuration operational
- run `pnpm --dir web lint`
- add lint before typecheck/component-tests/build in Web CI
- minimal fixes only; no broad refactor

### CP5 — TestClient Deprecation Cleanup

- investigate Starlette/httpx TestClient deprecation
- migrate only if a supported behavior-preserving path is clear
- otherwise document the debt instead of forcing a risky package change

### CP6 — Real Viewport, Keyboard, and Release Acceptance

Required viewports:

- 390 x 844
- 768 x 1024
- 1440 x 900

Final authenticated journey:

**Giriş -> Piyasa Merkezi -> Akıllı Tarama -> Tarama -> Decision Motor -> filtre -> Detaylı Analiz -> Projeksiyon -> Performans -> Strateji Lab -> Hesap**

Check:

- horizontal overflow / clipping
- mobile navigation and `Diğer`
- disclosure behavior
- modal Escape/focus return
- auth form error focus
- Smart Scan hierarchy
- ticker continuity into Detail/Projection
- Performance mobile cards/period controls
- Account export/delete surfaces without routine destructive deletion
- Piyasa Merkezi latest-scan language

Any real bug found here should be fixed in a narrow `fix/final-acceptance-*` PR.

## 9. Technical Debt Snapshot

### Strong / relatively mature

- FastAPI boundary
- auth recovery
- 401 refresh/retry semantics
- 403 handling
- same-origin API proxy
- scan job recovery
- durable readiness
- Firestore-backed scan persistence boundary
- Python/Web CI gates
- Vercel/Cloud Run split
- decision-first Smart Scan hierarchy
- Detailed Analysis decomposition
- mobile navigation and component behavior coverage

### Open release-polish debt

- CP1 copy/semantic consistency
- CP2 four-card Smart Scan preset layout
- CP3 Projection information-density cleanup
- CP4 ESLint flat configuration and CI lint gate
- CP5 Starlette/httpx TestClient deprecation warning
- CP6 real viewport/keyboard/final authenticated acceptance
- generic/stacked CSS layers remain maintenance debt but are **not** release-polish scope
- deferred Smart Scan revisit ticker-reset behavior remains non-blocking

### Technical debt policy

- no new decorative/product features before CP6 closes
- no broad CSS refactor before release acceptance
- remove duplicate responsibilities instead of layering more UI
- prefer authoritative server state over browser-only state
- keep business calculations in Python
- each checkpoint must reduce or leave flat, never knowingly increase, release debt

## 10. CI / Release Verification Rules

For code checkpoints:

1. TDD RED -> GREEN for the bounded change.
2. Relevant local/source-contract tests.
3. GitHub PR into `develop`.
4. Both IZFIN Python and Web quality gates green where applicable.
5. Merge only after green gates.
6. Verify post-merge `develop` CI.
7. Verify production Vercel deployment exact SHA when the checkpoint affects deployed web code.
8. Verify same-origin health/readiness for final release closure.

Current Web CI before CP4 runs:

- Next.js typecheck
- component behavior tests
- Next.js production build

CP4 will add lint as a first-class Web quality gate.

## 11. Working Style / Communication

At checkpoint end, report:

- **What works** — concrete verified behavior
- **What changed** — only the checkpoint scope
- **What is missing** — remaining checkpoints/debt
- **What the user should test live** — only where live acceptance is meaningful
- **Technical debt trend** — increased / decreased / flat and why

Internally, branches/PRs/tests/commits remain required, but user-facing progress stays checkpoint-based.

## 12. Codex Efficiency Rules

- Start from this file plus the current checkpoint spec/plan.
- Do not repeatedly scan the whole repository.
- Keep each Codex task to a narrow 2–4 related changes where practical.
- Target only relevant files/tests.
- Use a new Codex session after a major checkpoint when that reduces context noise.
- Trace real data flow before applying fixes.
- If a fix fails repeatedly, reassess the boundary instead of stacking workarounds.
- Preserve the explicit user decision not to prioritize the low-value Smart Scan revisit ticker reset.

## 13. Canonical Next Action

After CP0 is reviewed and merged, begin:

# CP1 — Copy and Semantic Consistency

Bounded scope only:

1. Align Performance explanatory copy with the actual `1 / 5 / 10 / 20 / 45G` selector.
2. Present Projection confidence consistently as **Model güven skoru X/100**, not `%` probability-like language.
3. Replace Piyasa Merkezi `BUGÜNÜN ÖNE ÇIKAN HİSSESİ` / `LIVE` / `Listende dikkat çekenler` language with truthful latest-completed-scan wording.
4. Remove FastAPI/Next.js/Firebase token/UID jargon from ordinary user-facing surfaces while retaining technical detail in Admin QA.
5. Standardize ordinary product navigation/copy on `Strateji Lab`.

Do **not** change financial calculations, central decision rules, scan universes, API payloads, auth/recovery, ticker continuity, or Projection mathematics in CP1.
