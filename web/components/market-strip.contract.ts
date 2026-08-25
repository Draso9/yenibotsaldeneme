import type { ComponentProps } from "react";
import { MarketStrip } from "./market-strip";
import { marketStripPath, type MarketStripResponse } from "../lib/market-strip";

const props: ComponentProps<typeof MarketStrip> = {};
const path: "/api/v1/market/strip" = marketStripPath();
const shape: MarketStripResponse = {
  items: [{ ad: "BIST 100", fiyat: 12345.6, deg: 1.25, kaynak: "Yahoo 1 dk" }],
  durum: "YAKIN CANLI",
  gecikme_sn: 42,
  yerel_saat: "23:30:00",
};

void props;
void path;
void shape;
