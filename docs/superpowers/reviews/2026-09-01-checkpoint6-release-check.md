# Checkpoint 6 — kapanış kontrolü

Bu belge, PR #132 ile başlayan mobil/accessibility kapsamının final gerçek-tarayıcı release kabul kaydıdır.

## Tamamlanan temel yapı

- Giriş, kayıt ve reset hataları ilgili inputlara `aria-invalid` / `aria-describedby` ile bağlandı; hata özeti klavye akışında odak alıyor.
- Mobil navigasyon, safe-area boşluğu ve mobil veri kartları uygulanmış durumda.
- Tarama ilerleme kilidi native `<dialog>` tabanlı modal kullanıyor.
- CP6 component davranış testleri Web CI içinde çalışıyor.
- CP4 sonrasında Web gate sırası ESLint → typecheck → component tests → production build şeklinde çalışıyor.
- CP5 sonrasında Starlette/TestClient deprecation warning'i temizlendi.

## Gerçek Chromium viewport kabulü — 3 Eylül 2026

Production `https://izfin-web.vercel.app` üzerinde Playwright/Chromium ile gerçek viewport kontrolü yapıldı.

### 390×844 — mobil

Kritik authenticated/public route matrisi çalıştırıldı:

- `/auth`
- `/legal/terms`
- `/legal/privacy`
- `/`
- `/scan`
- `/projection`
- `/performance`
- `/strategy-lab`
- `/account`

Kontroller:

- yatay overflow / kesilen interaktif kontrol bulunmadı,
- mobil navigasyon görünür, desktop navigasyon gizli,
- içerik alt padding'i sabit mobil navigasyonu temizliyor,
- `Diğer` menüsü viewport dışında taşmıyor,
- route bazlı kullanım rehberi klavyeyle açılıp kapanabiliyor.

### 768×1024 — tablet

Aynı kritik workspace/public yüzeyleri kontrol edildi.

- yatay overflow / kesilen birincil kontrol bulunmadı,
- responsive navigasyon geçişi doğru,
- kart ve panel yapıları viewport içinde kaldı,
- kullanım rehberi ve legal yüzeyler erişilebilir kaldı.

### 1440×900 — desktop

Kritik desktop workspace yüzeyleri kontrol edildi.

- sidebar/topbar/content geometrisinde blocker bulunmadı,
- Piyasa Merkezi, Akıllı Tarama ve Projeksiyon kontrol edildi,
- ayrı hedefli turda Performans, Strateji Lab ve Hesap yüzeyleri de geçti,
- Performans dönem kontrolü klavyeyle `1G` → `45G` yolunda çalıştı.

## Klavye / focus kabulü

### Auth formu

Gerçek Chromium'da invalid submit sonrası:

- hata özeti focus aldı,
- e-posta ve parola inputları `aria-invalid=true` taşıdı,
- `aria-describedby` hata özetiyle bağlantılı kaldı.

### Scan modal

Gerçek tarama sırasında modalın native `:modal` olduğu ve focus'un dialog içine taşındığı doğrulandı.

Acceptance turu bir gerçek regression yakaladı: tarama tamamlandıktan sonra eski launch butonu kapatılmış/hidden ayar alanında kaldığında `ModalSurface` onu bağlı (`isConnected`) sanıyor, `.focus()` etkisiz kalıyor ve odak `BODY`'ye düşüyordu.

TDD kanıtı:

- RED run `33780810313`: yeni focused contract mevcut `ModalSurface` kodunda hidden opener görünürlük kontrolü ve deferred focus restoration olmadığı için kırıldı.
- Fix: focus dönüş hedefi `getClientRects().length > 0` ile görünürlük açısından doğrulanıyor; native dialog close işlemi sonrası `requestAnimationFrame` içinde geçerli opener'a, aksi halde `#main-content` fallback'ine odak veriliyor.
- Focused regression test kalıcı olarak `tests/test_checkpoint6_modal_focus_return.py` içinde tutuluyor.

Merge sonrası production re-check:

- PR #142 merge SHA: `265346151af1c64350281c894014b06b462a2995`
- production deployment: `dpl_E2nFdzXsAkVtHTk7KvKejKq6vnqg`
- QA-only real Chromium run: **33787610230**
- modal açılışında `isModal=true` ve focus dialog içindeydi,
- scan tamamlandıktan sonra `inMain=true`,
- aktif odak `DIV#main-content.app-content` oldu,
- temp QA hesabı test sonunda başarıyla silindi (`cleanup: deleted`).

Bu sonuçla modal focus regression'ı production üzerinde de kapandı.

## CI / production kapanış kanıtı

PR #142 final head:

- CI run `33787002223` → SUCCESS
- Python full suite → SUCCESS
- ESLint → SUCCESS
- Typecheck → SUCCESS
- component behavior tests → SUCCESS
- Next production build → SUCCESS

Post-merge `develop`:

- SHA `265346151af1c64350281c894014b06b462a2995`
- CI run `33787173807` → Python + Web SUCCESS
- Vercel production exact aynı SHA → READY
- `/izfin-api/api/v1/health` → HTTP 200 / `status=ok`
- `/izfin-api/api/v1/health/ready/durable` → HTTP 200 / tüm readiness alanları `true`

## Bilinçli olarak ertelenen son yayın ayarı — LEGAL

Production `/api/v1/legal/privacy` şu anda aşağıdaki üç deployment değerinin boş olduğunu açıkça gösteriyor:

- `IZFIN_DATA_CONTROLLER_NAME`
- `IZFIN_CONTACT_EMAIL`
- `IZFIN_DATA_CONTROLLER_ADDRESS`

Bu değerler gerçek kişi/kurum bilgisi gerektirdiği için uydurulmayacak. Ürün sahibi bu üç alanı gerçek halka açık yayın öncesindeki son legal-config adımına erteledi.

Bu nedenle durum ayrımı:

- **Teknik viewport/keyboard/release acceptance:** COMPLETE.
- **Public legal publication readiness:** bilinçli olarak açık; gerçek veri sorumlusu adı/ünvanı, iletişim e-postası ve başvuru adresi girilmeden final public-release etiketi verilmemeli.

Aynı final legal adımında eski altyapı anlatımları (`Streamlit Secrets` / `Streamlit Cloud`) mevcut Vercel + Cloud Run mimarisine göre yeniden doğrulanmalıdır.

## Final kapanış kapıları

- [x] 390×844 gerçek viewport kabulü
- [x] 768×1024 gerçek viewport kabulü
- [x] 1440×900 gerçek viewport kabulü
- [x] mobil `Diğer` / usage-guide keyboard kontrolü
- [x] auth invalid-submit focus + ARIA ilişkileri
- [x] Performance dönem keyboard yolu
- [x] scan modal regression RED reproduksiyonu
- [x] PR #142 final head Python + Web CI
- [x] PR #142 → `develop` squash merge
- [x] post-merge Python + Web CI
- [x] production Vercel exact merge SHA
- [x] production scan-modal focus-return re-check
- [x] live health/readiness smoke
- [ ] final public release öncesi gerçek KVKK veri sorumlusu alanları

**Checkpoint 6 teknik olarak COMPLETE.**

`main` değiştirilmedi. Finansal hesaplama, scan karar mantığı, projection matematiği, API response şekilleri ve auth semantics CP6 fix'i kapsamında değiştirilmedi.
