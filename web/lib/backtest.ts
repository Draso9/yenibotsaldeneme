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

export type BacktestSymbolSuggestion = {
  symbol: string;
  name: string;
  exchange: string;
  quote_type: string;
};

export type BacktestSymbolSearchResponse = {
  query: string;
  suggestions: BacktestSymbolSuggestion[];
};

export function backtestRunPath(): "/api/v1/backtest/run" {
  return "/api/v1/backtest/run";
}

export function backtestSymbolSearchPath(
  query: string,
  limit = 8,
): `/api/v1/scan/symbols?q=${string}&limit=${number}` {
  return `/api/v1/scan/symbols?q=${encodeURIComponent(query.trim())}&limit=${Math.max(1, Math.min(limit, 15))}`;
}

export function searchBacktestSymbols(
  idToken: string,
  query: string,
  limit = 8,
): Promise<BacktestSymbolSearchResponse> {
  return izfinApiFetch<BacktestSymbolSearchResponse>(backtestSymbolSearchPath(query, limit), idToken);
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
