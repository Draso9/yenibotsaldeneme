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
};

export function performanceScorecardPath(days = 20): `/api/v1/performance/scorecard?${string}` {
  const normalized = Math.max(1, Math.min(365, Math.round(days)));
  return `/api/v1/performance/scorecard?gun=${normalized}`;
}

export function fetchPerformanceScorecard(idToken: string, days = 20): Promise<PerformanceScorecardResponse> {
  return izfinApiFetch<PerformanceScorecardResponse>(performanceScorecardPath(days), idToken);
}
