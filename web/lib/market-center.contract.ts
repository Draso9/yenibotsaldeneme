import {
  marketCenterJobPath,
  marketStockJobPath,
  type MarketCenterResponse,
  type StockDetailResponse,
} from "./market-center";

const centerPath: `/api/v1/market/jobs/${string}/center` = marketCenterJobPath("job-1");
const stockPath: `/api/v1/market/jobs/${string}/stocks/${string}` = marketStockJobPath("job-1", "thyao.is");

const centerShape: MarketCenterResponse = {
  empty: false,
  metrics: {},
  decision: {},
  best_ticker: "THYAO.IS",
  top_signals: [],
  movers: [],
};

const stockShape: StockDetailResponse = {
  ticker: "THYAO.IS",
  price: 100,
  signal: "GÜÇLÜ AL",
  entry_quality: "Yüksek",
  score: {},
  decision: {},
  action: {},
  panel: {},
};

void [centerPath, stockPath, centerShape, stockShape];

