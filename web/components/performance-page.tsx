"use client";

import { useEffect, useState } from "react";
import { fetchPerformanceScorecard, type PerformanceScorecardResponse } from "../lib/performance";
import { useIzfinAuth } from "./auth-provider";

const PERIODS = [20, 60, 120] as const;

export function PerformancePage() {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(20);
  const [scorecard, setScorecard] = useState<PerformanceScorecardResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    setScorecard(null);
    setError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchPerformanceScorecard(token, days);
        if (active) setScorecard(result);
      } catch {
        if (active) setError("Performans karnesi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [days, getIdToken, loading, user]);

  if (loading) return <main className="performance-page"><p className="performance-muted">Oturum hazırlanıyor…</p></main>;
  if (!user) return <main className="performance-page"><section className="performance-panel performance-empty"><p className="eyebrow">SİNYAL PERFORMANSI</p><h1>Performans Karnesi</h1><p>Bu ekranı görmek için IZFIN hesabınla giriş yap.</p><a href="/">Ana sayfaya dön →</a></section></main>;

  return <main className="performance-page" aria-label="IZFIN performans karnesi">
    <section className="performance-hero">
      <div><p className="eyebrow">SİNYAL PERFORMANSI</p><h1>Performans Karnesi</h1><p className="performance-muted">Geçmiş IZFIN sinyallerini seçilen ölçüm penceresinde toplu olarak değerlendir.</p></div>
      <div className="performance-period">{PERIODS.map((period) => <button className={days === period ? "active" : ""} key={period} onClick={() => setDays(period)}>{period}G</button>)}</div>
    </section>

    {!scorecard && !error && <section className="performance-panel performance-state">Karne hazırlanıyor…</section>}
    {error && <section className="performance-panel performance-state" role="alert">{error}</section>}

    {scorecard && <>
      <section className="performance-overview-grid">
        <article className="performance-panel performance-summary-card"><span>KAYIT HAVUZU</span><strong>{scorecard.kayit_adedi}</strong><small>{days} günlük pencere</small></article>
        <article className={`performance-panel performance-summary-card${scorecard.kucuk_orneklem ? " is-warning" : ""}`}><span>ÖRNEKLEM</span><strong>{scorecard.kucuk_orneklem ? "SINIRLI" : "YETERLİ"}</strong><small>{scorecard.kucuk_orneklem ? "Temkinli yorumla" : "Karne değerlendirmeye uygun"}</small></article>
        <article className="performance-panel performance-summary-card"><span>DÖNEM</span><strong>{days}G</strong><small>Performans ölçümü</small></article>
      </section>

      {scorecard.bos_mesaj ? <section className="performance-panel performance-empty-state"><p>{scorecard.bos_mesaj}</p><a href="/#akilli-tarama">Yeni tarama başlat →</a></section> : <section className="performance-metric-grid">
        {scorecard.metrikler.map((metric, index) => <article className="performance-panel performance-metric-card" key={`${metric.label}-${index}`}><span>{metric.label}</span><strong>{metric.value}</strong><i /></article>)}
      </section>}

      <section className="performance-lower-grid">
        <article className="performance-panel performance-context-card"><p className="eyebrow">KARNE OKUMASI</p><h2>Sonuç kalitesi</h2><p>{scorecard.kucuk_orneklem ? "Örneklem henüz küçük; oranlar yeni sonuçlarla hızlı değişebilir." : "Örneklem daha dengeli bir toplu değerlendirme sunuyor."}</p><div className="performance-quality-bar"><span style={{ width: `${Math.min(100, Math.max(8, scorecard.kayit_adedi))}%` }} /></div></article>
        <article className="performance-panel performance-context-card"><p className="eyebrow">ÖLÇÜM BAĞLAMI</p><h2>Mevcut performans motoru</h2><p>Bu ekran mevcut IZFIN performans hesaplamasını native web arayüzünde gösterir. Streamlit akışı geçiş boyunca korunur.</p></article>
      </section>
    </>}
  </main>;
}
