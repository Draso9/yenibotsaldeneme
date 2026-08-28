import { performancePositionsPath, type PerformancePositionsResponse } from "./performance";

const path: "/api/v1/performance/positions" = performancePositionsPath();
const shape: PerformancePositionsResponse = {
  kpis: [{ label: "Aktif Hisse", value: "1" }],
  active: [{ "Varlık": "THYAO.IS", "Kâr / Zarar %": 5 }],
  closed: [],
  closed_summary: {
    adet: 0,
    unique_tickers: 0,
    win_rate: null,
    avg_ret: null,
    median_ret: null,
    median_days: null,
    tp1_rate: null,
    stop_rate: null,
    best_txt: "—",
    worst_txt: "—",
    yorumlar: [],
    reason_counts: [],
  },
};

void path;
void shape;
