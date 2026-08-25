import { izfinApiFetch } from "./api";

export type MarketCenterResponse = {
  empty: boolean;
  metrics: Record<string, unknown>;
  decision: Record<string, unknown>;
  best_ticker?: string | null;
  top_signals: Array<Record<string, unknown>>;
  movers: Array<Record<string, unknown>>;
};

export type StockDetailResponse = {
  ticker: string;
  price?: unknown;
  signal?: unknown;
  entry_quality?: unknown;
  score: Record<string, unknown>;
  decision: Record<string, unknown>;
  panel: Record<string, unknown>;
};

export function marketCenterJobPath(jobId: string): `/api/v1/market/jobs/${string}/center` {
  return `/api/v1/market/jobs/${encodeURIComponent(jobId)}/center`;
}

export function marketStockJobPath(jobId: string, ticker: string): `/api/v1/market/jobs/${string}/stocks/${string}` {
  return `/api/v1/market/jobs/${encodeURIComponent(jobId)}/stocks/${encodeURIComponent(ticker)}`;
}

export function fetchMarketCenter(jobId: string, idToken: string): Promise<MarketCenterResponse> {
  return izfinApiFetch<MarketCenterResponse>(marketCenterJobPath(jobId), idToken);
}

export function fetchMarketStockDetail(jobId: string, ticker: string, idToken: string): Promise<StockDetailResponse> {
  return izfinApiFetch<StockDetailResponse>(marketStockJobPath(jobId, ticker), idToken);
}
