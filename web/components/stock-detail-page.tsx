"use client";

import { technicalProfile, trendExplanation } from "../lib/signal-labels";
import { useEffect, useState } from "react";
import { fetchMarketStockDetail, type StockDetailResponse } from "../lib/market-center";
import { projectionHref } from "../lib/projection";
import { useAnalysisContext } from "./analysis-context-provider";
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

function scoreItems(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function scoreInterpretation(value: unknown): { label: string; tone: string; meaning: string } {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return { label: "Değerlendiriliyor", tone: "neutral", meaning: "Skor etiketi için yeterli sayısal veri bulunmuyor." };
  if (parsed < 50) return { label: "Cezalı", tone: "penalized", meaning: "Olumsuz teknik kalemler ve cezalar nihai skoru baskılıyor; olumlu bileşenler güçlü banda taşımaya yetmiyor." };
  if (parsed < 70) return { label: "Nötr", tone: "neutral", meaning: "Olumlu ve olumsuz teknik etkiler birlikte bulunuyor; skor tek başına belirgin bir yön üstünlüğü göstermiyor." };
  return { label: "Güçlü", tone: "strong", meaning: "Birden fazla teknik bileşen nihai skoru destekliyor; yine de risk ve merkezi karar işlem yönünü sınırlayabilir." };
}

export function StockDetailPage({ jobId, ticker }: Readonly<{ jobId: string; ticker: string }>) {
  const { loading, user, getIdToken } = useIzfinAuth();
  const { setActiveScan, setSelectedTicker, setLastVisitedAnalysisRoute } = useAnalysisContext();
  const [detail, setDetail] = useState<StockDetailResponse | null>(null);
  const [error, setError] = useState("");
  const normalizedTicker = String(ticker || "").trim().toUpperCase();

  useEffect(() => {
    if (loading || !user || !jobId || !normalizedTicker) return;
    setActiveScan(jobId);
    setSelectedTicker(normalizedTicker);
    setLastVisitedAnalysisRoute(`/stocks/${normalizedTicker}`);
  }, [jobId, loading, normalizedTicker, setActiveScan, setLastVisitedAnalysisRoute, setSelectedTicker, user]);

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
    return <section className="detail-page"><a className="detail-back" href="/scan#scan-result">← Akıllı Tarama sonuçlarına dön</a><div className="detail-section"><h1>Detaylı Analiz</h1><p>Bu ekran bir tamamlanmış tarama ve sembol bilgisiyle açılmalıdır.</p></div></section>;
  }

  if (loading) {
    return <section className="detail-page"><a className="detail-back" href="/scan#scan-result">← Akıllı Tarama sonuçlarına dön</a><p>Güvenli oturum hazırlanıyor…</p></section>;
  }

  if (!user) {
    return <section className="detail-page"><a className="detail-back" href="/scan#scan-result">← Akıllı Tarama sonuçlarına dön</a><div className="detail-section"><p className="eyebrow">DETAYLI ANALİZ</p><h1>{normalizedTicker}</h1><p>Bu taramaya ait analizi görmek için IZFIN hesabınla giriş yap.</p></div></section>;
  }

  return <section className="detail-page" aria-label={`${normalizedTicker} detaylı analiz`}>
    <div className="detail-path"><a className="detail-back" href="/scan#scan-result">← Akıllı Tarama sonuçlarına dön</a><span>Akıllı Tarama → Detaylı Analiz → {normalizedTicker}</span></div>
    <div className="detail-section detail-hero">
      <p className="eyebrow">DETAYLI ANALİZ</p>
      <h1>{normalizedTicker}</h1>
      {!detail && !error && <p className="detail-status" aria-live="polite">Analiz yükleniyor…</p>}
      {error && <p className="detail-status" role="alert">{error}</p>}
      {detail && <>
        <div className="detail-summary">
          <span><b>{text(detail.price)}</b> fiyat</span>
          <span><b>{text(detail.score.nihai)}</b> Gelişmiş Skor</span>
        </div>
        <p className="detail-note"><b>Teknik profil:</b> {technicalProfile(detail.action.profile)} · <b>Merkezi karar:</b> {text(detail.decision.karar)}</p>
        <p className="detail-note">{trendExplanation} Kararın teyit koşullarını Akıllı Tarama karar kartında inceleyebilirsin.</p>
        <a className="projection-cta" href={projectionHref(jobId, normalizedTicker)}>45G projeksiyon senaryosunu aç →</a>
        <p className="detail-note"><b>Odak</b> · Bu ekran Karar Motoru’nu tekrar etmez; skorun nedenlerini ve teknik planı gerektiğinde açılan ayrıntılarla gösterir.</p>
      </>}
    </div>

    {detail && <div className="detail-grid">
      <ScoreBreakdown score={detail.score} />
      <TechnicalOverview technical={detail.technical} fallback={detail.panel} />
    </div>}
  </section>;
}

function ScoreBreakdown({ score }: Readonly<{ score: Record<string, unknown> }>) {
  const scoreValue = text(score.nihai);
  const interpretation = scoreInterpretation(score.nihai);
  const positiveItems = scoreItems(score.bonus_kalemler);
  const penaltyItems = scoreItems(score.ceza_kalemler);
  const baseItems = scoreItems(score.eski_kalemler);

  return <details className="detail-section detail-score-breakdown">
    <summary>
      <span><small>GELİŞMİŞ SKOR</small><b>{scoreValue}/100 · {interpretation.label}</b><i className={`score-band is-${interpretation.tone}`}>{interpretation.label}</i></span>
      <em>Bu skor neden {scoreValue}?</em>
    </summary>
    <div className="detail-score-explanation">
      <h3>Gelişmiş Skor ne anlatıyor?</h3>
      <p><b>{scoreValue}/100 · {interpretation.label}</b> — {interpretation.meaning}</p>
      <small>Bu skor otomatik AL değildir ve başarı olasılığı anlamına gelmez. Risk, giriş koşulları ve Akıllı Tarama’daki merkezi Karar Motoru güçlü bir skoru dahi sınırlayabilir.</small>
    </div>
    <div className="detail-score-metrics">
      <span><b>{text(score.eski)}</b>eski / temel teknik skor</span>
      <span><b>+{text(score.bonus, "0")}</b>gelişmiş bonus</span>
      <span><b>-{text(score.ceza, "0")}</b>gelişmiş ceza</span>
      <span><b>{scoreValue}</b>nihai Gelişmiş Skor</span>
    </div>
    <div className="detail-score-drivers">
      <section className="detail-score-driver is-positive">
        <strong>Skoru yukarı çekenler</strong>
        {positiveItems.length ? <ul>{positiveItems.map((item, index) => <li key={index}>{text(item.metin)}</li>)}</ul> : <p>Bu taramada belirgin ek bonus oluşmadı.</p>}
      </section>
      <section className="detail-score-driver is-negative">
        <strong>Skoru aşağı çekenler</strong>
        {penaltyItems.length ? <ul>{penaltyItems.map((item, index) => <li key={index}>{text(item.metin)}</li>)}</ul> : <p>Bu taramada belirgin ek ceza oluşmadı.</p>}
      </section>
    </div>
    <div className="detail-score-group">
      <strong>Skorun temel teknik kalemleri</strong>
      {baseItems.length ? <ul>{baseItems.map((item, index) => <li key={index}>{text(item.metin)}</li>)}</ul> : <p>Ek temel skor kalemi oluşmadı.</p>}
    </div>
    <div className="detail-score-reading"><b>{interpretation.label} ne demek?</b><p>{interpretation.meaning} İşlem yönünün merkezi kaynağı Akıllı Tarama’daki Hisseye Özel Karar Motoru olarak kalır.</p></div>
  </details>;
}

function technicalItems(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : [];
}

function technicalTone(value: unknown): string {
  const tone = String(value ?? "neutral");
  return ["positive", "negative", "warning"].includes(tone) ? tone : "neutral";
}

function TechnicalOverview({ technical, fallback }: Readonly<{ technical?: import("../lib/market-center").StructuredTechnicalAnalysis; fallback: Record<string, unknown> }>) {
  const metrics = technicalItems(technical?.metrics);
  const trend = technicalItems(technical?.trend);
  const levels = technicalItems(technical?.levels);
  const targets = technicalItems(technical?.targets);
  const entry = technical?.entry ?? {};
  const entryDetails = Array.isArray(entry.details) ? entry.details : [];
  if (!technical || metrics.length === 0) return <DetailSection title="Teknik panel" values={fallback} wide />;

  return <article className="detail-section detail-wide detail-technical">
    <div className="detail-technical-heading"><div><p className="eyebrow">TEKNİK ANALİZ HARİTASI</p><h2>Teknik özet</h2></div><span>Veri kaynağı · {text(technical.source)}</span></div>
    <div className="detail-technical-summary">{metrics.slice(0, 4).map((item, index) => <div className={`is-${technicalTone(item.tone)}`} key={`${text(item.label)}-${index}`}><small>{text(item.label)}</small><strong>{text(item.value)}</strong><span>{text(item.note)}</span></div>)}</div>

    <details className="detail-technical-disclosure"><summary>Göstergeler</summary><div className="detail-technical-metrics">{metrics.map((item, index) => <div className={`is-${technicalTone(item.tone)}`} key={`${text(item.label)}-${index}`}><small>{text(item.label)}</small><strong>{text(item.value)}</strong><span>{text(item.note)}</span></div>)}</div></details>

    <details className="detail-technical-disclosure"><summary>Trend ve momentum özeti</summary><div className="detail-technical-rows">{trend.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><b className={`is-${technicalTone(item.tone)}`}>{text(item.value)}</b></div>)}</div></details>

    <details className="detail-technical-disclosure"><summary>Destek, direnç ve giriş planı</summary><div className="detail-technical-sections"><section><h3>Destek ve direnç bölgeleri</h3><div className="detail-technical-rows">{levels.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><b className={`is-${technicalTone(item.tone)}`}>{text(item.value)}</b></div>)}</div></section><section><h3>Çok zaman dilimli giriş motoru</h3><div className="detail-entry-score"><strong>{text(entry.score, "0")}/100</strong><span>{text(entry.level)}</span></div>{entryDetails.length ? <ul>{entryDetails.map((item, index) => <li key={index}>{text(item)}</li>)}</ul> : <p>Henüz yeterli çok zaman dilimli giriş teyidi bulunmuyor.</p>}</section></div></details>

    <details className="detail-technical-disclosure"><summary>Teknik hedefler ve algoritmik yorum</summary><section className="detail-target-section"><h3>Teknik kâr hedefleri</h3><div className="detail-targets">{targets.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><strong>{text(item.value)}</strong><small>{"★".repeat(Math.max(1, Math.min(5, Number(item.confidence) || 1)))}</small></div>)}</div></section><div className="detail-algorithm-comment"><b>Algoritmik yorum</b><p>{text(technical.algorithmic_comment)}</p></div></details>
  </article>;
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
