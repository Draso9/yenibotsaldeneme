"use client";

import { usePathname } from "next/navigation";

type UsageGuideSurface = "market" | "scan" | "detail" | "projection" | "performance" | "strategy";

type GuideCopy = {
  title: string;
  eyebrow: string;
  intro: string;
  badge: string;
  cards: Array<{ step: string; title: string; body: string }>;
  rule: string;
  notes: string[];
};

function usageGuideSurface(pathname: string): UsageGuideSurface | null {
  if (pathname.startsWith("/stocks/")) return "detail";
  if (pathname.startsWith("/scan")) return "scan";
  if (pathname.startsWith("/projection")) return "projection";
  if (pathname.startsWith("/performance")) return "performance";
  if (pathname.startsWith("/strategy-lab")) return "strategy";
  if (pathname === "/") return "market";
  return null;
}

const guideCopy: Record<UsageGuideSurface, GuideCopy> = {
  market: {
    title: "Piyasa Merkezi nasıl kullanılır?",
    eyebrow: "PİYASA MERKEZİ REHBERİ",
    intro: "Bir sonucu 30 saniyede değerlendirin: önce piyasa modunu, sonra listedeki karar dağılımını ve öne çıkan setup'ları okuyun.",
    badge: "GENEL BAKIŞ",
    cards: [
      { step: "1 · MOD", title: "Piyasa modunu okuyun", body: "Trend, momentum, para akışı ve risk bileşiminin son taramadaki ortak tonunu görün." },
      { step: "2 · DAĞILIM", title: "Karar sayılarını karşılaştırın", body: "Alım tarafı, güçlü setup, teyit bekleyen ve yüksek risk sayıları taranan listenin dengesini gösterir." },
      { step: "3 · LİSTE", title: "Öne çıkan hisseleri inceleyin", body: "Yedi öne çıkan hisseyi doğrudan karşılaştırın; ekstra sıralama seçimi olmadan taramanın canonical önem sırasını koruyun." },
      { step: "4 · DEVAM", title: "Tek hisseye inin", body: "Karar gerekçesi için Akıllı Tarama Karar Motoru'nu, teknik derinlik için Detaylı Analiz'i kullanın." },
    ],
    rule: "Piyasa modu resmi piyasa breadth verisi değildir; yalnızca son IZFIN taramasındaki listenin teknik bileşimidir.",
    notes: ["Skorlar karar vermez; kararı açıklar.", "Piyasa Merkezi tek bir hisse için işlem emri üretmez; listeyi hızlı okumaya yardım eder."],
  },
  scan: {
    title: "Akıllı Tarama nasıl kullanılır?",
    eyebrow: "AKILLI TARAMA REHBERİ",
    intro: "Evreni seçin, taramayı çalıştırın; merkezi kararı önce okuyup teyitleri ve riskleri birlikte değerlendirin.",
    badge: "KARAR ODAĞI",
    cards: [
      { step: "1 · EVREN", title: "Doğru evreni seçin", body: "BIST 30, BIST 100 veya Kendi Listenizden uygun evreni seçin; sonuçlar yalnızca taranan varlıkları karşılaştırır." },
      { step: "2 · KARAR", title: "Merkezi kararı önce okuyun", body: "İşlem yönünün merkezi kaynağı Karar Motoru'dur; tek bir skor veya indikatör üzerinden karar vermeyin." },
      { step: "3 · TEYİT", title: "Artı ve eksileri karşılaştırın", body: "Neden alınabilir ve neden beklenmeli bölümlerindeki teknik teyit ve risk gerekçelerini dengeli okuyun." },
      { step: "4 · RİSK", title: "İkinci hiyerarşiyi kontrol edin", body: "Güven, giriş kalitesi, MTF uyumu, risk ve teknik seviyeleri merkezi kararın bağlamı olarak değerlendirin." },
    ],
    rule: "Trend Adayı teknik profildir; Teyit Bekle giriş koşullarının eksik olduğunu belirtir. Algoritma güven puanı başarı olasılığı değildir. Karar Motoru işlem yönünün merkezi kaynağıdır; Detaylı Analiz aynı kararı tekrar etmek yerine teknik derinlik sağlar.",
    notes: ["Karar etiketleri nasıl yorumlanır? Etiketi güven, teyit ve risk bağlamıyla birlikte okuyun.", "Sonuç tablosundaki alanları birlikte okuyun; tek bir yüksek değer diğer riskleri geçersiz kılmaz."],
  },
  detail: {
    title: "Detaylı Analiz nasıl kullanılır?",
    eyebrow: "DETAYLI ANALİZ REHBERİ",
    intro: "Bu bölüm Karar Motoru'nu tekrarlamaz; Gelişmiş Skorun nedenini, göstergeleri, trend/momentumu ve teknik seviyeleri açar.",
    badge: "TEKNİK DERİNLİK",
    cards: [
      { step: "1 · SKOR", title: "Skorlar ne söylüyor?", body: "Gelişmiş Skor kartını açıp eski skoru, bonusları, cezaları, nihai skoru ve her kalemin gerekçesini okuyun." },
      { step: "2 · GÖSTERGE", title: "Göstergeleri birlikte okuyun", body: "Trend ve momentum göstergelerinin aynı yönü destekleyip desteklemediğini tek bir indikatöre bağlı kalmadan değerlendirin." },
      { step: "3 · SEVİYE", title: "Destek ve direnç bölgelerini kontrol edin", body: "Destek ve direnç seviyelerini stop, giriş ve teknik planın referans bölgeleri olarak kullanın." },
      { step: "4 · HEDEF", title: "Hedefleri teknik plan olarak görün", body: "TP seviyeleri garanti değildir; risk–ödül planının teknik senaryo noktalarıdır." },
    ],
    rule: "80 puan, %80 başarı ihtimali anlamına gelmez. Gelişmiş Skor otomatik AL değildir; risk ve merkezi Karar Motoru güçlü bir skoru sınırlayabilir.",
    notes: ["<50 Cezalı, 50–69 Nötr, >=70 Güçlü canonical bantları yalnızca teknik puanı sınıflandırır.", "Güçlü bantta dahi stop, volatilite ve haber riskini ayrıca değerlendirin."],
  },
  projection: {
    title: "Projeksiyon nasıl kullanılır?",
    eyebrow: "45G PROJEKSİYON REHBERİ",
    intro: "Projeksiyonu kesin fiyat tahmini değil, mevcut teknik yapıdan türetilen bantlar ve koşullu senaryolar olarak okuyun.",
    badge: "SENARYO",
    cards: [
      { step: "1 · BAĞLAM", title: "Doğru hisseyi doğrulayın", body: "Projeksiyonun hangi tarama ve ticker bağlamından geldiğini kontrol edin." },
      { step: "2 · BANT", title: "Merkez ve bantları birlikte okuyun", body: "Tek bir hedefe değil, olası yol ile üst/alt belirsizlik bantlarına birlikte odaklanın." },
      { step: "3 · KOŞUL", title: "Koşullu senaryo mantığını koruyun", body: "Teknik yapı veya piyasa koşulu değişirse önceki senaryonun geçerliliğinin azalabileceğini kabul edin." },
      { step: "4 · KARŞILAŞTIR", title: "Kararla bağlam kurun", body: "Projeksiyon karar üretmez; Akıllı Tarama ve Detaylı Analiz bağlamını tamamlar." },
    ],
    rule: "Projeksiyon fiyat garantisi değildir; yeni veri geldikçe teknik senaryo ve bantlar değişebilir.",
    notes: ["Olasılık, merkez yol ve bantları birlikte değerlendirin.", "Haber, bilanço ve gap hareketleri teknik projeksiyonu hızlı biçimde geçersiz kılabilir."],
  },
  performance: {
    title: "Performans nasıl kullanılır?",
    eyebrow: "PERFORMANS REHBERİ",
    intro: "Aktif pozisyon, kapanmış pozisyon ve performans karnesini birbirinden ayırarak modelin geçmiş davranışını okuyun.",
    badge: "GERİYE DÖNÜK",
    cards: [
      { step: "1 · AKTİF", title: "Aktif pozisyonları kontrol edin", body: "Açık takiplerin güncel durumunu ve henüz kapanmamış ölçümlerin geçmiş karneden farkını görün." },
      { step: "2 · KAPANMIŞ", title: "Kapanmış pozisyonları okuyun", body: "Hedef, stop ve diğer kapanış nedenlerini sonuçla birlikte inceleyin." },
      { step: "3 · KARNE", title: "Karne ufuklarını karşılaştırın", body: "1/5/10/20/45 günlük ölçümleri örneklem büyüklüğüyle birlikte okuyun; tek bir yüzdeye dayanmayın." },
      { step: "4 · VARLIK", title: "Varlık bazında karşılaştırın", body: "Tek bir hissenin toplam performans karnesini sürükleyip sürüklemediğini kontrol edin." },
    ],
    rule: "Hangi alan ne işe yarar? Aktif/kapanmış durum, başarı oranı, ortalama getiri, örneklem ve kapanış nedeni birlikte anlamlıdır.",
    notes: ["Geçmiş performans gelecekte aynı sonucu garanti etmez.", "Küçük örneklem uyarısını gördüğünüzde karne yüzdelerini daha temkinli yorumlayın."],
  },
  strategy: {
    title: "Strateji Lab nasıl kullanılır?",
    eyebrow: "STRATEJİ LAB REHBERİ",
    intro: "Backtest'i geçmişteki Daily Core karar davranışını incelemek için kullanın; bugünkü işlem sinyalinin yerine koymayın.",
    badge: "BACKTEST",
    cards: [
      { step: "1 · SEMBOL", title: "Varlık ve dönemi seçin", body: "3Y / 5Y / 10Y dönemlerinde yeterli veri kapsamı ve örneklem olup olmadığını kontrol edin." },
      { step: "2 · KPI", title: "Özet metrikleri okuyun", body: "Getiri, başarı, örneklem ve karar dağılımını tek başına değil birlikte değerlendirin." },
      { step: "3 · TABLO", title: "Geçmiş karar tablosunu açın", body: "Ayrıntılı tablo ile hangi tarihte, hangi koşulda ve hangi karar etiketinin oluştuğunu inceleyin." },
      { step: "4 · SINIR", title: "Backtest sınırını unutmayın", body: "Geçmiş veri, işlem maliyeti ve piyasa rejimi gelecekte farklı davranabilir." },
    ],
    rule: "Backtest sonuçları geçmiş veri üzerindeki model davranışını gösterir; canlı getiri vaadi değildir.",
    notes: ["Sonuçları dönemler ve örneklem büyüklükleri arasında karşılaştırın.", "IZFIN algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi veya getiri garantisi değildir."],
  },
};

export function UsageGuide() {
  const pathname = usePathname();
  const surface = usageGuideSurface(pathname);
  if (!surface) return null;
  const copy = guideCopy[surface];

  return <details className="usage-guide">
    <summary>
      <span>📘 Nasıl Kullanılır?</span>
      <b>{copy.title}</b>
      <em>Rehberi aç</em>
    </summary>
    <div className="usage-guide-body">
      <section className="usage-guide-section">
        <div className="usage-guide-head"><div><small>{copy.eyebrow}</small><h2>{copy.title}</h2><p>{copy.intro}</p></div><span>{copy.badge}</span></div>
        <div className="usage-guide-grid usage-guide-grid-four">
          {copy.cards.map((card) => <article key={card.step}><small>{card.step}</small><b>{card.title}</b><p>{card.body}</p></article>)}
        </div>
        <div className="usage-guide-rule"><small>ANA KURAL</small><p>{copy.rule}</p></div>
        <div className="usage-guide-notes">{copy.notes.map((note) => <p key={note}>{note}</p>)}</div>
      </section>
      <p className="usage-guide-warning">IZFIN analizleri açıklayıcı karar desteğidir; piyasa koşulları, haberler ve likidite teknik yapıyı değiştirebilir.</p>
    </div>
  </details>;
}
