# Scan worker ownership — 2026-09-08

Base develop: `05f940d40d6ac567c0b74bd8849caf9c50b750d8`.
Branch: `fix/scan-worker-ownership`. Main untouched. Not merged/deployed.

## Problem and fix

A second process reading a live scan previously declared it interrupted and wrote
failed to the shared repository. Remote snapshots were also cached indefinitely.
The first two regression tests failed on baseline (live job falsely failed;
foreign read mutated a running record).

- `izfin_api/scan_jobs.py`: per-store worker UUID, 90-second lease renewed every
  15 seconds during execution including silent runners; remote records reread on
  every request; owner checked before recovery; executing runners continue to
  occupy capacity even after a persisted failure fences their writes.
- `izfin_repositories/signal_repository.py`: Firestore document-version
  preconditions guard owner writes and expired-lease interruption. A concurrent
  heartbeat/completion invalidates the read version; the loser reads current state.
  A failed/completed record cannot be overwritten by the old worker.
- No ownership takeover or automatic rerun is introduced. Lease expiry is detected
  by status/history reads. It is a failure detector, not proof the CPU stopped;
  physical runner cancellation is outside this package.
- Public response schemas do not expose worker/lease fields. Financial calculations,
  UI, provider settings, auth and Streamlit presentation remain unchanged.

## Evidence

- Full local Python suite: **650 passed**.
- Full web behavior suite: **34 passed**.
- New tests: 7 worker/endpoint cases + 4 real-repository/version-boundary cases.
- Covers remote poll/history through completion, owner isolation, silent heartbeat,
  expired worker and late completion, fenced runner capacity, legacy records,
  heartbeat-versus-expiry and late-write-versus-expiry conflicts.
- Existing restart test now supplies an explicitly expired owned lease. Missing
  ownership metadata alone is not evidence of restart.
- Tests use real store/repository code with fake provider/storage boundaries;
  repository tests use the installed Firestore LastUpdateOption type.
- `git diff --check` passed. CI for the published head must be checked separately.
- No live multi-instance Firestore or authenticated browser QA claimed here.
  Existing 34 web tests protect presentation/context behavior; this is backend work.

## Deployment gates and operational limits

Do not merge/deploy blindly: develop has automatic production deployment.

1. Validate version-precondition behavior against an isolated Firestore emulator or
   staging database and a two-worker status/history flow before production rollout.
2. Drain old worker revisions and their active scans before allowing new scans on
   the new revision. Old code still has destructive recovery; mixed old/new reads
   are unsafe. No live traffic or infrastructure changes were made in this package.
3. Review queued/running legacy records without worker_id after old workers are
   confirmed stopped. Reconcile those records explicitly with an auditable operation.
   This fix deliberately does not guess they are dead; otherwise they can remain
   running in history. Completed legacy results remain readable.
4. Monitor heartbeat writes/read cost, clock synchronization and lease expiry.
   90/15 seconds are constructor defaults, not a measured capacity/SLA. A long
   scheduling pause or persistence outage can expire a live computation; fencing
   prevents its late result from reviving a terminal job.
5. Firestore calls still use existing SDK request/retry behavior under the store
   lock; provider/job time budgets, IO deadline tuning, global quota and the legacy
   /scan/run capacity gap remain separate bounded packages.

Next package after safe acceptance: shared admission policy for run/jobs/stream.
Keep #149 documentation reconciliation separate; do not reopen #145–#148.
