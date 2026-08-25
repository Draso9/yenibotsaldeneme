import { projectionHref, projectionJobPath, type ProjectionResponse } from "./projection";

const apiPath: `/api/v1/projection/jobs/${string}/stocks/${string}` = projectionJobPath("job 1", "THYAO.IS");
const pageHref: `/projection?${string}` = projectionHref("job 1", "THYAO.IS");

const projectionShape: ProjectionResponse = {
  ticker: "THYAO.IS",
  horizon_days: 45,
  model: {},
  scenario: {},
  metrics: { birincil: [], ikincil: [], guven_ilerleme: 0, volatilite_aciklamasi: "" },
  bands: [
    { kind: "downside", label: "Aşağı bant", target: 90, extreme: 80, change_pct: -10 },
    { kind: "base", label: "Baz", target: 100, extreme: 100, change_pct: 0 },
    { kind: "upside", label: "Yukarı bant", target: 110, extreme: 120, change_pct: 10 },
  ],
};

void apiPath;
void pageHref;
void projectionShape;
