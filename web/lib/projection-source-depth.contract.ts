import { projectionHref, type ProjectionResponse } from "./projection";

type ScenarioSide = ProjectionResponse["technical_scenarios"]["up"];

const up: ScenarioSide = {
  title: "Yükseliş / Alım Senaryosu",
  trigger: "106.00 üzeri kalıcılık + RSI 50 üstü + MACD yukarı kesişim",
  targets: [112, 120],
  model_bands: [110, 120],
  risk_invalidation: 92,
};

const response: ProjectionResponse = {
  ticker: "THYAO.IS",
  available_tickers: ["THYAO.IS", "AKBNK.IS"],
  horizon_days: 45,
  model: {},
  scenario: {},
  technical_scenarios: {
    up,
    down: {
      title: "Düşüş / Satış Baskısı",
      trigger: "94.00 altı kapanış + RSI 40 altı veya MACD negatifliğinin güçlenmesi",
      model_bands: [90, 80],
      invalidation: 106,
    },
  },
  metrics: { birincil: [], ikincil: [], guven_ilerleme: 0, volatilite_aciklamasi: "" },
  bands: [],
};

const nextTicker: `/projection?${string}` = projectionHref("job-1", response.available_tickers[1]);
void nextTicker;
void response;
