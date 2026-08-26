"use client";

import { useEffect, useMemo, useState } from "react";
import { IzfinApiError } from "../lib/api";
import { fetchAdminQuality, type AdminQualityResponse } from "../lib/admin-quality";
import { useIzfinAuth } from "./auth-provider";

function metricLabel(key: string): string {
  const labels: Record<string, string> = {
    python_satir: "Python satırı", css_satir: "CSS satırı", important: "!important", media_query: "Media query", hardcoded_hex: "Hardcoded HEX", design_token_kullanimi: "Design token kullanımı", gecersiz_design_token: "Geçersiz design token", "10px_alti_font": "10px altı font", inline_style: "Inline style", unsafe_html: "Unsafe HTML",
  };
  return labels[key] ?? key;
}

export function AdminQualityPage() {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [data, setData] = useState<AdminQualityResponse | null>(null);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchAdminQuality(token);
        if (active) setData(result);
      } catch (caught) {
        if (!active) return;
        if (caught instanceof IzfinApiError && caught.status === 403) {
          setForbidden(true); setError("Bu ekran yalnızca IZFIN yöneticilerine açıktır."); return;
        }
        setError("Kalite verileri şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, user]);

  const metricEntries = useMemo(() => Object.entries(data?.metrics ?? {}), [data]);

  if (loading) return <main className="admin-quality-page"><p className="admin-quality-muted">Güvenli oturum hazırlanıyor…</p></main>;
  if (!user) return <main className="admin-quality-page"><section className="admin-quality-panel"><p className="eyebrow">ADMIN QA</p><h1>Sistem Sağlığı</h1><p>Bu alanı görmek için yönetici hesabınla giriş yap.</p></section></main>;

  return <main className="admin-quality-page" aria-label="IZFIN admin kalite kontrol merkezi">
    <section className="admin-quality-hero">
      <div><p className="eyebrow">ADMIN QA · SİSTEM SAĞLIĞI</p><h1>Kalite Kontrol Merkezi</h1><p className="admin-quality-muted">Statik kalite metriklerini ve release durumunu tek ekranda izle.</p></div>
      {data && <div><span className={`admin-quality-status ${data.status.seviye}`}>{data.status.durum}</span><p className="admin-quality-muted">RELEASE · {data.app_release}</p></div>}
    </section>

    {error && <section className={`admin-quality-panel admin-quality-state${forbidden ? " forbidden" : ""}`} role="alert">{error}</section>}
    {!data && !error && <section className="admin-quality-panel admin-quality-state">Kalite metrikleri hazırlanıyor…</section>}

    {data && <>
      <section className="admin-quality-kpis">
        {metricEntries.map(([key, value]) => <article className="admin-quality-panel admin-quality-card" key={key}><span>{metricLabel(key)}</span><strong>{String(value)}</strong></article>)}
      </section>
      <section className="admin-quality-grid">
        <article className="admin-quality-panel admin-quality-notes"><p className="eyebrow">RELEASE DURUMU</p><h2>{data.status.durum}</h2><ul>{data.status.notlar.map((note) => <li key={note}>{note}</li>)}</ul></article>
        <article className="admin-quality-panel admin-quality-notes"><p className="eyebrow">YORUM</p><h2>Teknik borç görünümü</h2><p>Bu ekran mevcut framework-neutral kalite servisini kullanır. Buradaki uyarılar release engeli olmak zorunda değildir; ancak yeni refactor kararlarında önceliklendirme sinyali olarak değerlendirilmelidir.</p></article>
      </section>
    </>}
  </main>;
}
