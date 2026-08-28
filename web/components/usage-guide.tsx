export function UsageGuide() {
  return <details className="usage-guide">
    <summary>
      <span>📘 Nasıl Kullanılır?</span>
      <b>IZFIN sonuçlarını doğru okuyun</b>
      <em>Rehberi aç</em>
    </summary>
    <div className="usage-guide-body">
      <section className="usage-guide-section">
        <div className="usage-guide-head"><div><small>IZFIN KISA REHBER</small><h2>Bir sonucu 30 saniyede değerlendirin</h2><p>Önce merkezi kararı, sonra kararın güvenini ve risk planını okuyun.</p></div><span>4 ADIM</span></div>
        <div className="usage-guide-grid usage-guide-grid-four">
          <article><small>1 · TARAMA</small><b>Evreni seçin</b><p>İzlemek istediğiniz listeyle Akıllı Tarama'yı çalıştırın.</p></article>
          <article><small>2 · KARAR</small><b>Aksiyonu okuyun</b><p>İlk referansınız puan değil, Merkezi Karar olsun.</p></article>
          <article><small>3 · TEYİT</small><b>Nedeni kontrol edin</b><p>Güven, giriş kalitesi ve MTF uyumunu birlikte değerlendirin.</p></article>
          <article><small>4 · PLAN</small><b>Riski belirleyin</b><p>Destek, stop ve hedefleri işlemden önce planlayın.</p></article>
        </div>
        <div className="usage-guide-rule"><small>ANA KURAL</small><p><b>Skorlar karar vermez; kararı açıklar.</b> İşlem yönünü trend, momentum, para akışı, zamanlama ve risk filtrelerini birlikte değerlendiren Merkezi Karar belirler.</p></div>
      </section>

      <section className="usage-guide-section">
        <div className="usage-guide-head"><div><small>DÖRT ANA GÖSTERGE</small><h2>Skorlar ne söylüyor?</h2><p>Her puan farklı bir soruya cevap verir; tek başına alım veya satım emri değildir.</p></div><span>0–100</span></div>
        <div className="usage-guide-grid usage-guide-grid-four">
          <article><small>IZFIN SKORU</small><b>Teknik yapı</b><p>Tablodaki Gelişmiş Skor; trend, momentum, hacim ve risk bileşimini özetler.</p></article>
          <article><small>GÜVEN</small><b>Kanıt uyumu</b><p>Kararı destekleyen teknik verilerin birbirleriyle ne kadar tutarlı olduğunu gösterir.</p></article>
          <article><small>GİRİŞ KALİTESİ</small><b>Zamanlama</b><p>5 dakika, 15 dakika ve 1 saat verilerinde giriş koşullarının olgunluğunu ölçer.</p></article>
          <article><small>MTF UYUM</small><b>Çoklu teyit</b><p>Farklı zaman dilimlerinin aynı yönü destekleyip desteklemediğini gösterir.</p></article>
        </div>
        <div className="usage-guide-rule"><small>ÖNEMLİ</small><p><b>80 puan, %80 başarı ihtimali anlamına gelmez.</b> Puanlar aynı taramadaki adayları karşılaştırmayı kolaylaştıran teknik ölçümlerdir.</p></div>
      </section>

      <section className="usage-guide-section">
        <div className="usage-guide-head"><div><small>MERKEZİ KARAR SÖZLÜĞÜ</small><h2>Karar etiketleri nasıl yorumlanır?</h2><p>Etiket, sistemin mevcut koşullarda önerdiği davranışı sade biçimde özetler.</p></div><span>GÜNCEL</span></div>
        <div className="usage-guide-grid usage-guide-grid-decisions">
          <article><small>EN GÜÇLÜ TEYİT</small><b>Güçlü Al</b><p>Trend, zamanlama, para akışı ve risk filtreleri birlikte olumlu.</p></article>
          <article><small>YETERLİ TEYİT</small><b>Al</b><p>Teknik yapı alım yönünü destekliyor; risk planı yine korunmalı.</p></article>
          <article><small>OLUMLU / ERKEN</small><b>Erken Al</b><p>Yapı olumlu ancak tüm güçlü teyitler henüz tamamlanmış değil.</p></article>
          <article><small>ADAY / EKSİK TEYİT</small><b>Teyit Bekle</b><p>Olumlu unsurlar var; final alım koşulları henüz yeterli değil.</p></article>
          <article><small>YÖN BELİRSİZ</small><b>İzle / Nötr</b><p>Göstergeler ortak ve yeterince güçlü bir işlem yönü üretmiyor.</p></article>
          <article><small>YENİ GİRİŞ ZAYIF</small><b>Kâr Koru</b><p>Aşırı ısınma veya momentum kaybı nedeniyle mevcut kazancı koruma öncelikli.</p></article>
          <article><small>SERMAYE KORUMA</small><b>Sat / Kaçın</b><p>Trend veya risk yapısı yeni pozisyon için yeterli avantaj sunmuyor.</p></article>
          <article><small>SON KONTROL</small><b>Gerekçeyi açın</b><p>Detay panelindeki olumlu teyitleri ve riskleri mutlaka okuyun.</p></article>
        </div>
      </section>

      <section className="usage-guide-section">
        <div className="usage-guide-head"><div><small>SONUÇ SATIRINI OKUMA</small><h2>Hangi alan ne işe yarar?</h2><p>Tek bir değere odaklanmak yerine kararın bütününü bu sırayla kontrol edin.</p></div><span>RİSK ÖNCE</span></div>
        <div className="usage-guide-grid usage-guide-grid-four usage-guide-compact">
          <article><small>1 · KARAR</small><b>Ne yapmalı?</b></article>
          <article><small>2 · RİSK</small><b>Ne bozabilir?</b></article>
          <article><small>3 · TEYİT</small><b>Ne destekliyor?</b></article>
          <article><small>4 · PLAN</small><b>Nerede vazgeçmeli?</b></article>
        </div>
        <div className="usage-guide-notes">
          <p><b>Risk:</b> Risk seviyesi ve olumsuz gerekçeler, yüksek görünen bir skoru sınırlandırabilir. Merkezi Karar bu çelişkileri sizin yerinize birlikte değerlendirir.</p>
          <p><b>Para akışı:</b> Fiyat hareketinin hacim ve para katılımıyla desteklenip desteklenmediğini gösterir. Zayıf akış, güçlü görünen hareketin kalıcılığını azaltabilir.</p>
          <p><b>PEG / değerleme:</b> Teknik karardan ayrı, tamamlayıcı bir değerleme bilgisidir. IZFIN Skoru'na veya Merkezi Karar'a doğrudan puan eklemez.</p>
          <p><b>Seans dışı:</b> ABD hisselerinde ek fiyat bilgisidir. Normal seans göstergelerini ve Giriş Kalitesi puanını değiştirmez.</p>
          <p><b>Stop / hedefler:</b> Stop teknik iptal noktasıdır; TP1, TP2 ve TP3 risk–ödül planlama seviyeleridir. Bunlar fiyat garantisi veya kesin tahmin değildir.</p>
        </div>
      </section>

      <p className="usage-guide-warning">IZFIN algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi veya getiri garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.</p>
    </div>
  </details>;
}
