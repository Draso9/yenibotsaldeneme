/** Presentation only: keep persisted values and Python decisions intact. */
export const trendExplanation = "Trend Adayı, teknik trend koşullarını karşılayan varlığı gösterir. Alım zamanlamasını merkezi karar belirler; şirketin finansal sağlamlığı bu etiketle değerlendirilmez.";
export const confidenceExplanation = "Algoritma güven puanı teknik uyumu özetler; ölçülmüş başarı olasılığı değildir.";

export function technicalProfile(value: unknown): string {
  return String(value ?? "—").replace(/uzun vadel[iİı] aday/giu, "TREND ADAYI") || "—";
}

export function confidenceScore(value: unknown): string {
  if (value === null || value === undefined || typeof value === "boolean") return "—";
  const raw = String(value).trim().replaceAll("%", "").replace(/\/100$/, "").trim().replace(",", ".");
  if (!/^\d+(?:\.\d+)?$/.test(raw)) return "—";
  const number = Number(raw);
  return Number.isFinite(number) && number >= 0 && number <= 100 ? `${number}/100` : "—";
}

export function isTrendCandidate(row: Record<string, unknown>): boolean {
  return technicalProfile(row["Teknik Profil"]).toLocaleUpperCase("tr-TR").includes("TREND ADAYI");
}
