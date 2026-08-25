import { izfinApiFetch } from "./api";

export type BacktestMetric = {
  label: string;
  value: string;
};

export type BacktestKpis = {
  birincil: BacktestMetric[];
  ikincil: BacktestMetric[];
  belirsiz: number;
  belirsizlik_mesaji: string | null;
};

export type BacktestPeriod = "3y" | "5y" | "10y";

export type BacktestResponse = {
  ticker: string;
  period: string;
  empty: boolean;
  stats: Record<string, unknown>;
  kpis: BacktestKpis;
  summary: Array<Record<string, unknown>>;
  detail: Array<Record<string, unknown>>;
  ambiguity_count: number;
  ambiguity_message: string | null;
  detail_explanation: string;
  reading_notes: string;
};

export function backtestRunPath(): "/api/v1/backtest/run" {
  return "/api/v1/backtest/run";
}

export function runBacktest(
  idToken: string,
  ticker: string,
  period: BacktestPeriod = "5y",
): Promise<BacktestResponse> {
  return izfinApiFetch<BacktestResponse>(backtestRunPath(), idToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker: ticker.trim().toUpperCase(), period }),
  });
}
