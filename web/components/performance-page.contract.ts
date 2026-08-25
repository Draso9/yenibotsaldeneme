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
};

void props;
void path;
void shape;
