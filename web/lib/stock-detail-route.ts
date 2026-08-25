export function stockDetailHref(jobId: string, ticker: string): string {
  const normalizedTicker = String(ticker || "").trim().toUpperCase();
  return `/stocks/${encodeURIComponent(normalizedTicker)}?job_id=${encodeURIComponent(jobId)}`;
}
