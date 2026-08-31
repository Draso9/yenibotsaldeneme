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
    intro: "Bir sonucu 30 saniyede değerlendirin: önce piyasa modunu, sonra listedeki karar dağılımını ve öne çıkan setup'ı okuyun.",
    badge: "GENEL BAKIŞ",
    cards: [
      { step: "1 · MOD", title: "Piyasa tonunu okuyun", body: "Trend, momentum, para akışı ve risk bileşiminin son taramadaki ortak tonunu görün." },
      { step: "2 · DAĞILIM", title: "Karar sayılarını karşılaştırın", body: "Alım tarafı, güçlü setup, teyit bekleyen ve yüksek risk sayıları taranan listenin dengesini gösterir." },
      { step: "3 · LİSTE", title: "Dikkat çekenleri inceleyin", body: "Yedi öne çıkan hisseyi doğrudan karşılaştırın; ekstra sıralama seçimi olmadan taramanın mevcut önceliğini koruyun." },
      { step: "4 · DETAY", title: "Tek hisseye inin", body: "Karar gerekçesi için Akıllı Tarama Karar Motoru'nu, teknik derinlik için Detaylı Analiz'i kullanın." },
    ],
    rule: "Piyasa modu resmi piyasa breadth verisi değildir; yalnızca son IZFIN taramasındaki listenin teknik bileşimidir.",
    notes: ["Skorlar karar vermez; kararı açıklar.", "Piyasa Merkezi tek bir hisse için işlem emri üretmez; listeyi hızlı okumaya yardım eder."],
  },
  scan: {
    title: "Akıllı Tarama nasıl kullanılır?",
    eyebrow: "AKILLI TARAMA REHBERİ",
    intro: "Evreni seçin, taramayı çalıştırın ve karar kartında neden alınabilir / neden beklenmeli ayrımını okuyun.",
    badge: "KARAR ODAĞI",
    cards: [
      { step: "1 · EVREN", title: "Doğru listeyi seçin", body: "Kendi listenizi veya profili belirleyin; sonuçlar yalnızca taranan varlıkları karşılaştırır." },
      { step: "2 · KARAR", title: "Merkezi kararı önce okuyun", body: "Sinyal, güven, risk ve MTF birlikte değerlendirilir; tek bir skor üzerinden karar vermeyin." },
      { step: "3 · NEDEN", title: "Artı ve eksileri karşılaştırın", body: "Olumlu teyitleri ve bekleme / kaçınma nedenlerini yan yana okuyun." },
      { step: "4 · DEVAM", title: "Tekniğe derinleşin", body: "Skorun nedenleri, seviyeler ve hedefler için Detaylı Analiz'e geçin." },
    ],
    rule: "Karar Motoru işlem yönünün merkezi kaynağıdır; Detaylı Analiz aynı kararı tekrar etmek yerine teknik derinlik sağlar.",
    notes: ["Karar etiketleri nasıl yorumlanır? Güçlü Al / Al daha fazla teyit, Teyit Bekle ise eksik koşul anlamına gelir.", "Sonuç tablosundaki alanları birlikte okuyun; tek bir yüksek değer diğer riskleri geçersiz kılmaz."],
  },
  detail: {
    title: "Detaylı Analiz nasıl kullanılır?",
    eyebrow: "DETAYLI ANALİZ REHBERİ",
    intro: "Bu bölüm Karar Motoru'nu tekrarlamaz; Gelişmiş Skorun nedenini, teknik göstergeleri, seviyeleri ve işlem planını açar.",
    badge: "TEKNİK DERİNLİK",
    cards: [
      { step: "1 · SKOR", title: "Skorlar ne söylüyor?", body: "Gelişmiş Skor kartını açıp bonusları, cezaları ve temel teknik kalemleri ayrı ayrı okuyun." },
      { step: "2 · YAPI", title: "Trend ve momentumu kontrol edin", body: "Göstergelerin aynı yönü destekleyip desteklemediğini, tek bir indikatöre bağlı kalmadan değerlendirin." },
      { step: "3 · SEVİYE", title: "Destek ve direnci okuyun", body: "Teknik seviyeleri giriş, iptal ve risk planının referans bölgeleri olarak kullanın." },
      { step: "4 · HEDEF", title: "Hedefleri senaryo olarak görün", body: "TP seviyeleri garanti değildir; teknik risk–ödül planının senaryo noktalarıdır." },
    ],
    rule: "80 puan, %80 başarı ihtimali anlamına gelmez. Skor bandı mevcut teknik puanı açıklar; işlem yönünü Karar Motoru belirler.",
    notes: ["Cezalı / Zayıf bantlarda ceza kalemlerinin baskın olup olmadığına bakın.", "Güçlü / Çok Güçlü bantlarda dahi stop, volatilite ve haber riskini ayrıca değerlendirin."],
  },
  projection: {
    title: "Projeksiyon nasıl kullanılır?",
    eyebrow: "45G PROJEKSİYON REHBERİ",
    intro: "Projeksiyonu kesin fiyat tahmini değil, mevcut teknik yapıdan türetilen olasılıklı senaryo haritası olarak okuyun.",
    badge: "SENARYO",
    cards: [
      { step: "1 · BAĞLAM", title: "Doğru hisseyi doğrulayın", body: "Projeksiyonun hangi tarama ve ticker bağlamından geldiğini kontrol edin." },
      { step: "2 · SENARYO", title: "Merkez ve bantları birlikte okuyun", body: "Tek bir hedefe değil, olası yol ve belirsizlik aralığına odaklanın." },
      { step: "3 · RİSK", title: "Bozulma koşulunu izleyin", body: "Teknik yapı değişirse önceki senaryonun geçerliliğinin azalabileceğini kabul edin." },
      { step: "4 · KARŞILAŞTIR", title: "Kararla bağlam kurun", body: "Projeksiyon karar üretmez; Akıllı Tarama ve Detaylı Analiz bağlamını tamamlar." },
    ],
    rule: "Projeksiyon fiyat garantisi değildir; yeni veri geldikçe teknik senaryo değişebilir.",
    notes: ["Olasılık ve bantları birlikte değerlendirin.", "Haber, bilanço ve gap hareketleri teknik projeksiyonu hızlı biçimde geçersiz kılabilir."],
  },
  performance: {
    title: "Performans nasıl kullanılır?",
    eyebrow: "PERFORMANS REHBERİ",
    intro: "Sinyal kalitesini tek bir kazanç oranıyla değil; dönem, örneklem, kapanış nedeni ve varlık dağılımıyla birlikte okuyun.",
    badge: "GERİYE DÖNÜK",
    cards: [
      { step: "1 · DÖNEM", title: "20G / 60G / 120G'yi ayırın", body: "Kısa ve daha uzun dönem skorlarının aynı davranışı gösterip göstermediğini karşılaştırın." },
      { step: "2 · ÖRNEKLEM", title: "Sinyal sayısını kontrol edin", body: "Az sayıda işlem yüksek veya düşük oranları olduğundan daha güçlü gösterebilir." },
      { step: "3 · NEDEN", title: "Kapanış nedenlerini okuyun", body: "Hedef, stop ve diğer kapanış nedenlerinin dağılımı sonuç kalitesini anlamaya yardım eder." },
      { step: "4 · VARLIK", title: "Hisse bazında karşılaştırın", body: "Tek bir varlığın toplam performansı sürükleyip sürüklemediğini kontrol edin." },
    ],
    rule: "Hangi alan ne işe yarar? Başarı oranı, ortalama getiri, örneklem ve kapanış nedeni birlikte anlamlıdır.",
    notes: ["Geçmiş performans gelecekte aynı sonucu garanti etmez.", "Küçük örneklem uyarısını gördüğünüzde yüzdeleri daha temkinli yorumlayın."],
  },
  strategy: {
    title: "Strateji Lab nasıl kullanılır?",
    eyebrow: "STRATEJİ LAB REHBERİ",
    intro: "Backtest'i geçmişteki Daily Core karar davranışını incelemek için kullanın; bugünkü işlem sinyalinin yerine koymayın.",
    badge: "BACKTEST",
    cards: [
      { step: "1 · SEMBOL", title: "Varlık ve dönemi seçin", body: "3Y / 5Y / 10Y dönemlerinde yeterli veri kapsamı olup olmadığını kontrol edin." },
      { step: "2 · KPI", title: "Özet metrikleri okuyun", body: "Getiri, başarı ve karar dağılımını tek başına değil birlikte değerlendirin." },
      { step: "3 · KARAR", title: "Geçmiş kararları açın", body: "Karar etiketleri nasıl yorumlanır? Ayrıntılı geçmiş tablo ile hangi koşullarda hangi etiketin oluştuğunu görün." },
      { step: "4 · SINIR", title: "Backtest sınırını unutmayın", body: "Geçmiş veri, işlem maliyeti ve piyasa rejimi gelecekte farklı davranabilir." },
    ],
    rule: "Backtest sonuçları geçmiş veri üzerindeki model davranışını gösterir; canlı getiri vaadi değildir.",
    notes: ["Sonuçları dönemler arasında karşılaştırın.", "IZFIN algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi veya getiri garantisi değildir."],
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
