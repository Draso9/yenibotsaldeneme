import { izfinApiFetch } from "./api";

export type PerformanceMetric = {
  label: string;
  value: string;
};

export type PerformanceScorecardResponse = {
  metrikler: PerformanceMetric[];
  kucuk_orneklem: boolean;
  bos_mesaj: string | null;
  kayit_adedi: number;
  gun: number;
  ozet: Array<Record<string, unknown>>;
  detay: Array<Record<string, unknown>>;
  medyan_alfa_mesaji: string | null;
};

export type PerformancePositionsResponse = {
  kpis: PerformanceMetric[];
  active: Array<Record<string, unknown>>;
  closed: Array<Record<string, unknown>>;
  closed_summary: Record<string, unknown>;
};

export function performanceScorecardPath(days = 20): `/api/v1/performance/scorecard?${string}` {
  const normalized = Math.max(1, Math.min(365, Math.round(days)));
  return `/api/v1/performance/scorecard?gun=${normalized}`;
}

export function performancePositionsPath(): "/api/v1/performance/positions" {
  return "/api/v1/performance/positions";
}

export function fetchPerformanceScorecard(idToken: string, days = 20): Promise<PerformanceScorecardResponse> {
  return izfinApiFetch<PerformanceScorecardResponse>(performanceScorecardPath(days), idToken);
}

export function fetchPerformancePositions(idToken: string): Promise<PerformancePositionsResponse> {
  return izfinApiFetch<PerformancePositionsResponse>(performancePositionsPath(), idToken);
}
