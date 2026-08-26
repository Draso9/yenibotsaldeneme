"use client";

import { useEffect, useState } from "react";
import { fetchMarketStockDetail, type StockDetailResponse } from "../lib/market-center";
import { projectionHref } from "../lib/projection";
import { useIzfinAuth } from "./auth-provider";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Evet" : "Hayır";
  return String(value);
}

function scalarEntries(values: Record<string, unknown>, limit = 18): Array<[string, unknown]> {
  return Object.entries(values)
    .filter(([, value]) => value === null || ["string", "number", "boolean"].includes(typeof value))
    .slice(0, limit);
}

function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toLocaleUpperCase("tr-TR"));
}

export function StockDetailPage({ jobId, ticker }: Readonly<{ jobId: string; ticker: string }>) {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [detail, setDetail] = useState<StockDetailResponse | null>(null);
  const [error, setError] = useState("");
  const normalizedTicker = String(ticker || "").trim().toUpperCase();

  useEffect(() => {
    if (loading || !user || !jobId || !normalizedTicker) return;
    let active = true;
    setDetail(null);
    setError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchMarketStockDetail(jobId, normalizedTicker, token);
        if (active) setDetail(result);
      } catch {
        if (active) setError("Detaylı analiz bu tarama için yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, jobId, loading, normalizedTicker, user]);

  if (!jobId || !normalizedTicker) {
    return <section className="detail-page"><a className="detail-back" href="/">← Piyasa Merkezi</a><div className="detail-section"><h1>Detaylı Analiz</h1><p>Bu ekran bir tamamlanmış tarama ve sembol bilgisiyle açılmalıdır.</p></div></section>;
  }

  if (loading) {
    return <section className="detail-page"><a className="detail-back" href="/">← Piyasa Merkezi</a><p>Güvenli oturum hazırlanıyor…</p></section>;
  }

  if (!user) {
    return <section className="detail-page"><a className="detail-back" href="/">← Ana sayfa</a><div className="detail-section"><p className="eyebrow">DETAYLI ANALİZ</p><h1>{normalizedTicker}</h1><p>Bu taramaya ait analizi görmek için IZFIN hesabınla giriş yap.</p></div></section>;
  }

  return <section className="detail-page" aria-label={`${normalizedTicker} detaylı analiz`}>
    <div className="detail-path"><a className="detail-back" href="/">← Piyasa Merkezi</a><span>Tarama sonucu / {normalizedTicker}</span></div>
    <div className="detail-section detail-hero">
      <p className="eyebrow">DETAYLI ANALİZ • JOB TABANLI</p>
      <h1>{normalizedTicker}</h1>
      {!detail && !error && <p className="detail-status" aria-live="polite">Analiz yükleniyor…</p>}
      {error && <p className="detail-status" role="alert">{error}</p>}
      {detail && <>
        <div className="detail-summary">
          <span><b>{text(detail.price)}</b> fiyat</span>
          <span><b>{text(detail.signal)}</b> nihai sinyal</span>
          <span><b>{text(detail.score.nihai)}</b> skor</span>
          <span><b>{text(detail.entry_quality)}</b> giriş kalitesi</span>
        </div>
        <a className="projection-cta" href={projectionHref(jobId, normalizedTicker)}>45G projeksiyon senaryosunu aç →</a>
        <p className="detail-note"><b>Veri kaynağı</b> · Bu görünüm yalnızca senin tamamlanmış taramana ait job verisinden üretiliyor.</p>
      </>}
    </div>

    {detail && <div className="detail-grid">
      <ScoreBreakdown score={detail.score} />
      <DecisionPanel decision={detail.decision} action={detail.action} />
      <DetailSection title="Teknik panel" values={detail.panel} wide />
    </div>}
  </section>;
}

function ScoreBreakdown({ score }: Readonly<{ score: Record<string, unknown> }>) {
  const groups: Array<[string, unknown]> = [["Eski sistem kalemleri", score.eski_kalemler], ["Bonuslar", score.bonus_kalemler], ["Cezalar", score.ceza_kalemler]];
  return <article className="detail-section"><p className="eyebrow">SKOR NASIL OLUŞTU?</p><div className="detail-score-metrics"><span><b>{text(score.eski)}</b>eski cezalı skor</span><span><b>+{text(score.bonus, "0")}</b>gelişmiş bonus</span><span><b>-{text(score.ceza, "0")}</b>gelişmiş ceza</span><span><b>{text(score.nihai)}</b>nihai skor</span></div>{groups.map(([title, value]) => <div className="detail-score-group" key={title}><strong>{title}</strong>{Array.isArray(value) && value.length ? <ul>{value.map((item, index) => <li key={index}>{text((item as Record<string, unknown>).metin)}</li>)}</ul> : <p>Ek kalem oluşmadı.</p>}</div>)}</article>;
}

function DecisionPanel({ decision, action }: Readonly<{ decision: Record<string, unknown>; action: Record<string, unknown> }>) {
  return <article className="detail-section detail-decision"><p className="eyebrow">ŞEFFAF KARAR MOTORU</p><h2>{text(decision.karar)}</h2><div className="detail-decision-kpis"><span><b>%{text(decision.guven)}</b>algoritma güveni</span><span><b>{text(decision.risk)}</b>risk</span><span><b>%{text(decision.mtf_uyum)}</b>MTF uyum</span></div><p><b>Olumlu teyitler:</b> {text(decision.olumlu_metin)}</p><p><b>Riskler:</b> {text(decision.risk_metin)}</p>{decision.mtf_metin ? <small>{text(decision.mtf_metin)}</small> : null}<div className="detail-action-note"><b>Giriş motoru:</b> {text(action.entry_quality)} · <b>Teknik profil:</b> {text(action.profile)}</div><small>Profil ve skorlar açıklayıcıdır; işlem aksiyonu merkezi nihai karar motorundan gelir.</small></article>;
}

function DetailSection({ title, values, wide = false }: Readonly<{ title: string; values: Record<string, unknown>; wide?: boolean }>) {
  const entries = scalarEntries(values, wide ? 28 : 16);
  return <article className={`detail-section${wide ? " detail-wide" : ""}`}>
    <p className="eyebrow">{title.toLocaleUpperCase("tr-TR")}</p>
    {entries.length === 0 ? <p>Gösterilecek veri bulunamadı.</p> : <div className="detail-kv">
      {entries.map(([key, value]) => <div key={key}><span>{label(key)}</span><strong>{text(value)}</strong></div>)}
    </div>}
  </article>;
}

