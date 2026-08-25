import { AuthPanel } from "../components/auth-panel";
import { AccountCenter } from "../components/account-center";
import { Dashboard } from "../components/dashboard";
import { ScanWorkspace } from "../components/scan-workspace";
import { webTransitionSummary } from "../lib/transition-status";

const apiBaseUrl = process.env.NEXT_PUBLIC_IZFIN_API_URL ?? "https://izfin-api-469145462773.europe-west1.run.app";

export default function Home() {
  return (
    <main id="top" className="command-page">
      <section className="command-hero">
        <div className="hero-copy">
          <div className="hero-kicker"><span className="kicker-dot" /> CANLI PİYASA ÇALIŞMA ALANI</div>
          <h1><span>IZFIN</span>Piyasa Merkezi</h1>
          <p className="intro">
            Tarama, piyasa modu ve hisse kararlarını tek çalışma alanında birleştiren yeni web deneyimi.
            Streamlit çalışmaya devam ederken ekranları kontrollü biçimde buraya taşıyoruz.
          </p>
          <div className="actions">
            <a className="primary" href="#akilli-tarama">Taramaya git <span>→</span></a>
            <a className="secondary" href={`${apiBaseUrl}/api/v1/health`} target="_blank" rel="noreferrer">API durumunu aç</a>
          </div>
        </div>

        <aside className="hero-system" aria-label="Sistem durumu">
          <div className="system-card-head"><span>GEÇİŞ DURUMU</span><b>Stage 05</b></div>
          <div className="system-stat"><span>Web istemcisi</span><strong>Next.js</strong></div>
          <div className="system-stat"><span>Analiz katmanı</span><strong>FastAPI</strong></div>
          <div className="system-stat"><span>Mevcut uygulama</span><strong>Streamlit {webTransitionSummary.streamlitStatus.toLocaleLowerCase("tr-TR")}</strong></div>
          <div className="system-foot"><span className="live-dot" /> API canlı · kademeli geçiş güvenli</div>
        </aside>
      </section>

      <section className="workspace-grid" aria-label="Hesap ve kişisel alan">
        <div className="auth-card">
          <div className="section-heading"><div><p className="eyebrow">GÜVENLİ OTURUM</p><h2>IZFIN hesabın</h2></div><span className="section-index">01</span></div>
          <AuthPanel />
        </div>
        <Dashboard />
      </section>

      <div id="akilli-tarama" className="anchor-target"><ScanWorkspace /></div>
      <div id="hesap" className="anchor-target"><AccountCenter /></div>

      <section className="roadmap" aria-label="Geçiş sırası">
        <article className="roadmap-current">
          <span>WEB</span>
          <div><h2>Web çalışma alanı</h2><p>Piyasa Merkezi, tarama, projeksiyon, performans, takip, Strategy Lab ve hesap ekranları native web deneyiminde hazır.</p></div>
          <strong>{webTransitionSummary.completedSurfaceCount} EKRAN HAZIR</strong>
        </article>
        <article id="projeksiyon">
          <span>AKIŞ</span>
          <div><h2>Streamlit paralel</h2><p>Mevcut Streamlit uygulaması korunuyor; kullanıcılar iki arayüzü de güvenle kullanabiliyor.</p></div>
          <strong>AKTİF</strong>
        </article>
        <article id="performans">
          <span>SONRAKİ</span>
          <div><h2>{webTransitionSummary.nextMilestone}</h2><p>Web deneyimi olgunlaştıkça aynı API sözleşmeleriyle mobil istemci hazırlanacak.</p></div>
          <strong>PLANLI</strong>
        </article>
      </section>
    </main>
  );
}
