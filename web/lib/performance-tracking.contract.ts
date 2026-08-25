import { performancePositionsPath, type PerformancePositionsResponse } from "./performance";

const path: "/api/v1/performance/positions" = performancePositionsPath();
const shape: PerformancePositionsResponse = {
  kpis: [{ label: "Aktif Hisse", value: "1" }],
  active: [{ "Varlık": "THYAO.IS", "Kâr / Zarar %": 5 }],
  closed: [],
  closed_summary: { adet: 0 },
};

void path;
void shape;
