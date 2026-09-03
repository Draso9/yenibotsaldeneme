"use client";

import { SignalExplanation } from "./signal-explanation";
import { technicalProfile, confidenceScore, confidenceExplanation, trendExplanation } from "../lib/signal-labels";
import { useEffect } from "react";
import type { StockDetailResponse } from "../lib/market-center";
import { projectionHref } from "../lib/projection";
import { stockDetailHref } from "../lib/stock-detail-route";
import { useAnalysisContext } from "./analysis-context-provider";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

type ScanDecisionCardProps = Readonly<{
  jobId: string;
  detail: StockDetailResponse;
  tickers: string[];
  onTickerChange: (ticker: string) => void;
}>;

export function ScanDecisionCard({ jobId, detail, tickers, onTickerChange }: ScanDecisionCardProps) {
  const {
    selectedTicker: sharedSelectedTicker,
    lastVisitedAnalysisRoute,
    setLastVisitedAnalysisRoute,
  } = useAnalysisContext();
  const { decision, action, panel } = detail;
  const selectorTicker = sharedSelectedTicker && tickers.includes(sharedSelectedTicker)
    ? sharedSelectedTicker
    : detail.ticker;

  useEffect(() => {
    const returningFromDetail = lastVisitedAnalysisRoute.startsWith("/stocks/");
    if (returningFromDetail && sharedSelectedTicker && tickers.includes(sharedSelectedTicker)) {
      if (sharedSelectedTicker !== detail.ticker) {
        onTickerChange(sharedSelectedTicker);
        return;
      }
      setLastVisitedAnalysisRoute("");
    } else if (returningFromDetail) {
      setLastVisitedAnalysisRoute("");
    }
  }, [detail.ticker, lastVisitedAnalysisRoute, onTickerChange, setLastVisitedAnalysisRoute, sharedSelectedTicker, tickers]);

  return <section className="scan-decision-card" aria-label={`${detail.ticker} hisse karar motoru`}>
    <div className="scan-decision-selector">
      <label htmlFor="scan-decision-ticker"><span>Karar motorunda gösterilen hisse</span><b>{tickers.length} tarama sonucu arasından seç</b></label>
      <select id="scan-decision-ticker" value={selectorTicker} onChange={(event) => onTickerChange(event.target.value)}>
        {tickers.map((symbol) => <option key={symbol} value={symbol}>{symbol}</option>)}
      </select>
    </div>

    <div className="scan-decision-primary">
      <div className="scan-decision-hero">
        <div className="scan-decision-identity">
          <p className="eyebrow">HİSSEYE ÖZEL KARAR MOTORU</p>
          <h3>{detail.ticker}</h3>
          <span>Fiyat <b>{text(detail.price)}</b> · IZFIN Skor <b>{text(detail.score.nihai)}</b></span>
        </div>
        <div className="scan-decision-verdict">
          <small>MERKEZİ KARAR</small>
          <strong>{text(decision.karar, text(detail.signal))}</strong>
          <span>Skorlar kararı açıklar; işlem yönünün merkezi kaynağı bu karardır.</span>
        </div>
      </div>
      <div className="scan-decision-reasons">
        <article className="is-positive"><small>01 · Olumlu teyitler</small><h4>Neden alınabilir?</h4><p>{text(decision.olumlu_metin, "Olumlu teknik teyit oluşmadı.")}</p></article>
        <article className="is-risk"><small>02 · Riskler ve bekleme nedenleri</small><h4>Neden beklenmeli / alınmamalı?</h4><p>{text(decision.risk_metin, "Belirgin ek risk gerekçesi oluşmadı.")}</p></article>
      </div>
      <div className="scan-decision-stop"><small>STOP / ZARAR KES</small><strong>{text(panel.stop)}</strong><span>İlk bakışta karar ile birlikte görünen temel risk sınırı.</span></div>
    </div>

    <details className="scan-decision-details">
      <summary>Güven, zamanlama ve teknik seviyeler</summary>
      <div className="scan-decision-secondary">
        <div className="scan-decision-kpis">
          <span title={confidenceExplanation}><small>Algoritma güven puanı</small><b>{confidenceScore(decision.guven)}</b></span>
          <span><small>Giriş kalitesi</small><b>{text(action.entry_quality, text(detail.entry_quality))}</b></span>
          <span><small>MTF uyumu</small><b>%{text(decision.mtf_uyum)}</b></span>
          <span><small>Risk</small><b>{text(decision.risk)}</b></span>
          <span><small>Teknik profil</small><b>{technicalProfile(action.profile)}</b></span>
        </div>
        <p className="scan-decision-note">{trendExplanation} {confidenceExplanation}</p>
        <SignalExplanation value={decision.teyitler} />
        {decision.mtf_metin ? <div className="scan-decision-note"><small>ZAMAN DİLİMLERİ</small><p>{text(decision.mtf_metin)}</p></div> : null}
        <div className="scan-decision-level-heading"><span>İşlem planı seviyeleri</span><small>Destek · direnç · hedefler</small></div>
        <div className="scan-decision-levels">{([
          ["Destek", panel.destek],
          ["Direnç", panel.direnc],
          ["TP1", panel.tp1],
          ["TP2", panel.tp2],
          ["TP3", panel.tp3],
        ] as Array<[string, unknown]>).map(([label, value]) => <span key={label}><small>{label}</small><b>{text(value)}</b></span>)}</div>
      </div>
    </details>

    <div className="scan-decision-actions">
      <a href={stockDetailHref(jobId, detail.ticker)}>Detaylı analizi aç →</a>
      <a href={projectionHref(jobId, detail.ticker)}>45G projeksiyonu aç →</a>
    </div>
  </section>;
}