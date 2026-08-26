# IZFIN Web Tasarım Sistemi ve Piyasa Merkezi

**Durum:** Onaylanmış tasarım yönü — uygulama planına geçiş için hazır
**Tarih:** 26 Ağustos 2026
**Hedef dal:** `develop` tabanlı `feat/web-design-system`

## Amaç

IZFIN'in mevcut Streamlit kimliğini terk etmeden, Next.js web deneyimini
birincil arayüz olacak seviyede tutarlı, yoğun veri okuyabilen ve mobilde
uyarlanabilir bir tasarım sistemine taşımak. İlk somut ekran Piyasa Merkezi
olacaktır. Streamlit uygulaması, API sözleşmeleri ve `main` bu çalışma ile
değişmeyecektir.

## Ürün İlkeleri

- Koyu lacivert/siyaha yakın zemin; turkuazdan maviye geçen IZFIN vurgu dili.
- Masaüstünde sabit sol navigasyon, dar ekranda erişilebilir kompakt navigasyon.
- Gösterişli boş alan yerine okunabilir finansal veri yoğunluğu.
- Her canlı/veri benzeri alan güncellik veya kaynak durumunu dürüstçe belirtir;
  doğrulanmamış veri için gerçek zamanlı izlenimi verilmez.
- Sinyal, skor, güven ve yön aynı görsel dilde okunur; renk tek başına anlam
  taşımaz.
- "Fırsat Haritası" ayrı bir ekran ya da navigasyon maddesi olmayacaktır.

## Bilgi Mimarisi

Masaüstü sol menü sırası: Piyasa Merkezi, Akıllı Tarama, Projeksiyon,
Performans, Strateji Lab, Hesap; yetkili kullanıcı için Admin QA sonradan
eklenir. Mevcut rota ve API davranışları korunur.

Piyasa Merkezi şu bloklardan oluşur:

1. Güncellik durumlu piyasa özet kartları (BIST, ABD endeksleri, VIX, ons,
   USD/TRY; gerçek veri yalnız ilgili sözleşme sağlıyorsa gösterilir).
2. Kullanıcının listesindeki öne çıkan sinyaller için satır tablosu:
   sembol, fiyat, IZFIN kararı, skor, güven, kısa yön/bağlam.
3. Günlük Büyük Hareketler: mevcut kaynakların doğruladığı hareketli hisseler
   listesi. Yükselenler, düşenler ve hacim sekmeleri ancak API bu kategorileri
   ayrı veri olarak sunduğunda eklenir.
4. Kısa piyasa modu/bağlam özeti ve tarama-veri durumu.

Tasarım, sayfa boş veya oturum kapalıyken de doğru bir boş durum sunar;
uydurma fiyat, skor veya canlılık bilgisi göstermez.

## Tasarım Tokenları

Mevcut `web/app/globals.css` değişkenleri genişletilerek tek bir token katmanı
oluşturulur. Tüketici bileşenler doğrudan yeni hex renkler tanımlamaz.

- **Renk:** arka plan, yükseltilmiş yüzey, kenarlık, ana metin, ikincil metin,
  turkuaz başarı/pozitif, mavi bilgi, kırmızı negatif ve sarı uyarı.
- **Ölçek:** 4px tabanlı boşluk; küçük/orta/büyük köşe yarıçapları; masaüstü
  sıkı veri düzeni için sabit tablo satır yüksekliği.
- **Tipografi:** okunabilir gövde metni; değerler için tabular-numeric;
  minik ama erişilebilir etiketler. 10px altına inilmez.
- **Durumlar:** hover, klavye odağı, yükleniyor, boş, hata ve devre dışı
  durumları ortak kurallarla gösterilir.

## Bileşen Sınırları

- `app-shell`: marka, menü, oturum/sistem durumu ve responsive navigasyon.
- `market-strip`: piyasa özet kartlarını API verisi ile sunar; veri yoksa
  açık bir bekleme/erişilemiyor durumu gösterir.
- `market-center`: kullanıcı listesindeki sinyaller, seçili hisse özeti ve
  günlük hareketleri API sınırını geçmeden biçimlendirir.
- Paylaşılan CSS tokenları ve ortak durum stilleri; sayfa-özel CSS yalnız
  yerleşim için kalır.

Bileşenler hesaplama veya veri sağlayıcı seçimi yapmaz. Veriyi mevcut API
istemcileri üzerinden alır; ileride Finnhub gibi ücretli bir sağlayıcıya geçiş
yalnız backend/adaptör katmanını etkiler.

## Responsive Davranış

- **Geniş ekran:** sabit sol menü, çok sütunlu kartlar ve yoğun tablo.
- **Tablet:** menü daralır; kartlar iki sütuna, yan panel alta geçer.
- **Mobil:** sol menü gizlenir ve erişilebilir alt navigasyon/drawer kullanır;
  tablo temel alanları koruyan kartlara dönüşür veya kontrollü yatay kaydırma
  sunar. Dokunma hedefleri en az 44px olur.

Bu kurallar web düzeninin mobil uygulamaya bire bir CSS aktarılmasını değil,
aynı token, hiyerarşi ve etkileşim dilinin taşınmasını sağlar.

## Hata, Gizlilik ve Erişilebilirlik

- Kimlik doğrulama gerekli alanlar kullanıcıya açıkça anlatılır; başka
  kullanıcının listesi hiçbir koşulda görünmez.
- API hataları tüm ekranı bozmaz; yalnız ilgili kart/alan tekrar deneme veya
  açıklayıcı hata durumuna geçer.
- Klavye odağı görünür, kontrast yeterli, ikonların metin karşılığı vardır.
- Admin QA menüsü yalnız mevcut sunucu tarafı yetki kontrolü başarılıysa görünür.

## Kapsam ve Teslim Sırası

1. Tokenların ve uygulama kabuğunun konsolidasyonu.
2. Piyasa Merkezi: piyasa bandı, kullanıcı sinyalleri, günlük büyük hareketler
   ve dürüst veri durumları.
3. Aynı sistemi Akıllı Tarama, Projeksiyon, Performans, Strateji Lab ve Hesap
   sayfalarına aşamalı uygulama.
4. Ayrı bir kararla web önizleme/deploy noktası oluşturma.

Bu paket yalnız 1–2. adımı uygular. Yeni veri sağlayıcı, yeni mobil uygulama,
backend sözleşmesi değişikliği ve Streamlit görünümünü kaldırma kapsam dışıdır.

## Doğrulama

- TypeScript typecheck ve production build.
- Mevcut web kalite testleri ile Piyasa Merkezi sözleşme/boş-hata durumları.
- Responsive görünüm için hedef kırılımlarda manuel kontrol.
- PR hedefi `develop`; GitHub CI yeşil olmadan merge edilmez. Merge sonrası
  `develop` CI ayrıca doğrulanır.
