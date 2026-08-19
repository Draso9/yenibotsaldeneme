# IZFIN v1.8.36 — Sortable Table Bind Fix

Bu paket, gönderilen düzleştirilmiş dosyaları GitHub/CI tarafından beklenen proje
yapısına geri yerleştirir ve canlı uygulama incelemesinde bulunan hataları düzeltir.

## Düzeltilenler

- Akıllı Tarama sonuç tablosunun sıralama betiğindeki iframe/üst belge arasında
  kararsız çalışan `MutationObserver` tamamen kaldırıldı. Tablo bağlama işlemi
  yavaş veri yüklemelerinde de çalışması için en fazla 120 saniye boyunca hafif
  aralıklarla bekliyor. Tablo artık yalnızca `tbody` ve sıralanabilir başlıklar
  gerçekten hazır olduğunda bağlandı olarak işaretleniyor; erken işaretleme
  nedeniyle sütun tıklamalarının çalışmaması giderildi.
- Google ile girişten sonra eski kalıcı oturumun geri yüklenmesine yol açabilen
  asenkron cookie `delete`/`set` yarışı kaldırıldı; yeni Firebase session cookie
  mevcut değerin üzerine tek işlemle ve 14 günlük güvenli seçeneklerle yazılıyor.
- Cookie bileşeni işlemlerine benzersiz anahtarlar verildi; aynı çalıştırmada
  oturum ve eski e-posta cookie'lerinin birbirinin işlemini engellemesi önlendi.
- Çıkış işleminde istemci tarafındaki cookie silme komutlarının tamamlanması için
  güvenli bekleme süresi artırıldı.
- Sayfalar arasında geçişte Projeksiyon başlığının önceki Akıllı Tarama anchor
  bağlantısını taşımasına neden olan Streamlit markdown yeniden kullanım sorunu
  giderildi; hero başlıkları kararlı HTML kimlikleriyle render ediliyor.
- Secrets dosyası bulunmayan ortamlarda `FINNHUB_API_KEY` okumasının uygulamayı
  çökertmesi engellendi; güvenli secret okuyucu kullanılıyor.
- Varsayılan Google OAuth yönlendirmesi güncel `izfin-develop.streamlit.app`
  adresine taşındı.
- Firebase/Google sağlayıcılarının ham teknik hata mesajlarının kullanıcıya
  yansıtılması engellendi; ayrıntılar sunucu logunda kalıyor.
- Akıllı Tarama, Projeksiyon, Takip ve Strateji Laboratuvarı başlıklarına kararlı
  ve benzersiz anchor kimlikleri verildi.
- Kişisel listede zaten bulunan sembol için yanıltıcı “Listeme Ekle” eylemi
  yerine devre dışı “Listemde” durumu gösteriliyor.
- Backtest sembol alanındaki Enter gereksinimi Türkçe ve görünür hâle getirildi.
- Sıfır sonuçlu tarama filtrelerine açıklayıcı boş durum eklendi.
- Teknik paneldeki iki geçersiz çift `class` niteliği birleştirildi.
- Harici sembol/açıklama metinleri HTML çıktısına eklenmeden önce kaçırılıyor.
- Firestore aktif pozisyon okuma hataları sessizce yutulmak yerine loglanıyor.
- Kullanılmayan import/değişkenler temizlendi; sürüm `v1.8.36` yapıldı.
- Yeni projeksiyon, giriş doğrulama, HTML güvenliği ve regresyon testleri CI
  akışına bağlandı.

## Doğrulama

- 57/57 Pytest testi geçti.
- Streamlit AppTest açılış ve secrets’sız fallback testleri geçti.
- Ruff `F`, `E9`, `B` kontrolleri temiz.
- Bandit taramasında orta/yüksek seviye bulgu yok.
- Canlı uygulamada 9 varlıklı Akıllı Tarama, filtreler, detay paneli,
  projeksiyon, takip yenileme, NVDA backtest’i ve geniş tablo görünümü çalıştı.
- 390 px mobil görünümde sayfa seviyesinde yatay taşma bulunmadı.

## Dağıtım notu

Paket içeriğini depo köküne kopyalayın. Üretim `secrets.toml` dosyasını repoya
eklemeyin. Google/Firebase yönetim ekranlarında
`https://izfin-develop.streamlit.app/` yönlendirme adresinin izinli olduğundan
emin olun.
