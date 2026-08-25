import { izfinPublicApiFetch } from "./api";

export type MarketStripItem = {
  ad: string;
  fiyat: number | null;
  deg: number | null;
  kaynak: string;
};

export type MarketStripResponse = {
  items: MarketStripItem[];
  durum: string;
  gecikme_sn: number | null;
  yerel_saat: string;
};

export function marketStripPath(): "/api/v1/market/strip" {
  return "/api/v1/market/strip";
}

export function fetchMarketStrip(): Promise<MarketStripResponse> {
  return izfinPublicApiFetch<MarketStripResponse>(marketStripPath());
}
