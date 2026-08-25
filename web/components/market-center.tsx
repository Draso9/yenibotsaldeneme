"use client";

import { useEffect, useState } from "react";
import {
  fetchMarketCenter,
  fetchMarketStockDetail,
  type MarketCenterResponse,
  type StockDetailResponse,
} from "../lib/market-center";
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

  return <section className="scan-result" aria-label="Piyasa Merkezi">
    <p className="eyebrow">PİYASA MERKEZİ</p>
    {!center && !error && <p>Tarama özeti hazırlanıyor…</p>}
    {error && <p role="alert">{error}</p>}
    {center?.empty && <p>Bu taramada Piyasa Merkezi için gösterilecek sonuç bulunamadı.</p>}
    {center && !center.empty && <>
      <div className="scan-metrics">
        <span><b>{text(center.metrics.pulse)}</b> pulse</span>
        <span><b>{text(center.metrics.trend)}</b> trend</span>
        <span><b>{text(center.metrics.momentum)}</b> momentum</span>
        <span><b>{text(center.metrics.risk)}</b> risk</span>
      </div>
      <p className="job-progress">Piyasa modu: <strong>{text(center.decision.mod)}</strong> · {text(center.decision.yorum)}</p>
      <div className="result-list">
        {center.top_signals.slice(0, 7).map((item, index) => {
          const ticker = tickerOf(item);
          return <div key={`${ticker}-${index}`}>
            <strong>{ticker || "Sembol"}</strong>
            <span>{text(item.sinyal)} · skor {text(item.skor)} · güven {text(item.guven)}</span>
          </div>;
        })}
      </div>
      {center.movers.length > 0 && <p className="job-progress">Hareketliler: {center.movers.slice(0, 6).map((item) => tickerOf(item)).filter(Boolean).join(", ")}</p>}
      {selectedTicker && <div className="scan-result">
        <p className="eyebrow">ÖNE ÇIKAN HİSSE · {selectedTicker}</p>
        {!detail && !detailError && <p>Detay yükleniyor…</p>}
        {detailError && <p role="alert">{detailError}</p>}
        {detail && <div className="scan-metrics">
          <span><b>{text(detail.price)}</b> fiyat</span>
          <span><b>{text(detail.signal)}</b> sinyal</span>
          <span><b>{text(detail.score.nihai)}</b> skor</span>
          <span><b>{text(detail.entry_quality)}</b> giriş kalitesi</span>
        </div>}
      </div>}
    </>}
  </section>;
}
