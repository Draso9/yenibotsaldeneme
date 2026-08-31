# IZFIN Web Tamamlama Programı — Tasarım Belgesi

**Tarih:** 2026-08-31  
**Durum:** Kullanıcı tarafından onaylandı; checkpoint bazlı uygulama bekliyor  
**Canonical ürün referansı:** Streamlit (`app2.py`, `izfin_ui/`)  
**Hedef dal:** `develop`  

## 1. Amaç

Next.js + FastAPI web uygulamasını Streamlit ürününün işlevsel anlamını bozmadan yayınlanabilir düzeye getirmek. Program; doğrulanmış yasal/kimlik açıklarını, yanlış veya eksik veri davranışlarını, analiz bağlamı sürekliliğini, bilgi tekrarlarını, görsel tutarsızlığı, mobil kullanım sorunlarını ve kalite kapılarını ayrı checkpoint'ler halinde kapatır.

Bu program yeni finansal özellik üretmez. Python iş mantığını React'e taşımaz ve gerçek veriyi dekoratif/mock verilerle değiştirmez.

## 2. Değişmez Kurallar

- `main` dalına dokunulmaz.
- Her checkpoint güncel `origin/develop` tabanlı ayrı feature branch'te uygulanır.
- Başka sohbetlerdeki açık worktree ve değişikliklere dokunulmaz.
- Her davranış değişikliği TDD RED → GREEN ile geliştirilir.
- Finansal hesaplamalar Python servislerinde kalır.
- Auth recovery, retry, job sahipliği, tarama recovery, durable readiness ve same-origin API proxy korunur.
- Her checkpoint bağımsız incelenebilir ve geri çevrilebilir büyüklükte tutulur.
- İlgili testler, tam Python paketi, web lint, typecheck ve production build yeşil olmadan PR açılmaz.
- İki GitHub CI kapısı yeşil olmadan `develop` merge edilmez.
- Her checkpoint canlı kullanıcı kabulüyle kapanır.

## 3. Uygulama Yaklaşımı

Program risk ve işlev öncelikli yürütülür:

1. Yasal ve kimlik güvenliği
2. Gerçek veri davranışı
3. Tarama/analiz durum sürekliliği
4. Bilgi mimarisi ve tekrarların kaldırılması
5. Görsel sistem ve Streamlit marka paritesi
6. Mobil/responsive kullanım
7. Admin, kalite kapıları ve tam yayın kabulü

Görsel değişiklikler, yanlış çalışan akışların üzerini örtmemesi için ilk üç checkpoint'ten sonra yapılır.

## 4. Checkpoint 1 — Giriş, Kayıt ve Yasal Onay Güvenliği

### Hedef

Streamlit'teki sürümlü yasal onay kapısını webde eksiksiz ve fail-closed biçimde kurmak; e-posta ve Google kullanıcılarını aynı hesap başlangıç sözleşmesine bağlamak.

### Gereksinimler

- Kayıt ekranında Kullanım Koşulları ve KVKK Aydınlatma Metni tıklanabilir ve girişsiz okunabilir olmalıdır.
- E-posta kaydı profil, başlangıç kişisel listesi ve açıkça kabul edilen belge sürümlerini kaydetmelidir.
- Google ile ilk giriş profil ve başlangıç kişisel listesini idempotent biçimde hazırlamalıdır.
- Google girişi kullanıcı adına yasal onayı otomatik vermemelidir.
- Güncel belge sürümlerini kabul etmemiş kullanıcı, korumalı uygulama ekranlarına geçememelidir.
- Yasal onay kontrolü okunamazsa uygulama fail-closed kalmalı; hata, tekrar deneme ve çıkış seçenekleri sunulmalıdır.
- Belge sürümü değiştiğinde yeniden onay istenmelidir.
- Oturum kalıcılığı Streamlit ile aynı biçimde varsayılan açık `Beni hatırla` seçeneğiyle yönetilir. Açıkken Firebase local persistence, kapalıyken session persistence kullanılır.
- Şifreyle oluşturulan hesap, Firebase `emailVerified` değeri doğru olana kadar korumalı uygulama ekranlarına geçemez; doğrulama kapısı yeniden e-posta gönderme ve çıkış seçenekleri sunar. Google sağlayıcısının Firebase tarafından doğrulanmış e-postası bu kapıyı geçer.

### Kabul Senaryoları

- Yeni e-posta kullanıcısı belgeleri açar, kabul eder ve doğru profile sahip olur.
- Yeni Google kullanıcısı bootstrap edilir, ardından açık yasal onay verir.
- Eski belge sürümüne sahip kullanıcı yeniden onay kapısına düşer.
- Onay servisi ulaşılamazken korumalı sayfa açılmaz.
- Kullanıcı onay kapısından güvenli biçimde çıkış yapabilir.
- Başka kullanıcının profil veya onayı kullanılamaz.

## 5. Checkpoint 2 — Piyasa Merkezi ve Performans Doğruluğu

### Piyasa Merkezi

- Hatalı ve gereksiz `Sonuç sırası: Skor/Risk` kontrolü kaldırılır.
- Dikkat çeken hisseler Python servisinin canonical önem sırasını korur.
- Piyasa şeridi ilk mount ile sınırlı kalmaz; 60 saniyede bir, pencere odağı ve bağlantı dönüşünde yeniden doğrulanır.
- Tazelik süresi ekranda ilerler; ilk snapshot değerinde donmaz.
- Yenileme hatasında son geçerli veri korunur ve stale durumu açıkça gösterilir.

### Performans

- `Verileri yenile` yalnız GET/refetch yapmaz; owner-scoped sunucu güncellemesi başlatır.
- Güncel fiyat, aktif K/Z ve uygun yeni performans ölçümleri Python servisinde hesaplanır.
- Streamlit ufukları `1/5/10/20/45` webde canonical seçenekler olur.
- Yenileme idempotent ve aynı kullanıcıya ait kayıtlarla sınırlı olur.
- Paralel tıklamalar aynı işi çoğaltmaz.
- Arayüz; yenileniyor, güncel, veri kaynağı hatası ve zaten güncel durumlarını ayırır.
- Hata halinde mevcut performans geçmişi bozulmaz.

### Kabul Senaryoları

- Piyasa şeridi açık sayfada güncel kalır.
- Risk sıralama kontrolü artık bulunmaz.
- Performans yenilemesi gerçek repository değişimi üretir.
- `1/5/10/20/45` karne sonuçları Streamlit sözleşmesiyle aynıdır.
- Bir kullanıcı diğer kullanıcının pozisyonlarını güncelleyemez.

## 6. Checkpoint 3 — Akıllı Tarama Durum Sürekliliği

### Gereksinimler

- Seçili tarama profili ortak analiz context'inden hydrate edilir.
- BIST 30, BIST 100 ve Kendi Listem hızlı kartları ile gerçek form tek React state kullanır.
- `document.querySelector`, prototype setter, gecikmeli DOM retry ve programlı buton tıklama kaldırılır.
- Seçilen karar ticker'ı kullanıcıya özel kalıcı context'e yazılır.
- Piyasa Merkezi dönüşünde job, sonuçlar, seçili ticker, karar kartı ve profil korunur.
- Detay ve Projeksiyon dönüşlerinde aynı job/ticker korunur.
- Daha yeni aktif sunucu job'ı eski terminal job'ın önüne geçer; mevcut aktif job gereksiz yere değiştirilmez.
- Geçici ağ hataları üstten sınırlı retry ile devam eder.
- Başka kullanıcıya veya silinmiş job'a ait cache güvenli biçimde reddedilir.

### Kabul Senaryosu

`Tarama başlat → hisse seç → Piyasa Merkezi → Akıllı Tarama` yolculuğu aynı tarama, profil ve hisseyle geri açılır.

## 7. Checkpoint 4 — Bilgi Mimarisi ve Tekrarların Kaldırılması

### Akıllı Tarama

- Hisseye özel karar motoru merkezi karar yüzeyi olur.
- Dropdown seçimi ve tablo satırı seçimi aynı ticker state'ini kullanır.
- Merkezi karar ana görsel vurgu olur.
- Neden alınabilir ve neden beklenmeli/alınmamalı metinleri dengeli ve okunabilir yerleşir.
- Güven, giriş kalitesi, MTF, risk ve teknik seviyeler ikinci hiyerarşide gösterilir.

### Detaylı Analiz

Karar motorundaki uzun tekrarlar kaldırılır:

- merkezi kararın tam açıklaması,
- uzun olumlu teyit tekrarı,
- uzun risk gerekçesi tekrarı,
- aynı güven/MTF/giriş profili kartları.

Detaylı Analizde kısa bağlam özeti, teknik göstergeler, trend/momentum, destek/direnç, stop/hedefler, skor bileşenleri, algoritma teknik yorumu ve Projeksiyon geçişi kalır.

### Gelişmiş Skor Açıklaması

Canonical bantlar:

- `<50`: Cezalı
- `50–69`: Nötr
- `>=70`: Güçlü

Ekran mevcut skoru, eski skoru, bonusları, cezaları, nihai skoru ve her kalemin gerekçesini gösterir. Yüksek skorun otomatik `AL` veya başarı olasılığı olmadığı; risk ve merkezi kararın skoru sınırlayabileceği açıklanır.

### Sayfaya Özel Rehberler

- Piyasa Merkezi: piyasa modu ve öne çıkanların okunması
- Akıllı Tarama: evren, karar, teyit ve risk
- Detaylı Analiz: skor, göstergeler ve teknik seviyeler
- Projeksiyon: bantlar ve koşullu senaryolar
- Performans: aktif/kapanmış pozisyon ve karne
- Strategy Lab: backtest, örneklem ve tablo yorumlama
- Hesap ve Admin QA: finansal rehber gösterilmez

Rehber yalnız ilgili sayfada ve kullanıcı açtığında görünür.

## 8. Checkpoint 5 — Tasarım Sistemi ve Görsel Parite

### Marka

- Streamlit'teki canonical logo tek web asset'i olur.
- Yan menü, auth, favicon ve başlık aynı asset'i kullanır.
- Logo ortalı, dairesel, kalın uyumlu çerçeveli olur.
- Piyasa Merkezi başlığındaki metinsel `IZ` kaldırılır.

### Tipografi ve Hiyerarşi

- Ana başlıklar yaklaşık `30–44px`, bölüm başlıkları `20–28px` ölçeğinde kurulur.
- Normal açıklamalar masaüstünde en az `13–14px` olur.
- Kullanıcıya bilgi taşıyan `7–8px` metinler kaldırılır.
- Kritik karar/risk yalnız renkle değil etiket ve font ağırlığıyla ayrılır.

### Token ve Kart Sistemi

- Zemin, yükseltilmiş yüzey, çizgi, ana/ikincil metin, olumlu, uyarı, risk ve bilgi renkleri tek token katmanında tanımlanır.
- Aynı sınıfı farklı CSS dosyalarında ezme azaltılır.
- Repo-geneli tek seferlik CSS yeniden yazımı yapılmaz; dokunulan bileşenler kademeli taşınır.
- Kart iç boşluğu, köşe yarıçapı, başlık ve etiket düzeni standartlaştırılır.
- Kontrast ve focus görünürlüğü doğrulanır.

## 9. Checkpoint 6 — Mobil ve Responsive Kullanım

### Navigasyon

- Alt menü sabit altı sütun varsayımından çıkarılır.
- Mobil ana yapı kesin olarak Piyasa, Tarama, Projeksiyon, Performans ve Diğer öğelerinden oluşur.
- Strategy Lab, Hesap ve yetkili kullanıcı için Admin QA `Diğer` alanında bulunur.
- Detaylı Analiz bağlamsal başlık/back akışı olarak kalır; alt menüye yeni satır eklemez.
- Safe-area ve içerik alt boşluğu gerçek menü yüksekliğini karşılar.

### Veri Yüzeyleri

- Tarama mobil öncelikleri: hisse, karar, skor, risk; ikincil alanlar açılır detayda gösterilir.
- Performans mobilde kart-öncelikli olur.
- Strategy Lab özet KPI'ları üstte, işlem detayları açılır bölümde olur.
- Masaüstü tablolar korunabilir; gerekli yatay tablolarda ilk sütun sabitlenebilir.

### Erişilebilirlik

- Ana dokunma hedefleri yaklaşık `44px` olur.
- Klavye, focus, modal/rehber focus yönetimi ve form hata ilişkileri doğrulanır.
- Yasal metinler semantik başlık ve listelerle render edilir.
- `390x844`, tablet ve masaüstü görünümleri kabul testine girer.

## 10. Checkpoint 7 — Admin, Kalite Kapıları ve Yayın Kabulü

### Admin QA

- Menü yetkisi için tam kalite endpoint'ine istek atılmaz; hafif capability sınırı kullanılır.
- Normal kullanıcıdaki beklenen 403 gürültüsü kaldırılır.
- Streamlit ve web statik kalite ölçümleri ayrı sunulur.
- Web ölçümleri TSX/CSS, küçük font, hardcoded renk, unsafe HTML ve kalite komutlarını kapsar.

### Geliştirici Kapıları

- ESLint 9 flat config eklenir ve `pnpm lint` çalışır.
- Web CI lint + typecheck + production build + ilgili davranış testlerini kapsar.
- Python CI tam pytest, API sözleşmesi, sahiplik ve yasal güvenlik testlerini kapsar.
- Starlette TestClient/httpx deprecation borcu doğrulanmış bağımlılık geçişiyle kapatılır.

### Tam Canlı Yolculuk

1. E-posta hesabı oluşturma ve yasal kabul
2. Google ilk giriş ve yasal kabul
3. Kişisel liste düzenleme
4. Tarama profili seçme ve tarama başlatma
5. Hisse seçimi ve karar motoru
6. Piyasa Merkezi gidiş-dönüş state doğrulaması
7. Detaylı Analiz ve skor açıklaması
8. Projeksiyon ticker değişimi
9. Gerçek Performans yenilemesi
10. Strategy Lab backtest
11. Veri indirme
12. Normal kullanıcı Admin reddi
13. Admin QA erişimi
14. Çıkış, yeniden giriş ve recovery
15. Masaüstü ve mobil görsel/işlevsel kabul

## 11. Yayın Tamamlanma Ölçütü

- Tüm checkpoint'ler `develop` üzerinde merge edilmiştir.
- Python ve web CI kapıları yeşildir.
- Herkese açık yayın adresi Vercel ekip girişi istemez.
- Durable readiness hazırdır.
- Mobil navigasyon içeriği örtmez.
- Streamlit karşılaştırmasında kritik işlev açığı kalmaz.
- Kullanıcı tam canlı yolculuğu kabul eder.

## 12. Checkpoint Branch Sırası

1. `fix/auth-legal-consent-gate`
2. `fix/market-performance-correctness`
3. `fix/scan-state-continuity`
4. `feat/information-hierarchy-guides`
5. `feat/streamlit-visual-system`
6. `feat/mobile-responsive-close`
7. `chore/release-quality-gates`

Her branch bir önceki checkpoint `develop`e merge edildikten sonra güncel `origin/develop`den açılır.
