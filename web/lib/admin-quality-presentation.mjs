const READINESS_FIELDS = [
  ["Kimlik doğrulama", "authentication"],
  ["Kullanıcı deposu", "user_repository"],
  ["Sinyal deposu", "signal_repository"],
  ["Tarama motoru", "scan_runner"],
  ["Tarama iş deposu", "scan_job_store"],
  ["Kalıcı tarama kaydı", "scan_job_persistence"],
];

export function readinessHeadline(readiness) {
  return readiness?.ready
    ? "Tüm çekirdek servisler hazır"
    : "Bazı çekirdek servisler kısıtlı";
}

export function readinessCards(readiness) {
  if (!readiness) return [];
  return READINESS_FIELDS.map(([label, key]) => ({
    label,
    ready: readiness?.[key] === true,
  }));
}
