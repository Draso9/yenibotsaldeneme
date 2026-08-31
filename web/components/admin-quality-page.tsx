"use client";

import { useEffect, useState } from "react";
import { IzfinApiError } from "../lib/api";
import { fetchAdminQuality, type AdminQualityResponse } from "../lib/admin-quality";
import { readinessCards, readinessHeadline } from "../lib/admin-quality-presentation.mjs";
import { fetchSystemReadiness, type SystemReadinessResponse } from "../lib/system-health";
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
  const [readiness, setReadiness] = useState<SystemReadinessResponse | null>(null);
  const [error, setError] = useState("");
  const [readinessError, setReadinessError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    setData(null);
    setReadiness(null);
    setError("");
    setReadinessError("");
    setForbidden(false);
    if (loading || !user) return;
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const [qualityResult, readinessResult] = await Promise.allSettled([
          fetchAdminQuality(token),
          fetchSystemReadiness(),
        ]);
        if (!active) return;
        if (qualityResult.status === "fulfilled") {
          setData(qualityResult.value);
        } else if (qualityResult.reason instanceof IzfinApiError && qualityResult.reason.status === 403) {
          setForbidden(true); setError("Bu ekran yalnızca IZFIN yöneticilerine açıktır.");
        } else {
          setError("Kalite verileri şu anda yüklenemedi.");
        }
        if (readinessResult.status === "fulfilled") {
          setReadiness(readinessResult.value);
        } else {
          setReadinessError("Canlı servis durumu şu anda alınamadı.");
        }
      } catch {
        if (active) setError("Güvenli yönetici oturumu doğrulanamadı.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, user]);

  const metricEntries = Object.entries(data?.metrics ?? {});
  const readinessItems = readinessCards(readiness);

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
      <section className="admin-quality-panel admin-readiness">
        <div className="admin-quality-section-head"><div><p className="eyebrow">CANLI READINESS</p><h2>{readiness ? readinessHeadline(readiness) : "Çekirdek servisler kontrol ediliyor"}</h2></div>{readiness && <span className={`admin-quality-status ${readiness.ready ? "success" : "warning"}`}>{readiness.ready ? "HAZIR" : "KISITLI"}</span>}</div>
        {readinessError ? <p className="admin-quality-readiness-error">{readinessError}</p> : readinessItems.length === 0 ? <p className="admin-quality-muted">Canlı servis sınırları doğrulanıyor…</p> : <div className="admin-readiness-grid">{readinessItems.map((item) => <article className={item.ready ? "ready" : "degraded"} key={item.label}><span>{item.label}</span><strong>{item.ready ? "Hazır" : "Kısıtlı"}</strong></article>)}</div>}
      </section>
      <section className="admin-quality-kpis">
        {metricEntries.map(([key, value]) => <article className="admin-quality-panel admin-quality-card" key={key}><span>{metricLabel(key)}</span><strong>{String(value)}</strong></article>)}
      </section>
      <section className="admin-quality-grid">
        <article className="admin-quality-panel admin-quality-notes"><p className="eyebrow">RELEASE DURUMU</p><h2>{data.status.durum}</h2><ul>{data.status.notlar.map((note) => <li key={note}>{note}</li>)}</ul></article>
        <article className="admin-quality-panel admin-quality-notes"><p className="eyebrow">RELEASE & CI</p><h2>{data.app_release}</h2><p>Python ve web kalite kapılarının canlı sonucu için <a href="https://github.com/Draso9/yenibotsaldeneme/actions" rel="noreferrer" target="_blank">GitHub Actions</a> kaynak-of-truth olmaya devam eder. Bu ekran çalışma zamanı readiness verisini ve repodaki statik kalite göstergelerini ayrı gösterir.</p></article>
      </section>
    </>}
  </main>;
}
