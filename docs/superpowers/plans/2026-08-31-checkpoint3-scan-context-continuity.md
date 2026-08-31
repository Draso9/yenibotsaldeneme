# Checkpoint 3 — Akıllı Tarama Durum Sürekliliği Uygulama Planı

Canonical scope: `docs/superpowers/specs/2026-08-31-web-completion-program-design.md`, Checkpoint 3 only.

## Goal
Akıllı Tarama profilini, aktif işi ve seçili karar motoru ticker'ını tek React/shared-context akışında tutmak; route değişimlerinden sonra aynı kullanıcıya ait doğrulanmış server state ile güvenli biçimde geri yüklemek.

## Task 1 — Tek React state ve DOM hack temizliği
- RED: Quick controls içinde `document.querySelector`, prototype setter, retry-by-timeout ve programmatic `.click()` kullanımını yasaklayan testler.
- GREEN: `activeUniverseProfile` shared context tek source-of-truth olacak.
- Quick controls kontrollü props/callback kullanacak; ScanWorkspace ile React üzerinden bağlanacak.
- Hisse arama focus/scroll işlemleri React ref ile yapılacak; launch doğrudan submit callback çağıracak.

## Task 2 — Seçili ticker sürekliliği
- RED: ScanResult'ın ayrı local selectedTicker tutmasını yasakla; shared `selectedTicker` ve setter kullanımını zorunlu kıl.
- GREEN: remembered ticker mevcut sonuçlarda varsa korunacak; yoksa ilk geçerli ticker fallback olarak seçilip shared context'e yazılacak.
- Tablo seçimi ve ScanDecisionCard ticker değişimi aynı shared setter'ı kullanacak.

## Task 3 — Owner-safe job/cache recovery
- RED: cache'deki activeScanJobId server-side owner-scoped job endpoint ile doğrulanmadan kullanılmamalı.
- RED: server history'deki queued/running job terminal cache/job'a göre öncelikli olmalı; mevcut in-memory active job gereksiz yere değiştirilmemeli.
- GREEN: cached job 404/403/deleted/stale ise güvenli fallback history recovery çalışacak.

## Task 4 — Bounded transient recovery
- RED: backoff yalnız gecikme açısından değil deneme sayısı açısından da üstten sınırlı olmalı.
- GREEN: helper ile maksimum recovery retry sayısı tanımlanacak; geçici hata halinde retry yapılacak, limit sonrası sonsuz döngü olmayacak.

## Verification
- Targeted Checkpoint 3 tests RED→GREEN.
- Complete `python -m pytest -q`.
- Web typecheck + production build.
- `pnpm lint` preflight: flat ESLint config yoksa Checkpoint 7 blocker olarak raporla, config ekleme.
- PR -> `develop`; post-merge CI green.
- Vercel production READY on merge SHA.

## Live acceptance
`Akıllı Tarama → profil seç → tarama başlat → ticker seç → Piyasa Merkezi → Akıllı Tarama` dönüşünde aynı profile/job/results/ticker/decision card. Ardından Detay ve Projeksiyon gidip dönünce de aynı job/ticker korunmalı.
