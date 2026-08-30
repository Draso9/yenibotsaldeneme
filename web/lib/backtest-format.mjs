const TICKER_STORAGE_PREFIX = "izfin:strategy-lab:last-ticker";
const FORMAT_DIGITS = /\.(\d+)f/;

function storageKey(uid) {
  const owner = String(uid || "").trim();
  return owner ? `${TICKER_STORAGE_PREFIX}:${owner}` : "";
}

export function formatBacktestValue(column, value, formats) {
  if (value === null || value === undefined || value === "") return "—";
  const pattern = formats[column];
  const numeric = Number(value);
  if (!pattern || !Number.isFinite(numeric)) {
    return typeof value === "number"
      ? value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })
      : String(value);
  }

  const digits = Number(pattern.match(FORMAT_DIGITS)?.[1] ?? 0);
  const rendered = numeric.toLocaleString("tr-TR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  const sign = pattern.includes("+") && numeric >= 0 ? "+" : "";
  const suffix = pattern.endsWith("%") ? "%" : "";
  return `${sign}${rendered}${suffix}`;
}

export function readStrategyTicker(storage, uid) {
  const key = storageKey(uid);
  if (!key) return "";
  try {
    return String(storage.getItem(key) || "").trim().toUpperCase();
  } catch {
    return "";
  }
}

export function writeStrategyTicker(storage, uid, ticker) {
  const key = storageKey(uid);
  const normalized = String(ticker || "").trim().toUpperCase();
  if (!key || !normalized) return;
  try {
    storage.setItem(key, normalized);
  } catch {
    // Session storage may be unavailable in hardened browser modes.
  }
}
