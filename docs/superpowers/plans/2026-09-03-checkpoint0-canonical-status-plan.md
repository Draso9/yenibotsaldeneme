# Checkpoint 0 Canonical Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `IZFIN_MASTER_STATUS.md` accurately describe the post-PR-135 product and establish the approved CP0–CP6 release-polish order as the only canonical next-work sequence.

**Architecture:** Documentation-only checkpoint. No application source, financial calculation, API, auth, CSS, or runtime behavior changes are allowed. The master status will be rewritten around the actual current product hierarchy and the final-polish design spec.

**Tech Stack:** Markdown documentation, GitHub branch/PR workflow.

**Spec:** `docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md`

## Global Constraints

- Never touch `main`.
- Base this checkpoint on `develop` after PR #135 (`d04705ca6b9d9632d311409f6fa4f1091a1b63aa`).
- CP0 is documentation-only.
- Do not alter financial calculations, decision rules, API payload semantics, auth/recovery, scan recovery, durable readiness, ticker continuity, frontend source, backend source, CSS, or tests.
- Preserve the explicit deferred low-priority scan revisit ticker-reset behavior as non-blocking debt.
- The final canonical order is CP0 -> CP1 -> CP2 -> CP3 -> CP4 -> CP5 -> CP6.

---

### Task 1: Replace stale project status with current product truth

**Files:**
- Modify: `IZFIN_MASTER_STATUS.md`

**Interfaces:**
- Consumes: current `develop` product state after PRs #132, #133, #134, #135.
- Produces: canonical handoff document for ChatGPT, Codex, and future development sessions.

- [ ] **Step 1: Identify stale statements that must disappear**

Confirm the current file still contains all of the following stale concepts:

```text
ACCOUNT / ADMIN STREAMLIT PARITY — IMPLEMENTED, LIVE ACCEPTANCE PENDING
selected-ticker decision motor below table
20G / 60G / 120G scorecards
Account/Admin parity audit — current
Stage 6 Mobile only after Stage 5 is accepted
Live-verify Account/Admin parity ... as the canonical next action
```

- [ ] **Step 2: Rewrite the current-state sections**

The replacement must explicitly record:

```text
Current program: FINAL PRODUCT POLISH / RELEASE CLOSURE
Latest baseline: PR #135 / develop d04705ca6b9d9632d311409f6fa4f1091a1b63aa
Smart Scan hierarchy: metrics -> Decision Motor -> result filters -> result table
Quick universes: Kendi Listem / BIST 30 / BIST 100 / ABD Büyük Teknoloji
Detailed Analysis: compact technical summary + collapsed score/technical depth; no full Decision Motor duplication
Performance web selector: 1 / 5 / 10 / 20 / 45G
Open polish: copy semantics, preset grid, Projection simplification, ESLint, TestClient warning, viewport/keyboard acceptance
```

- [ ] **Step 3: Replace the stale work order**

Use exactly this continuation order:

```text
CP0 Canonical Status Reset
CP1 Copy and Semantic Consistency
CP2 Smart Scan Preset Layout Polish
CP3 Projection Decision-First Simplification
CP4 ESLint Quality Gate
CP5 TestClient Deprecation Cleanup
CP6 Real Viewport, Keyboard, and Release Acceptance
```

- [ ] **Step 4: Update latest relevant merges**

Add the post-parity closing PRs:

```text
#132 mobile/responsive/accessibility
#133 Trend Adayı + explainable signals
#134 decision-first UI simplification
#135 scan flow + US technology profile + guide polish
```

Include the known merge SHAs where available in the existing release record.

- [ ] **Step 5: Make the next action CP1, not old Account/Admin work**

The final `Canonical Next Action` must say that after CP0 merge the next branch/checkpoint is:

```text
CP1 — Copy and Semantic Consistency
```

and list its bounded scope without instructing any financial or behavioral change.

### Task 2: Verify CP0 is documentation-only and internally consistent

**Files:**
- Verify: `IZFIN_MASTER_STATUS.md`
- Verify: `docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md`
- Verify: `docs/superpowers/plans/2026-09-03-checkpoint0-canonical-status-plan.md`

**Interfaces:**
- Consumes: Task 1 output.
- Produces: reviewable documentation-only PR.

- [ ] **Step 1: Search for stale blockers**

The updated master status must no longer present these as current next work:

```text
Account/Admin parity audit — current
selected-ticker decision motor below table
Stage 6 Mobile only after Stage 5 is accepted
```

Historical mention of old states is allowed only when clearly labeled historical.

- [ ] **Step 2: Verify required current strings exist**

Confirm the master status contains:

```text
ABD Büyük Teknoloji
Decision Motor
1 / 5 / 10 / 20 / 45G
CP1 — Copy and Semantic Consistency
CP6 — Real Viewport, Keyboard, and Release Acceptance
```

- [ ] **Step 3: Verify changed-file scope**

The CP0 PR may change only:

```text
IZFIN_MASTER_STATUS.md
docs/superpowers/specs/2026-09-03-final-product-polish-checkpoints-design.md
docs/superpowers/plans/2026-09-03-checkpoint0-canonical-status-plan.md
```

- [ ] **Step 4: Open PR to `develop`**

Use title:

```text
chore(status): reset canonical state for final polish
```

PR body must state that CP0 is documentation-only, `main` is untouched, and CP1 is the next checkpoint.

- [ ] **Step 5: Merge after review/CI and verify `develop`**

Because this checkpoint is documentation-only, no application behavior claim should be made. Verify the merge SHA is on `develop` and then begin CP1 from that new baseline.
