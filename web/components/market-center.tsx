"use client";

import { useEffect, useState } from "react";
import {
  fetchMarketCenter,
  fetchMarketStockDetail,
  type MarketCenterResponse,
  type StockDetailResponse,
} from "../lib/market-center";
import { stockDetailHref } from "../lib/stock-detail-route";
import { useIzfinAuth } from "./auth-provider";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function tickerOf(item: Record<string, unknown> | undefined): string {
  return text(item?.ticker, "");
}

export function MarketCenterPanel({ jobId }: Readonly<{ jobId: string }>) {
  const { user, getIdToken } = useIzfinAuth();
  const [center, setCenter] = useState<MarketCenterResponse | null>(null);
  const [selectedTicker, setSelectedTicker] = useState("");
  const [detail, setDetail] = useState<StockDetailResponse | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    if (!user || !jobId) return;
    let active = true;
    setCenter(null);
    setDetail(null);
    setError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchMarketCenter(jobId, token);
        if (!active) return;
        setCenter(result);
        setSelectedTicker(result.best_ticker || tickerOf(result.top_signals[0]));
      } catch {
        if (active) setError("Piyasa Merkezi bu tarama için yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, jobId, user]);

  useEffect(() => {
    if (!user || !jobId || !selectedTicker) { setDetail(null); return; }
    let active = true;
    setDetail(null);
    setDetailError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchMarketStockDetail(jobId, selectedTicker, token);
        if (active) setDetail(result);
      } catch {
        if (active) setDetailError("Hisse detayı yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, jobId, selectedTicker, user]);

  if (!user) return null;

  return <section className="market-center-panel" aria-label="Piyasa Merkezi">
    <div className="section-heading market-center-heading">
      <div><p className="eyebrow">PİYASA MERKEZİ</p><h2>Tarama karar özeti</h2></div>
      <span className="section-index">03</span>
    </div>
    {!center && !error && <p className="market-center-state">Tarama özeti hazırlanıyor…</p>}
    {error && <p role="alert">{error}</p>}
    {center?.empty && <p className="market-center-state">Bu taramada Piyasa Merkezi için gösterilecek sonuç bulunamadı.</p>}
    {center && !center.empty && <>
      <div className="scan-metrics market-metrics">
        <span><b>{text(center.metrics.pulse)}</b> pulse</span>
        <span><b>{text(center.metrics.trend)}</b> trend</span>
        <span><b>{text(center.metrics.momentum)}</b> momentum</span>
        <span><b>{text(center.metrics.risk)}</b> risk</span>
      </div>
      <div className="market-mode"><span>Piyasa modu</span><strong>{text(center.decision.mod)}</strong><p>{text(center.decision.yorum)}</p></div>
      <div className="market-columns">
        <div className="market-signals">
          <div className="subsection-title"><span>ÖNE ÇIKAN SİNYALLER</span><b>{center.top_signals.length}</b></div>
          <div className="result-list">
            {center.top_signals.slice(0, 7).map((item, index) => {
              const ticker = tickerOf(item);
              if (!ticker) return <div key={`missing-${index}`}><strong>Sembol</strong><span>{text(item.sinyal)}</span></div>;
              return <a href={stockDetailHref(jobId, ticker)} key={`${ticker}-${index}`}>
                <strong>{ticker}</strong>
                <span>{text(item.sinyal)} · skor {text(item.skor)} · güven {text(item.guven)}</span>
              </a>;
            })}
          </div>
        </div>
        <div className="market-focus-card">
          <div className="subsection-title"><span>ÖNE ÇIKAN HİSSE</span><b>LIVE</b></div>
          {selectedTicker ? <>
            <h3>{selectedTicker}</h3>
            {!detail && !detailError && <p>Detay yükleniyor…</p>}
            {detailError && <p role="alert">{detailError}</p>}
            {detail && <>
              <div className="focus-kv"><span>Fiyat<b>{text(detail.price)}</b></span><span>Sinyal<b>{text(detail.signal)}</b></span><span>Skor<b>{text(detail.score.nihai)}</b></span><span>Giriş<b>{text(detail.entry_quality)}</b></span></div>
              <a className="detail-open" href={stockDetailHref(jobId, selectedTicker)}>Detaylı analizi aç →</a>
            </>}
          </> : <p>Öne çıkan hisse bulunamadı.</p>}
        </div>
      </div>
      {center.movers.length > 0 && <p className="market-movers">Hareketliler · {center.movers.slice(0, 6).map((item) => tickerOf(item)).filter(Boolean).join("  ·  ")}</p>}
    </>}
  </section>;
}
