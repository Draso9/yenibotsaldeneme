const BASE_RECOVERY_DELAY_MS = 1_000;
const MAX_RECOVERY_DELAY_MS = 10_000;
const ACTIVE_SCAN_STATUSES = new Set(["queued", "running"]);

type RecoverableScanJob = { status: string };

export function recoveryRetryDelayMs(failureCount: number): number {
  const normalizedFailures = Math.max(0, Math.floor(Number.isFinite(failureCount) ? failureCount : 0));
  const exponent = Math.min(normalizedFailures, 4);
  return Math.min(BASE_RECOVERY_DELAY_MS * (2 ** exponent), MAX_RECOVERY_DELAY_MS);
}

export function preferActiveRecoveryJob<T extends RecoverableScanJob>(current: T | null, discovered: T): T {
  return current && ACTIVE_SCAN_STATUSES.has(current.status) ? current : discovered;
}
