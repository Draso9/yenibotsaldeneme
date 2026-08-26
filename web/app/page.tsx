import { AuthPanel } from "../components/auth-panel";
import { AccountCenter } from "../components/account-center";
import { Dashboard } from "../components/dashboard";
import { MarketStrip } from "../components/market-strip";
import { ScanWorkspace } from "../components/scan-workspace";

export default function Home() {
  return (
    <main id="top" className="command-page">
      <MarketStrip />
      <section className="command-hero">
        <div className="hero-copy">
          <div className="hero-kicker"><span className="kicker-dot" /> CANLI PİYASA ÇALIŞMA ALANI</div>
          <h1><span>IZFIN</span>Piyasa Merkezi</h1>
          <p className="intro">
            Akıllı tarama, piyasa modu, detaylı analiz ve karar destek katmanlarını tek komuta merkezinde birleştir.
            Sinyalleri izle, fırsatları karşılaştır ve aynı taramadan projeksiyon ile performans ekranlarına ilerle.
          </p>
          <div className="actions">
            <a className="primary" href="#akilli-tarama">Taramayı başlat <span>→</span></a>
          </div>
        </div>
        <aside className="hero-system" aria-label="IZFIN platform özeti">
          <div className="system-card-head"><span>IZFIN PLATFORM</span><b>WEB</b></div>
          <div className="system-stat"><span>Tarama motoru</span><strong>Job tabanlı</strong></div>
          <div className="system-stat"><span>Analiz akışı</span><strong>Gerçek zamanlı</strong></div>
          <div className="system-stat"><span>Hesap güvenliği</span><strong>Firebase Auth</strong></div>
          <div className="system-foot"><span className="live-dot" /> API canlı · güvenli çalışma alanı</div>
        </aside>
      </section>
      <section className="workspace-grid" aria-label="Hesap ve kişisel alan">
        <div className="auth-card"><div className="section-heading"><div><p className="eyebrow">GÜVENLİ OTURUM</p><h2>IZFIN hesabın</h2></div><span className="section-index">01</span></div><AuthPanel /></div>
        <Dashboard />
      </section>
      <div id="akilli-tarama" className="anchor-target"><ScanWorkspace /></div>
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
