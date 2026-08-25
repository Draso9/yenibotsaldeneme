import type { ComponentProps } from "react";
import { StrategyLabPage } from "./strategy-lab-page";
import { backtestRunPath, type BacktestResponse } from "../lib/backtest";

const props: ComponentProps<typeof StrategyLabPage> = {};
const path: "/api/v1/backtest/run" = backtestRunPath();
const shape: BacktestResponse = {
  ticker: "NVDA",
  period: "5y",
  empty: false,
  stats: { sinyal: 1 },
  kpis: {
    birincil: [{ label: "Bağımsız Test İşlemi", value: "1" }],
    ikincil: [],
    belirsiz: 0,
    belirsizlik_mesaji: null,
  },
  summary: [{ Sinyal: "AL 🟢", "Örnek": 1 }],
  detail: [{ Tarih: "2026-01-02", Sinyal: "AL 🟢" }],
  ambiguity_count: 0,
  ambiguity_message: null,
  detail_explanation: "detay",
  reading_notes: "notlar",
};

void props;
void path;
void shape;
