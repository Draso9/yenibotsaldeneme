import type {
  PerformanceClosedSummary,
  PerformancePositionsResponse,
} from "../lib/performance";
import {
  PerformancePositionTrackingView,
  PerformanceScorecardView,
} from "./performance-view";

const closedSummary: PerformanceClosedSummary = {
  adet: 12,
  unique_tickers: 5,
  win_rate: 58.3,
  avg_ret: 4.2,
  median_ret: 2.1,
  median_days: 11,
  tp1_rate: 66.7,
  stop_rate: 25,
  best_txt: "THYAO.IS %+14.2",
  worst_txt: "EREGL.IS %-7.1",
  yorumlar: ["Örnek performans yorumu"],
  reason_counts: [["Sinyal sona erdi", 7], ["Stop", 3]],
};

const positions: PerformancePositionsResponse = {
  kpis: [{ label: "Aktif Hisse", value: "2" }],
  active: [],
  closed: [{
    "İlk Alım Tarihi": "01.08.2026 10:00",
    "Kapanış Tarihi": "12.08.2026 10:00",
    "Varlık": "THYAO.IS",
    "Son Alım Sinyali": "Kusursuz Alım",
    "Kapanış Nedeni": "Sinyal sona erdi",
    "İlk Alım Fiyatı": 300,
    "Kapanış Fiyatı": 330,
    "Kâr / Zarar %": 10,
    "Pozisyonda Gün": 11,
    "Maks. Kâr %": 14,
    "Maks. Düşüş %": -3,
    "İlk Stop": 285,
    "İlk TP1": 315,
    "TP1": "✅",
    "TP2": "❌",
    "TP3": "❌",
    "Stop": "❌",
  }],
  closed_summary: closedSummary,
};

void positions;
void PerformancePositionTrackingView;
void PerformanceScorecardView;
