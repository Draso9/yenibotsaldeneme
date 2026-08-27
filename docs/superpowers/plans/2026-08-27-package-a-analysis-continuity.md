# Package A — Analysis Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make completed scans reusable across IZFIN web pages so Projection and other analysis screens automatically recover the latest valid scan/ticker context instead of opening as empty technical dead ends.

**Architecture:** Add a small typed scan-context client layer that treats authenticated scan history as server truth and browser storage only as a convenience cache. A React `AnalysisContextProvider` resolves the newest completed scan, tracks the selected ticker/profile, and is updated by Akıllı Tarama when scans complete or historical jobs are opened. Projection consumes explicit route context first, then provider context, then newest completed scan; when multiple tickers exist and no valid selection exists it shows a selector rather than a contract error.

**Tech Stack:** Next.js App Router, React/TypeScript, existing Firebase auth provider, existing FastAPI `/api/v1/scan/jobs` and `/api/v1/scan/jobs/{job_id}` contracts, existing `izfinApiFetch`, pytest source/contract tests, pnpm typecheck/build.

**Spec:** `docs/superpowers/specs/2026-08-27-streamlit-full-parity-migration-design.md`

## Global Constraints

- Do not touch `main`.
- Work from `develop` through feature branches and PRs.
- Do not merge unless relevant Python and web CI gates are green.
- Do not break the existing Streamlit app.
- Do not replace real data with mock or decorative financial data.
- Do not remove currently working auth recovery, retry, scan recovery, durable readiness, or same-origin API proxy behavior.
- React must not reimplement Streamlit business calculations.
- Explicit deep links with `job_id` and `ticker` remain valid and take precedence over recovered context.
- Browser storage is never the authoritative source when authenticated server history is available.
- Package A is functional continuity work; do not start Package C visual polish here.

---

## File Structure

- `web/lib/scan-context.ts` — typed scan-history/job contracts and pure context-resolution helpers.
- `web/components/analysis-context-provider.tsx` — authenticated React provider that loads latest completed scan, persists lightweight user-scoped convenience state, and exposes update methods.
- `web/app/layout.tsx` — mounts `AnalysisContextProvider` inside the existing auth boundary.
- `web/components/scan-workspace.tsx` — publishes scan completion/history selection/profile selection into shared analysis context without changing the scan engine.
- `web/components/projection-page.tsx` — resolves explicit/recovered context, offers a ticker selector when required, and preserves existing projection rendering.
- `web/app/projection/page.tsx` — continues parsing optional route params; no hard requirement that they exist.
- `tests/test_web_analysis_context_contract.py` — RED/GREEN source-contract checks for provider wiring and context precedence.
- `tests/test_web_projection_context_recovery.py` — RED/GREEN checks for Projection recovery and guided empty state.

---

### Task 1: Typed Scan Context Resolver

**Files:**
- Create: `web/lib/scan-context.ts`
- Test: `tests/test_web_analysis_context_contract.py`

**Interfaces:**
- Consumes: `izfinApiFetch` from `web/lib/api.ts` and authenticated ID token.
- Produces:
  - `type ScanHistoryItem = { job_id: string; status: "queued" | "running" | "completed" | "failed"; stage: string; completed: number; total: number; tickers: string[]; created_at?: string | null }`
  - `type ScanJobContext = { job_id: string; status: string; tickers: string[]; result?: { sonuclar?: Array<Record<string, unknown>> } }`
  - `fetchScanHistory(idToken: string): Promise<ScanHistoryItem[]>`
  - `fetchScanJobContext(jobId: string, idToken: string): Promise<ScanJobContext>`
  - `latestCompletedScan(items: ScanHistoryItem[]): ScanHistoryItem | null`
  - `resultTickers(job: ScanJobContext): string[]`
  - `resolveTicker(explicitTicker: string, rememberedTicker: string, availableTickers: string[]): string`

- [ ] **Step 1: Write the failing contract test**

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_analysis_context_helpers_are_defined():
    source = (ROOT / "web" / "lib" / "scan-context.ts").read_text(encoding="utf-8")
    assert "export type ScanHistoryItem" in source
    assert "export function latestCompletedScan" in source
    assert "export function resultTickers" in source
    assert "export function resolveTicker" in source
    assert '"/api/v1/scan/jobs"' in source
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_web_analysis_context_contract.py -q`

Expected: FAIL because `web/lib/scan-context.ts` does not exist.

- [ ] **Step 3: Implement the minimal typed resolver**

```ts
import { izfinApiFetch } from "./api";

export type ScanHistoryItem = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  completed: number;
  total: number;
  tickers: string[];
  created_at?: string | null;
};

export type ScanJobContext = {
  job_id: string;
  status: string;
  tickers: string[];
  result?: { sonuclar?: Array<Record<string, unknown>> };
};

export async function fetchScanHistory(idToken: string): Promise<ScanHistoryItem[]> {
  const response = await izfinApiFetch<{ jobs: ScanHistoryItem[] }>("/api/v1/scan/jobs", idToken);
  return response.jobs;
}

export function latestCompletedScan(items: ScanHistoryItem[]): ScanHistoryItem | null {
  return items.find((item) => item.status === "completed") ?? null;
}

export async function fetchScanJobContext(jobId: string, idToken: string): Promise<ScanJobContext> {
  return izfinApiFetch<ScanJobContext>(`/api/v1/scan/jobs/${encodeURIComponent(jobId)}`, idToken);
}

export function resultTickers(job: ScanJobContext): string[] {
  const rows = job.result?.sonuclar ?? [];
  const fromResults = rows.map((row) => String(row.Varlık ?? row.ticker ?? "").trim().toUpperCase()).filter(Boolean);
  return [...new Set(fromResults.length ? fromResults : job.tickers.map((ticker) => ticker.trim().toUpperCase()).filter(Boolean))];
}

export function resolveTicker(explicitTicker: string, rememberedTicker: string, availableTickers: string[]): string {
  const available = new Set(availableTickers.map((ticker) => ticker.toUpperCase()));
  const explicit = explicitTicker.trim().toUpperCase();
  if (explicit && available.has(explicit)) return explicit;
  const remembered = rememberedTicker.trim().toUpperCase();
  if (remembered && available.has(remembered)) return remembered;
  return availableTickers.length === 1 ? availableTickers[0] : "";
}
```

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_web_analysis_context_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Run web typecheck**

Run: `cd web && pnpm typecheck`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/lib/scan-context.ts tests/test_web_analysis_context_contract.py
git commit -m "feat(web): add typed scan context resolver"
```

---

### Task 2: Authenticated Analysis Context Provider

**Files:**
- Create: `web/components/analysis-context-provider.tsx`
- Modify: `web/app/layout.tsx`
- Modify: `tests/test_web_analysis_context_contract.py`

**Interfaces:**
- Consumes: `useIzfinAuth`, `fetchScanHistory`, `latestCompletedScan`.
- Produces:
  - `type AnalysisContextValue = { latestCompletedScanJobId: string; activeScanJobId: string; selectedTicker: string; activeUniverseProfile: string; lastVisitedAnalysisRoute: string; setActiveScan(jobId: string): void; setSelectedTicker(ticker: string): void; setActiveUniverseProfile(profile: string): void; setLastVisitedAnalysisRoute(route: string): void; refreshLatestCompletedScan(): Promise<void> }`
  - `AnalysisContextProvider`
  - `useAnalysisContext()`

- [ ] **Step 1: Extend the RED test**

```python
def test_analysis_context_provider_is_mounted_inside_auth():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    provider = (ROOT / "web" / "components" / "analysis-context-provider.tsx").read_text(encoding="utf-8")
    assert "AnalysisContextProvider" in layout
    assert "latestCompletedScanJobId" in provider
    assert "refreshLatestCompletedScan" in provider
    assert "useIzfinAuth" in provider
    assert "localStorage" in provider
```

- [ ] **Step 2: Run focused test and verify RED**

Run: `python -m pytest tests/test_web_analysis_context_contract.py -q`

Expected: FAIL because the provider is not present or mounted.

- [ ] **Step 3: Implement provider state and server-truth refresh**

Provider behavior:

```ts
const storageKey = user ? `izfin:analysis-context:${user.uid}` : "";
```

On authenticated user change:

1. Read cached `selectedTicker`, `activeUniverseProfile`, and `lastVisitedAnalysisRoute` from the user-scoped key.
2. Call `fetchScanHistory(token)`.
3. Set `latestCompletedScanJobId` from `latestCompletedScan(history)`.
4. If `activeScanJobId` is empty, initialize it to the latest completed job.
5. Never replace an explicit active job merely because history refreshes.
6. On logout, clear in-memory context. Do not read another user's cached state.

Persist only:

```ts
{
  activeScanJobId,
  selectedTicker,
  activeUniverseProfile,
  lastVisitedAnalysisRoute,
}
```

Do not persist tokens, job result payloads, or financial result data.

- [ ] **Step 4: Mount provider in layout**

Change the body composition from:

```tsx
<AuthProvider><AppShell>{children}</AppShell></AuthProvider>
```

to:

```tsx
<AuthProvider>
  <AnalysisContextProvider>
    <AppShell>{children}</AppShell>
  </AnalysisContextProvider>
</AuthProvider>
```

- [ ] **Step 5: Run focused test**

Run: `python -m pytest tests/test_web_analysis_context_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Run typecheck/build**

Run: `cd web && pnpm typecheck && pnpm build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/components/analysis-context-provider.tsx web/app/layout.tsx tests/test_web_analysis_context_contract.py
git commit -m "feat(web): add authenticated analysis context"
```

---

### Task 3: Publish Akıllı Tarama Context

**Files:**
- Modify: `web/components/scan-workspace.tsx`
- Modify: `tests/test_web_analysis_context_contract.py`

**Interfaces:**
- Consumes: `useAnalysisContext()`.
- Produces: updates shared `activeScanJobId`, `selectedTicker`, `activeUniverseProfile`, and latest-completed state when scan behavior changes.

- [ ] **Step 1: Add failing scan-publication assertions**

```python
def test_scan_workspace_publishes_completed_scan_context():
    source = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    assert "useAnalysisContext" in source
    assert "setActiveUniverseProfile(profile)" in source
    assert "setActiveScan(completed.job_id)" in source
    assert "refreshLatestCompletedScan" in source
```

- [ ] **Step 2: Run focused test and verify RED**

Run: `python -m pytest tests/test_web_analysis_context_contract.py -q`

Expected: FAIL because ScanWorkspace does not publish shared context.

- [ ] **Step 3: Wire profile updates**

After a valid profile changes, call:

```ts
setActiveUniverseProfile(profile);
```

Keep the existing `profile` local state because it directly controls scan UI; shared context mirrors it for cross-page continuity.

- [ ] **Step 4: Wire completed scan updates**

After `izfinApiStream` resolves a completed job:

```ts
setJob(completed);
if (completed.status === "completed") {
  setActiveScan(completed.job_id);
  await refreshLatestCompletedScan();
}
```

Do not publish failed jobs as the active analysis context.

- [ ] **Step 5: Wire history selection**

After `openHistoryJob(jobId)` fetches the job successfully:

```ts
setJob(opened);
if (opened.status === "completed") {
  setActiveScan(opened.job_id);
  const tickers = resultTickers(opened);
  if (tickers.length === 1) setSelectedTicker(tickers[0]);
}
```

- [ ] **Step 6: Run focused test and web checks**

Run:

```bash
python -m pytest tests/test_web_analysis_context_contract.py -q
cd web && pnpm typecheck && pnpm build
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add web/components/scan-workspace.tsx tests/test_web_analysis_context_contract.py
git commit -m "feat(web): publish scan analysis context"
```

---

### Task 4: Projection Context Recovery

**Files:**
- Modify: `web/components/projection-page.tsx`
- Modify: `web/app/projection/page.tsx`
- Create: `tests/test_web_projection_context_recovery.py`

**Interfaces:**
- Consumes: explicit `jobId`/`ticker` props, `useAnalysisContext`, `fetchScanJobContext`, `resultTickers`, `resolveTicker`, existing `fetchProjection`.
- Produces: Projection page that resolves context in priority order: explicit route → shared context → latest completed scan → ticker selector → guided no-scan state.

- [ ] **Step 1: Write failing Projection recovery contract**

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_projection_recovers_latest_completed_scan_context():
    source = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    assert "useAnalysisContext" in source
    assert "fetchScanJobContext" in source
    assert "resultTickers" in source
    assert "projection-ticker-selector" in source
    assert "Henüz tamamlanmış bir taraman yok" in source
    assert "Bu ekran bir tamamlanmış tarama" not in source
```

- [ ] **Step 2: Run focused test and verify RED**

Run: `python -m pytest tests/test_web_projection_context_recovery.py -q`

Expected: FAIL because Projection still requires route parameters.

- [ ] **Step 3: Replace the early route-parameter dead end with resolved state**

Add component state:

```ts
const [resolvedJobId, setResolvedJobId] = useState(jobId);
const [resolvedTicker, setResolvedTicker] = useState(ticker.trim().toUpperCase());
const [availableTickers, setAvailableTickers] = useState<string[]>([]);
const [contextLoading, setContextLoading] = useState(true);
```

Resolution order after auth is ready:

```ts
const candidateJobId = jobId || activeScanJobId || latestCompletedScanJobId;
```

If no candidate exists, set `contextLoading=false` and render the guided no-scan state.

If a candidate exists:

1. Fetch `/api/v1/scan/jobs/{candidateJobId}`.
2. Require `status === "completed"`; if not completed and it came from recovered context, fall back to `latestCompletedScanJobId` when different.
3. Build `tickers = resultTickers(job)`.
4. Resolve ticker with `resolveTicker(ticker, selectedTicker, tickers)`.
5. If resolved ticker exists, update provider `setActiveScan` + `setSelectedTicker` and call existing `fetchProjection`.
6. If multiple tickers exist and none resolves, render the selector before fetching a projection.

- [ ] **Step 4: Add selector behavior**

Render only when `availableTickers.length > 1 && !resolvedTicker`:

```tsx
<section className="projection-panel projection-ticker-selector">
  <p className="eyebrow">SON TAMAMLANAN TARAMA</p>
  <h1>Projeksiyon için hisse seç</h1>
  <p>Son tamamlanan taramandaki varlıklardan birini seç.</p>
  <select value={resolvedTicker} onChange={(event) => {
    const next = event.target.value;
    setResolvedTicker(next);
    setSelectedTicker(next);
  }}>
    <option value="">Hisse seç…</option>
    {availableTickers.map((value) => <option key={value}>{value}</option>)}
  </select>
</section>
```

- [ ] **Step 5: Add product-oriented no-scan state**

When no completed scan exists:

```tsx
<section className="projection-panel projection-empty">
  <p className="eyebrow">PROJEKSİYON</p>
  <h1>Henüz tamamlanmış bir taraman yok</h1>
  <p>45 günlük senaryo analizi, Akıllı Tarama sonucundaki gerçek teknik panel verisini kullanır.</p>
  <a href="/scan">Akıllı Tarama'yı aç →</a>
</section>
```

- [ ] **Step 6: Preserve explicit deep-link precedence**

Keep `web/app/projection/page.tsx` parsing `job_id` and `ticker`. Do not redirect server-side. Explicit props must win inside the client resolver whenever valid.

- [ ] **Step 7: Run focused tests and web checks**

Run:

```bash
python -m pytest tests/test_web_projection_context_recovery.py tests/test_web_analysis_context_contract.py -q
cd web && pnpm typecheck && pnpm build
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add web/components/projection-page.tsx web/app/projection/page.tsx tests/test_web_projection_context_recovery.py
git commit -m "feat(web): recover projection from latest scan context"
```

---

### Task 5: Package A Regression and PR Gate

**Files:**
- Modify only if failures expose a Package A regression.

**Interfaces:**
- Consumes all outputs from Tasks 1–4.
- Produces one reviewable Package A PR targeting `develop`.

- [ ] **Step 1: Run Package A focused tests**

```bash
python -m pytest \
  tests/test_web_analysis_context_contract.py \
  tests/test_web_projection_context_recovery.py -q
```

Expected: PASS.

- [ ] **Step 2: Run complete Python suite**

Run: `python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Run complete web gate locally**

Run: `cd web && pnpm typecheck && pnpm build`

Expected: PASS.

- [ ] **Step 4: Review the diff against Package A acceptance criteria**

Verify all four cases explicitly in code/tests:

```text
1. explicit job_id+ticker deep link wins
2. sidebar Projection uses shared/latest completed scan
3. multiple tickers without selection show a real selector
4. account with no completed scan gets guided /scan empty state
```

- [ ] **Step 5: Open PR against develop only**

PR title:

```text
feat(web): restore analysis context continuity
```

PR body must state:

```text
- Package A of Streamlit Full Parity Migration
- server scan history is authoritative
- explicit deep links keep priority
- Projection recovers latest completed scan/ticker context
- no Streamlit/main changes
- RED→GREEN contract tests included
```

- [ ] **Step 6: Wait for GitHub CI and merge only when both gates are green**

Required successful jobs:

```text
IZFIN Quality Gate
IZFIN Web Quality Gate
```

- [ ] **Step 7: Verify Vercel develop deployment**

After merge, verify the deployment commit equals the merge commit and is `READY`. Smoke check `/scan` and `/projection` return HTTP 200.

- [ ] **Step 8: Manual Vercel acceptance journey**

Using the authenticated `develop` preview:

```text
1. run or open a completed scan
2. choose/open a ticker where available
3. click Projection in sidebar
4. confirm latest valid scan is recovered
5. if multiple tickers and no remembered choice, select one
6. refresh Projection and confirm context is recovered
7. open a valid explicit projection deep link and confirm it overrides remembered context
```

Do not begin Package B until this journey is accepted or any discovered Package A defects are fixed.

---

## Self-Review

**Spec coverage:** This plan implements Package A's shared analysis context, newest completed scan recovery, selected ticker continuity, Projection sidebar recovery, explicit deep-link priority, guided no-scan state, refresh persistence, and Vercel journey verification. Piyasa Merkezi cleanup and screen-level parity intentionally remain Package B.

**Placeholder scan:** No TBD/TODO/"implement later" instructions are present. Each implementation task defines concrete files, interfaces, behavior, tests, commands, and commit boundaries.

**Type consistency:** `ScanHistoryItem`, `ScanJobContext`, `latestCompletedScan`, `resultTickers`, `resolveTicker`, `AnalysisContextValue`, and provider method names are used consistently across Tasks 1–5.
