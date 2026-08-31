const TURKISH_MONTHS = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];
const ISO_DATE_TIME = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/;

function renderAccountDate(year, monthNumber, day, hour, minute) {
  const month = TURKISH_MONTHS[monthNumber - 1];
  if (!month) return "Henüz kaydedilmedi";
  return `${day} ${month} ${year} · ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function formatAccountDate(value) {
  const text = String(value || "").trim();
  const match = text.match(ISO_DATE_TIME);
  if (match) {
    return renderAccountDate(match[1], Number(match[2]), Number(match[3]), match[4], match[5]);
  }

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return "Henüz kaydedilmedi";
  return renderAccountDate(
    parsed.getUTCFullYear(),
    parsed.getUTCMonth() + 1,
    parsed.getUTCDate(),
    parsed.getUTCHours(),
    parsed.getUTCMinutes(),
  );
}

export function accountProfileSummary(profile, identityEmail, authMetadata = {}) {
  const source = profile && typeof profile === "object" ? profile : {};
  return {
    email: String(identityEmail || source.email || "—"),
    createdAt: formatAccountDate(
      source.olusturma_zamani || source.created_at || authMetadata.creationTime,
    ),
    lastLogin: formatAccountDate(
      source.son_giris || source.last_login || authMetadata.lastSignInTime,
    ),
  };
}
