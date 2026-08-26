import type { ComponentProps } from "react";
import { PerformancePage } from "./performance-page";
import { performanceScorecardPath, type PerformanceScorecardResponse } from "../lib/performance";

const props: ComponentProps<typeof PerformancePage> = {};
const path: `/api/v1/performance/scorecard?${string}` = performanceScorecardPath(20);
const shape: PerformanceScorecardResponse = {
  metrikler: [{ label: "İsabet", value: "%62" }],
  kucuk_orneklem: false,
  bos_mesaj: null,
  kayit_adedi: 42,
  gun: 20,
  ozet: [{ Varlık: "THYAO.IS", "Sinyal Sayısı": 2 }],
  detay: [{ Varlık: "THYAO.IS", "Sinyal Tarihi": "01.08.2026" }],
  medyan_alfa_mesaji: "Medyan göreceli performans (alfa): %+3.10",
};

void props;
void path;
void shape;
