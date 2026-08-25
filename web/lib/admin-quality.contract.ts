import { adminQualityPath, type AdminQualityResponse } from "./admin-quality";

const path: "/api/v1/admin/quality" = adminQualityPath();
const shape: AdminQualityResponse = {
  metrics: {
    python_satir: 1,
    css_satir: 1,
    important: 0,
    media_query: 0,
    hardcoded_hex: 0,
    design_token_kullanimi: 0,
    gecersiz_design_token: 0,
    "10px_alti_font": 0,
    inline_style: 0,
    unsafe_html: 0,
  },
  status: { durum: "SAĞLIKLI", seviye: "success", notlar: ["ok"] },
};

void path;
void shape;
