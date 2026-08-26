import { izfinApiFetch } from "./api";

export type AdminQualityMetrics = {
  python_satir: number;
  css_satir: number;
  important: number;
  media_query: number;
  hardcoded_hex: number;
  design_token_kullanimi: number;
  gecersiz_design_token: number;
  "10px_alti_font": number;
  inline_style: number;
  unsafe_html: number;
};

export type AdminQualityStatus = {
  durum: string;
  seviye: "success" | "warning";
  notlar: string[];
};

export type AdminQualityResponse = {
  app_release: string;
  metrics: AdminQualityMetrics;
  status: AdminQualityStatus;
};

export function adminQualityPath(): "/api/v1/admin/quality" {
  return "/api/v1/admin/quality";
}

export function fetchAdminQuality(idToken: string): Promise<AdminQualityResponse> {
  return izfinApiFetch<AdminQualityResponse>(adminQualityPath(), idToken);
}
