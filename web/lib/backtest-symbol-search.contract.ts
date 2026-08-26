import {
  backtestSymbolSearchPath,
  searchBacktestSymbols,
  type BacktestSymbolSearchResponse,
} from "./backtest";

const path: `/api/v1/scan/symbols?q=${string}&limit=${number}` = backtestSymbolSearchPath("nvda", 8);
const response: BacktestSymbolSearchResponse = {
  query: "nvda",
  suggestions: [
    { symbol: "NVDA", name: "NVIDIA Corporation", exchange: "NMS", quote_type: "EQUITY" },
  ],
};

void path;
void response;
void searchBacktestSymbols;
