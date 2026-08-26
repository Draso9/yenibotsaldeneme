import { AuthPanel } from "../components/auth-panel";
import { AccountCenter } from "../components/account-center";
import { Dashboard } from "../components/dashboard";
import { HomeDecisionCenter } from "../components/home-decision-center";
import { MarketStrip } from "../components/market-strip";

export default function Home() {
  return (
    <main id="top" className="command-page">
      <MarketStrip />
      <div className="home-scan-banner"><div><b>✦ Fırsatları tüm evrende tara</b><span>IZFIN merkezi karar motorunu seçtiğin piyasa grubunda çalıştır.</span></div><a className="primary" href="/scan">Akıllı Tarama Merkezine Git →</a></div>
      <HomeDecisionCenter />
      <section className="workspace-grid" aria-label="Hesap ve kişisel alan">
        <div className="auth-card"><div className="section-heading"><div><p className="eyebrow">GÜVENLİ OTURUM</p><h2>IZFIN hesabın</h2></div><span className="section-index">01</span></div><AuthPanel /></div>
        <Dashboard />
      </section>
      <div id="hesap" className="anchor-target"><AccountCenter /></div>
      <section className="roadmap" aria-label="IZFIN analiz araçları">
        <article className="roadmap-current"><span>01</span><div><h2>Piyasa Merkezi</h2><p>Tarama sonuçlarını, piyasa modunu, öne çıkan sinyalleri ve hareketleri tek görünümde takip et.</p></div><strong>MERKEZ</strong></article>
        <article><span>02</span><div><h2>Projeksiyon</h2><p>Seçili hissede 45 günlük ATR ve tarihsel volatilite bantlarını senaryo görünümünde incele.</p></div><a href="/projection">AÇ →</a></article>
        <article><span>03</span><div><h2>Performans</h2><p>Geçmiş sinyalleri, aktif pozisyonları ve kapanmış sonuçları performans karnesinde değerlendir.</p></div><a href="/performance">AÇ →</a></article>
        <article><span>04</span><div><h2>Strateji Laboratuvarı</h2><p>Daily Core stratejisini farklı dönemlerde backtest ederek karar motorunun geçmiş davranışını test et.</p></div><a href="/strategy-lab">AÇ →</a></article>
      </section>
    </main>
  );
}

