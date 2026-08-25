import { izfinApiFetch } from "./api";

export type ProjectionBand = {
  kind: "downside" | "base" | "upside";
  label: string;
  target: number;
  extreme: number;
  change_pct: number;
};

export type ProjectionMetrics = {
  birincil: Array<Record<string, unknown>>;
  ikincil: Array<Record<string, unknown>>;
  guven_ilerleme: number;
  volatilite_aciklamasi: string;
};

export type ProjectionResponse = {
  ticker: string;
  horizon_days: number;
  model: Record<string, unknown>;
  scenario: Record<string, unknown>;
  metrics: ProjectionMetrics;
  bands: ProjectionBand[];
};

export function projectionJobPath(jobId: string, ticker: string): `/api/v1/projection/jobs/${string}/stocks/${string}` {
  return `/api/v1/projection/jobs/${encodeURIComponent(jobId)}/stocks/${encodeURIComponent(ticker)}`;
}

export function projectionHref(jobId: string, ticker: string): `/projection?${string}` {
  return `/projection?job_id=${encodeURIComponent(jobId)}&ticker=${encodeURIComponent(ticker)}`;
}

export function fetchProjection(jobId: string, ticker: string, idToken: string): Promise<ProjectionResponse> {
  return izfinApiFetch<ProjectionResponse>(projectionJobPath(jobId, ticker), idToken);
}
