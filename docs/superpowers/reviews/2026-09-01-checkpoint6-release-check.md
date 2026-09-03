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

Branch preview authenticated browser yeniden-kontrolü production Firebase/auth konfigürasyonu preview aliasında birebir bulunmadığı için temp QA hesabı bootstrap aşamasında kullanılamadı. Bu preview-env sınırlaması ürün regression'ı olarak değerlendirilmedi. Modal fix merge sonrası production üzerinde aynı gerçek senaryoyla tekrar doğrulanacaktır.

## Bilinçli olarak ertelenen son yayın ayarı — LEGAL

Production `/api/v1/legal/privacy` şu anda aşağıdaki üç deployment değerinin boş olduğunu açıkça gösteriyor:

- `IZFIN_DATA_CONTROLLER_NAME`
- `IZFIN_CONTACT_EMAIL`
- `IZFIN_DATA_CONTROLLER_ADDRESS`

Bu değerler gerçek kişi/kurum bilgisi gerektirdiği için uydurulmayacak. Ürün sahibi bu üç alanı gerçek halka açık yayın öncesindeki son legal-config adımına erteledi.

Bu nedenle durum ayrımı:

- **Teknik viewport/keyboard acceptance:** tamamlanma aşamasında; modal fix merge sonrası production re-check bekliyor.
- **Public legal publication readiness:** bilinçli olarak açık; gerçek veri sorumlusu adı/ünvanı, iletişim e-postası ve başvuru adresi girilmeden final public-release etiketi verilmemeli.

## Final kapanış kapıları

- [x] 390×844 gerçek viewport kabulü
- [x] 768×1024 gerçek viewport kabulü
- [x] 1440×900 gerçek viewport kabulü
- [x] mobil `Diğer` / usage-guide keyboard kontrolü
- [x] auth invalid-submit focus + ARIA ilişkileri
- [x] Performance dönem keyboard yolu
- [x] scan modal regression RED reproduksiyonu
- [ ] PR #142 final head Python + Web CI
- [ ] PR #142 → `develop` squash merge
- [ ] post-merge Python + Web CI
- [ ] production Vercel exact merge SHA
- [ ] production scan-modal focus-return re-check
- [ ] live health/readiness smoke
- [ ] final public release öncesi gerçek KVKK veri sorumlusu alanları

`main` değiştirilmedi. Finansal hesaplama, scan karar mantığı, projection matematiği, API response şekilleri ve auth semantics CP6 fix'i kapsamında değiştirilmedi.
