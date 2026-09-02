# IZFIN teknik sinyalleri

2 Eylül 2026 — Trend Adayı ve karar açıklamaları paketi.

## Kullanıcı için anlamları

**Teknik profil**, fiyat/gösterge yapısını sınıflandırır. **Merkezi karar**, bu yapı
için o tarama anında yeterli giriş teyidi olup olmadığını ve öncelikli riskleri
değerlendirir. Aynı hissede **Trend Adayı + Teyit Bekle** birlikte görülebilir.

| İfade | Ne anlatır? |
| --- | --- |
| Trend Adayı | Teknik trend/skor koşulları adaylık oluşturmuştur. Şirketin finansal sağlamlığını veya elde tutma süresini belirtmez. |
| Teyit Bekle | Alım yönündeki teknik profile rağmen alım dallarının koşulları tamamlanmamıştır. Sonraki kararın mutlaka AL olacağını söylemez. |
| Erken AL | Daha düşük teyit eşiklerini karşılayan teknik alım sınıfıdır. AL ve Güçlü AL ek koşullar ister. |
| AL | AL dalının koşulları sağlanmış ve öncelikli risk/kâr koruma kararı oluşmamıştır. |
| Güçlü AL | Daha yüksek puanlara ek olarak kısa trend ve momentum teyitleri de aranır. Getiri garantisi değildir. |
| İzle / Nötr | Yeterli ortak işlem yönü oluşmamıştır. |
| Kâr Al / Risk Azalt, Kâr Koru / Yeni Giriş Bekle | Aşırı ısınma, momentum veya risk bağlamında koruma kararıdır. |
| Sat / Kaçın, Riskten Kaçın | Motorun olumsuz trend/risk koşulları öncelik kazanmıştır. |

**Algoritma güven puanı: 80/100**, kurallı bir teknik uyum puanıdır. Ölçülmüş %80
başarı olasılığı anlamına gelmez. Giriş kalitesi giriş koşullarını, MTF uyumu zaman
dilimlerinin uyumunu özetler. Tek başına yüksek puan bir alım kararı üretmez.

Filtreler farklı alanlara bakar ve birbirini dışlamaz:

- **Trend Adayları:** teknik profili aday olan sonuçlar.
- **AL Sinyalleri:** merkezi alım kararları.
- **İzle / Bekle:** teyit bekleme, nötr izleme ve yeni giriş bekleme kararları;
  kâr koruma kararının yeni giriş bekleyen türü de bu gruptadır.

## Mevcut kurallar

Bu paket eşikleri değiştirmez. Aday etiketinin iki mevcut oluşum yolu vardır:

1. Ön-sinyal sınıflandırıcısında ana trend (fiyat > SMA200) ve skor ≥70.
   Öncelikli kırılım, aşırı ısınma veya diğer özel profil dalları önce değerlendirilir.
2. Sonraki profil sınıflandırıcısında fiyat > SMA200 ve EMA50, EMA9 > EMA21,
   skor ≥70 ve profilin aşırı ısınma koşulunun oluşmaması. Burada da özel profiller
   daha önce değerlendirilir. Ön adaylık ayrıca bu aşamadan korunarak geçebilir.

Dolayısıyla her Trend Adayı için EMA50/EMA9 teyitlerinin tamamlandığı iddia edilmez.
Eksik teyitler merkezi karar tarafından ayrıca değerlendirilir.

| Alım dalı | Güven puanı | Giriş puanı | MTF uyumu | CMF | Ek şart |
| --- | ---: | ---: | ---: | ---: | --- |
| Erken AL | ≥62 | ≥55 | ≥55 | ≥−0,05 | Ortak koşullar |
| AL | ≥70 | ≥65 | ≥60 | ≥−0,03 | SuperTrend yukarı |
| Güçlü AL | ≥80 | ≥80 | ≥70 | ≥0 | SuperTrend yukarı, EMA9 > EMA21, MACD > sinyal ve +DI ≥ −DI |

Ortak koşullar: alım yönünde profil; fiyat SMA200 ve EMA50 üzerinde; yüksek
risk/panik, sahte kırılım ve merkezi motorun aşırı ısınma engellerinin olmaması.
Merkezi aşırı ısınma koşulu RSI ≥70 ile fiyatın üst Bollinger bandının en az
%99,5'ine ulaşmasının birlikte gerçekleşmesidir. Önce satış/kaçınma ve kâr
koruma dalları, sonra Güçlü AL → AL → Erken AL değerlendirilir.

“Neden bu karar? Hangi teyit eksik?” bölümü bu **aynı Python koşullarından**
sağlanan/eksik listelerini üretir. Örneğin güven 69, giriş 64, MTF 59 ise AL için
gereken 70/65/60 eşikleri açıkça görülür; Erken AL koşulları ayrıca değerlendirilir.
Bu açıklama tarama anına aittir; yeni piyasa verisi veya ikinci bir karar üretmez.

## Uygulama ve uyumluluk

- Python tarama, profil ve geçmiş test motorları yeni adı üretir. Web ve Streamlit
  eski `UZUN VADELİ ADAY` kayıtlarını da yeni adla gösterir ve filtreler.
- Eski kayıtlar/veritabanı yeniden yazılmaz. Ham karar alanları ve puanları korunur.
- Güven puanı tablo, kart, piyasa özeti ve geçmiş işlem görünümlerinde `/100`
  biçimindedir. Geçmiş test sunumunun `Güven %` alanı `Güven puanı` olarak
  gösterilir; web eski API alanını da kabul eder. Gerçek getiri yüzdeleri değişmez.
- Eksik veri sıfıra dönüştürülmez. Eksik/bozuk girdilerde veya kayıtlı karar ve
  puanlarla uyuşmayan bir açıklamada ayrıntılı teyit gösterilmez; kayıt korunur.
- Karar kartı ayrıntılı gerekçeyi taşır; Detaylı Analiz yalnız kısa profil/karar
  bağlamı verir ve teknik göstergeleri açar.
- Yeni bağımlılık, veri sağlayıcı çağrısı, SEC bağlantısı veya React finansal
  hesaplaması eklenmez. SEC/finansal değerlendirme çalışması ertelenmiştir.
- Projeksiyonun ayrı model güveni bu sinyal puanı paketi kapsamında değiştirilmez.

## Doğrulama

RED → GREEN: aday adı, eski/yeni filtre üyeliği, mobil/Streamlit sunumu,
gerçek alım eşikleri, öncelikli kâr koruma, eski kayıt uyuşmazlığı, eksik/bozuk veri.

- Python full suite: 608 test geçti (mevcut tek Starlette/httpx uyarısı).
- Web gerçek bileşen testleri: 10 test geçti; CI bu testlerin tamamını çalıştırır.
- Next.js typecheck ve production build geçti; iki GitHub CI kapısı merge öncesi zorunlu.
- Mevcut sürümle bağımsız 10.000 teknik girdi karşılaştırmasında merkezi karar
  çıktıları birebir korundu. Bu bir yatırım performansı ölçümü değildir.
- Yerel CPU ölçümü: 3.000 tekrarın üç koşusundan en düşük ortalama;
  karar başına önce 0,0145 ms, sonra 0,0199 ms; 100 karar için fark 0,54 ms.
  Seçilen detayın teyit açıklaması yaklaşık 0,0317 ms. Bunlar uçtan uca canlı
  tarama süresi değildir; ağ isteği eklenmediği ayrıca test edilir.

Sonraki ayrı iş: etiketler kullanıcı tarafından değerlendirildikten sonra sinyal
eşiklerinin geçmiş veri performansını incelemek. Bu paket eşik optimizasyonu veya
şirket finansal kalite puanı eklemez. Önceki checkpointlerin açık canlı kabul
işlerini de kendiliğinden tamamlanmış saymaz.
