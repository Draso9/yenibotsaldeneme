const apiBaseUrl = process.env.NEXT_PUBLIC_IZFIN_API_URL ?? "https://izfin-api-469145462773.europe-west1.run.app";

export default function Home() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">IZFIN WEB • BETA</p>
        <h1>BIST kararlarını daha net gör.</h1>
        <p className="intro">
          Yeni web arayüzü hazırlanıyor. Mevcut Streamlit uygulaması çalışmaya devam ederken,
          ekranları güvenli biçimde burada aşamalı olarak taşıyacağız.
        </p>
        <div className="actions">
          <a className="primary" href={`${apiBaseUrl}/api/v1/health`} target="_blank" rel="noreferrer">
            API durumunu kontrol et
          </a>
          <span className="status"><i /> API canlı</span>
        </div>
      </section>

      <section className="roadmap" aria-label="Geçiş durumu">
        <article>
          <span>01</span>
          <h2>Güvenli altyapı</h2>
          <p>FastAPI, Firebase ve Cloud Run hazır.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Web deneyimi</h2>
          <p>Giriş, watchlist ve dashboard ekranları sırada.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Mobil uyum</h2>
          <p>Aynı API, sonraki mobil istemciyi de besleyecek.</p>
        </article>
      </section>
    </main>
  );
}
