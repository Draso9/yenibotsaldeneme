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
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  completed: number;
  total: number;
  tickers: string[];
  current_ticker?: string | null;
  error?: string;
  projectable_tickers?: string[];
  result?: {
    sonuclar?: Array<Record<string, unknown>>;
    basarisiz_taramalar?: string[];
    boga_sayisi?: number;
    alim_firsati?: number;
    teknik_paneller?: Record<string, Record<string, unknown>>;
  };
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
  const projectable = job.projectable_tickers ?? Object.keys(job.result?.teknik_paneller ?? {});
  const normalized = projectable
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);
  return [...new Set(normalized)];
}

export function resolveTicker(explicitTicker: string, rememberedTicker: string, availableTickers: string[]): string {
  const normalized = availableTickers.map((ticker) => ticker.trim().toUpperCase()).filter(Boolean);
  const available = new Set(normalized);
  const explicit = explicitTicker.trim().toUpperCase();
  if (explicit && available.has(explicit)) return explicit;
  const remembered = rememberedTicker.trim().toUpperCase();
  if (remembered && available.has(remembered)) return remembered;
  return normalized.length === 1 ? normalized[0] : "";
}
