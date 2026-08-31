const BASE_RECOVERY_DELAY_MS = 1_000;
const MAX_RECOVERY_DELAY_MS = 10_000;
export const MAX_RECOVERY_RETRIES = 4;
const ACTIVE_SCAN_STATUSES = new Set(["queued", "running"]);

/**
 * @param {number} failureCount
 * @returns {number}
 */
export function recoveryRetryDelayMs(failureCount) {
  const normalizedFailures = Math.max(0, Math.floor(Number.isFinite(failureCount) ? failureCount : 0));
  const exponent = Math.min(normalizedFailures, 4);
  return Math.min(BASE_RECOVERY_DELAY_MS * (2 ** exponent), MAX_RECOVERY_DELAY_MS);
}

/**
 * A recovery sequence may retry after the first four transient failures.
 * Once the count reaches the limit, the UI stops scheduling automatic work
 * until a fresh user action or route mount restarts recovery.
 *
 * @param {number} failureCount
 * @returns {boolean}
 */
export function canRetryRecovery(failureCount) {
  const normalizedFailures = Math.max(0, Math.floor(Number.isFinite(failureCount) ? failureCount : 0));
  return normalizedFailures < MAX_RECOVERY_RETRIES;
}

/**
 * @template {{ status: string }} T
 * @param {T | null} current
 * @param {T} discovered
 * @returns {T}
 */
export function preferActiveRecoveryJob(current, discovered) {
  return current && ACTIVE_SCAN_STATUSES.has(current.status) ? current : discovered;
}

/**
 * Prefer a live job; otherwise recover the newest completed job from the
 * owner-scoped history returned newest-first by the API.
 *
 * @template {{ status: string }} T
 * @param {T[]} items
 * @returns {T | null}
 */
export function recoverableJob(items) {
  return items.find((item) => ACTIVE_SCAN_STATUSES.has(item.status))
    ?? items.find((item) => item.status === "completed")
    ?? null;
}

/**
 * Never replace a job that is still progressing, but allow a completed job
 * to be rehydrated after the scan route has unmounted.
 *
 * @template {{ status: string }} T
 * @param {T | null} current
 * @param {T} recovered
 * @returns {T}
 */
export function preferRecoveredJob(current, recovered) {
  return current && ACTIVE_SCAN_STATUSES.has(current.status) ? current : recovered;
}

/**
 * Persisted jobs from earlier releases may not contain the aggregate summary
 * counters added later. Preserve their real rows/panels and supply neutral
 * display defaults so revisiting the scan route remains backward compatible.
 *
 * @template {Record<string, any>} T
 * @param {T} job
 * @returns {T}
 */
export function normalizeRecoveredScanJob(job) {
  const result = job?.result;
  if (!result || typeof result !== "object" || Array.isArray(result)) return job;
  return {
    ...job,
    result: {
      ...result,
      sonuclar: Array.isArray(result.sonuclar) ? result.sonuclar : [],
      basarisiz_taramalar: Array.isArray(result.basarisiz_taramalar) ? result.basarisiz_taramalar : [],
      boga_sayisi: Number.isFinite(result.boga_sayisi) ? result.boga_sayisi : 0,
      alim_firsati: Number.isFinite(result.alim_firsati) ? result.alim_firsati : 0,
    },
  };
}
