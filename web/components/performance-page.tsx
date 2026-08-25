"use client";

import { useEffect, useState } from "react";
import {
  fetchPerformancePositions,
  fetchPerformanceScorecard,
  type PerformancePositionsResponse,
  type PerformanceScorecardResponse,
} from "../lib/performance";
import { useIzfinAuth } from "./auth-provider";

const PERIODS = [20, 60, 120] as const;

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function number(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function pctClass(value: unknown): string {
  const parsed = number(value);
  if (parsed === null || parsed === 0) return "neutral";
  return parsed > 0 ? "positive" : "negative";
}

function pct(value: unknown): string {
  const parsed = number(value);
  if (parsed === null) return "—";
  return `${parsed > 0 ? "+" : ""}${parsed.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}%`;
}

function price(value: unknown): string {
  const parsed = number(value);
  return parsed === null ? "—" : parsed.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function PerformancePage() {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(20);
  const [scorecard, setScorecard] = useState<PerformanceScorecardResponse | null>(null);
  const [tracking, setTracking] = useState<PerformancePositionsResponse | null>(null);
  const [scoreError, setScoreError] = useState("");
  const [trackingError, setTrackingError] = useState("");

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    setTracking(null);
    setTrackingError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchPerformancePositions(token);
        if (active) setTracking(result);
      } catch {
        if (active) setTrackingError("Pozisyon takibi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, user]);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    setScorecard(null);
    setScoreError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchPerformanceScorecard(token, days);
        if (active) setScorecard(result);
      } catch {
        if (active) setScoreError("Performans karnesi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [days, getIdToken, loading, user]);

  if (loading) return <main className="performance-page"><p className="performance-muted">Oturum hazırlanıyor…</p></main>;
  if (!user) return <main className="performance-page"><section className="performance-panel performance-empty"><p className="eyebrow">TAKİP & PERFORMANS</p><h1>Performans Merkezi</h1><p>Bu ekranı görmek için IZFIN hesabınla giriş yap.</p><a href="/">Ana sayfaya dön →</a></section></main>;

  const closedSummary = tracking?.closed_summary ?? {};

  return <main className="performance-page" aria-label="IZFIN takip ve performans merkezi">
    <section className="performance-hero">
      <div><p className="eyebrow">TAKİP & PERFORMANS</p><h1>Performans Merkezi</h1><p className="performance-muted">Aktif alım dönemlerini, kapanmış pozisyon geçmişini ve IZFIN sinyal karnesini tek ekranda izle.</p></div>
      <div className="performance-period" aria-label="Ölçüm dönemi">{PERIODS.map((period) => <button className={days === period ? "active" : ""} key={period} onClick={() => setDays(period)}>{period}G</button>)}</div>
    </section>

    {!tracking && !trackingError && <section className="performance-panel performance-state">Pozisyon takibi hazırlanıyor…</section>}
    {trackingError && <section className="performance-panel performance-state" role="alert">{trackingError}</section>}

    {tracking && <>
      <section className="performance-kpi-strip" aria-label="Pozisyon takip KPI'ları">
        {tracking.kpis.map((item) => <article className="performance-panel performance-track-kpi" key={item.label}><span>{item.label}</span><strong>{item.value}</strong></article>)}
      </section>

      <section className="performance-panel performance-table-card">
        <div className="performance-section-title"><div><p className="eyebrow">AKTİF ALIM POZİSYONLARI</p><h2>Devam eden sinyal dönemleri</h2></div><span>{tracking.active.length} aktif</span></div>
        {tracking.active.length === 0 ? <p className="performance-table-empty">Şu anda açık alım pozisyonu bulunmuyor.</p> : <div className="performance-table-scroll"><table className="performance-table">
          <thead><tr><th>Varlık</th><th>İlk sinyal</th><th>Güncel sinyal</th><th>İlk fiyat</th><th>Güncel fiyat</th><th>K/Z</th><th>Geçen gün</th></tr></thead>
          <tbody>{tracking.active.map((row, index) => <tr key={`${text(row["Varlık"])}-${index}`}>
            <td><b>{text(row["Varlık"])}</b></td><td>{text(row["İlk Sinyal"])}</td><td>{text(row["Güncel Sinyal"])}</td><td>{price(row["İlk Alım Fiyatı"])}</td><td>{price(row["Güncel Fiyat"])}</td><td className={pctClass(row["Kâr / Zarar %"])}>{pct(row["Kâr / Zarar %"])}</td><td>{text(row["Geçen Gün"])}</td>
          </tr>)}</tbody>
        </table></div>}
      </section>

      <section className="performance-closed-summary">
        <article className="performance-panel performance-closed-card"><span>KAPANMIŞ DÖNEM</span><strong>{text(closedSummary.adet, "0")}</strong><small>{text(closedSummary.unique_tickers, "0")} farklı hisse</small></article>
        <article className="performance-panel performance-closed-card"><span>POZİTİF KAPANIŞ</span><strong>{closedSummary.win_rate === null || closedSummary.win_rate === undefined ? "—" : pct(closedSummary.win_rate)}</strong><small>Win rate</small></article>
        <article className="performance-panel performance-closed-card"><span>ORT. GETİRİ</span><strong className={pctClass(closedSummary.avg_ret)}>{pct(closedSummary.avg_ret)}</strong><small>Kapalı dönem ortalaması</small></article>
        <article className="performance-panel performance-closed-card"><span>MEDYAN SÜRE</span><strong>{closedSummary.median_days === null || closedSummary.median_days === undefined ? "—" : `${text(closedSummary.median_days)} gün`}</strong><small>Taşıma süresi</small></article>
      </section>

      <section className="performance-panel performance-table-card">
        <div className="performance-section-title"><div><p className="eyebrow">KAPANMIŞ POZİSYON GEÇMİŞİ</p><h2>Gerçekleşmiş alım dönemleri</h2></div><span>{tracking.closed.length} kayıt</span></div>
        {tracking.closed.length === 0 ? <p className="performance-table-empty">Henüz kapanmış alım dönemi bulunmuyor.</p> : <div className="performance-table-scroll"><table className="performance-table performance-table-wide">
          <thead><tr><th>Varlık</th><th>Kapanış nedeni</th><th>İlk fiyat</th><th>Kapanış fiyatı</th><th>K/Z</th><th>Maks. kâr</th><th>Maks. düşüş</th><th>TP1</th><th>Stop</th></tr></thead>
          <tbody>{tracking.closed.map((row, index) => <tr key={`${text(row["Varlık"])}-${index}`}>
            <td><b>{text(row["Varlık"])}</b></td><td>{text(row["Kapanış Nedeni"])}</td><td>{price(row["İlk Alım Fiyatı"])}</td><td>{price(row["Kapanış Fiyatı"])}</td><td className={pctClass(row["Kâr / Zarar %"])}>{pct(row["Kâr / Zarar %"])}</td><td className={pctClass(row["Maks. Kâr %"])}>{pct(row["Maks. Kâr %"])}</td><td className={pctClass(row["Maks. Düşüş %"])}>{pct(row["Maks. Düşüş %"])}</td><td>{text(row.TP1)}</td><td>{text(row.Stop)}</td>
          </tr>)}</tbody>
        </table></div>}
      </section>

      {(Array.isArray(closedSummary.yorumlar) && closedSummary.yorumlar.length > 0) && <section className="performance-panel performance-insight-card"><p className="eyebrow">IZFIN GEÇMİŞ PERFORMANS ÖZETİ</p><div className="performance-insight-head"><h2>Sistem geçmişte ne yaptı?</h2><div><span><b>En iyi</b> {text(closedSummary.best_txt)}</span><span><b>En zayıf</b> {text(closedSummary.worst_txt)}</span></div></div><ul>{closedSummary.yorumlar.map((item, index) => <li key={index}>{text(item)}</li>)}</ul></section>}
    </>}

    {!scorecard && !scoreError && <section className="performance-panel performance-state">Karne hazırlanıyor…</section>}
    {scoreError && <section className="performance-panel performance-state" role="alert">{scoreError}</section>}

    {scorecard && <>
      <section className="performance-scorecard-heading"><div><p className="eyebrow">IZFIN PERFORMANS KARNESİ</p><h2>{days} günlük sinyal ölçümü</h2></div><span>{scorecard.kayit_adedi} kayıt</span></section>
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
        <article className="performance-panel performance-context-card"><p className="eyebrow">ÖLÇÜM BAĞLAMI</p><h2>Mevcut performans motoru</h2><p>Aktif/kapanmış dönem takibi ve sinyal karnesi mevcut IZFIN hesaplarını native web arayüzünde gösterir. Streamlit akışı geçiş boyunca korunur.</p></article>
      </section>
    </>}
  </main>;
}
