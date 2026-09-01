# Checkpoint 6 — kapanış kontrolü

PR: #131 — `feat/checkpoint6-mobile-responsive` → `develop`.

Base: `e91d7bad8b70f7d0468ecfa2f529ff2a29e622b5`.
Bu oturumun başlangıç head'i: `cd0d4419f114f25d215ce49210160f707e420dbe`.

## Tamamlanan ek düzeltmeler

- Giriş, kayıt ve reset hataları ilgili inputlara `aria-invalid` / `aria-describedby` ile bağlandı. Parola gereksinimi ilişkilendirildi; tekrarlanan hatalı gönderimde de hata özeti odaklanır.
- Eski altı sütunlu mobil sidebar kuralları kaldırıldı. Tek alt menü yüksekliği ve safe-area boşluğu korunur. Mobil veri etiketleri okunabilir boyuta getirildi; ana telefon/tablet kontrolleri en az 44px yüksekliğindedir.
- Mobil Performans kartları masaüstü görünümüyle aynı seçili kapanmış pozisyon state'ini kullanır. İkincil tablo alanları açılır detayda korunur; eksik K/Z sıfır olarak gösterilmez.
- Tarama ilerleme kilidi gerçek native modal içinde canlı durum alanı kullanır. Geniş sonuç görünümü aynı DOM alt ağacını koruyarak modal olur; Escape/çıkış ve önceki odağa dönüş sağlanır. İlerleme kilidi tarama bitince kapanır.
- CP6 bileşen davranış testleri mevcut web CI kapısında çalıştırılır. Finansal hesaplama/API/veri servisi taşınmadı; yeni finansal veri üretilmedi.

## Yerel doğrulama

- TDD RED: form ilişkileri, eski sidebar, mobil okunabilirlik, kart detay bağlantısı, modal focus ve tekrar gönderim testleri uygulama öncesinde başarısız oldu.
- Node regresyonu: boş K/Z değerinin `0%` görünmesi gerçek React render'ıyla RED → GREEN doğrulandı.
- Python full: **575 passed**, mevcut Starlette/httpx deprecation uyarısı var.
- Node CP6: **4 passed**.
- Next.js typecheck: **PASS**.
- Next.js production build: **PASS**.
- `git diff --check`: **PASS**.
- `pnpm lint`: mevcut ESLint 9 flat config eksikliği nedeniyle çalışmıyor. Bu yapılandırma canonical Checkpoint 7 kapsamındadır; CP6 içinde değiştirilmedi.

## Açık kabul / release kapıları

Bu belge **Checkpoint 6 COMPLETE** kaydı değildir.

Tarayıcı servisi sayfa açma, tanılama ve yeniden başlatma sırasında transport/zaman aşımı hatası verdi. Bu nedenle aşağıdaki gerçek tarayıcı kontrolleri henüz yapılmış sayılmaz:

- 390×844, 768×1024, 1440×900: taşma, kesilme, menünün içeriği örtmemesi.
- Mobil Diğer menüsü, kart açılır detayları, Performans dönem inceleme yolu.
- Klavyeyle modal açma/kapama, Escape, arka plan izolasyonu ve odağın geri dönmesi.
- Form hatalarının ekran okuyucu/focus davranışı; rehber ve yasal metinlerin görsel kabulü.

Devam sırası: final PR head'inde iki GitHub CI kapısı → gerçek viewport kabulü → #131'in `develop`a merge edilmesi → exact merge SHA → post-merge CI → production Vercel exact SHA ve canlı smoke kontrolü.

`main` değiştirilmedi. Kullanıcının merge/yayın onayı geçerlidir; yalnız eksik kontroller tamamlanmadan merge yapılmaz.
