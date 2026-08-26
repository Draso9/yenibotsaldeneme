"use client";

import { useEffect, useMemo, useState } from "react";
import { izfinApiFetch } from "../lib/api";
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

function numeric(value: unknown): number { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : -Infinity; }
const DECISION_LABELS: Record<string, string> = { yon: "Yön", guven: "Güven", gerekce: "Gerekçe", risk: "Risk", tetikleyici: "Tetikleyici" };

export function MarketCenterPanel({ jobId }: Readonly<{ jobId: string }>) {
  const { user, getIdToken } = useIzfinAuth();
  const [center, setCenter] = useState<MarketCenterResponse | null>(null);
  const [selectedTicker, setSelectedTicker] = useState("");
  const [detail, setDetail] = useState<StockDetailResponse | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [sortBy, setSortBy] = useState<"score" | "risk">("score");
  const [watchlistMessage, setWatchlistMessage] = useState("");

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

  const sortedSignals = useMemo(() => [...(center?.top_signals ?? [])].sort((left, right) => sortBy === "score" ? numeric(right.skor) - numeric(left.skor) : numeric(left.risk) - numeric(right.risk)), [center, sortBy]);

  if (!user) return null;

  async function addSelectedToWatchlist() {
    if (!selectedTicker) return;
    setWatchlistMessage("");
    try {
      const token = await getIdToken();
      if (!token) return;
      const current = await izfinApiFetch<{ tickers: string[] }>("/api/v1/watchlist", token);
      if (current.tickers.includes(selectedTicker)) { setWatchlistMessage(`${selectedTicker} zaten takip listende.`); return; }
      await izfinApiFetch("/api/v1/watchlist", token, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers: [...current.tickers, selectedTicker] }) });
      setWatchlistMessage(`${selectedTicker} takip listene eklendi.`);
    } catch { setWatchlistMessage("Takip listesi güncellenemedi."); }
  }

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
          <div className="subsection-title"><span>LISTENDE DIKKAT ÇEKENLER</span><b>{center.top_signals.length}</b></div>
          <div className="market-sort" aria-label="Sonuç sırası"><span>Sonuç sırası</span><button className={sortBy === "score" ? "active" : ""} type="button" onClick={() => setSortBy("score")}>Skor</button><button className={sortBy === "risk" ? "active" : ""} type="button" onClick={() => setSortBy("risk")}>Risk</button></div>
          <div className="market-signal-table" role="table" aria-label="Listende dikkat çekenler">
            <div className="market-signal-head" role="row"><span>Sembol</span><span>Fiyat</span><span>IZFIN kararı</span><span>Skor</span><span>Güven</span></div>
            {sortedSignals.slice(0, 7).map((item, index) => {
              const ticker = tickerOf(item);
              if (!ticker) return <div className="market-signal-row" role="row" key={`missing-${index}`}><strong>Sembol</strong><span>—</span><span>{text(item.sinyal)}</span><span>{text(item.skor)}</span><span>{text(item.guven)}</span></div>;
              return <a className="market-signal-row" role="row" href={stockDetailHref(jobId, ticker)} key={`${ticker}-${index}`}>
                <strong>{ticker}</strong><span>{text(item.fiyat ?? item.price)}</span><span>{text(item.sinyal)}</span><span>{text(item.skor)}</span><span>{text(item.guven)}</span>
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
              <button className="watchlist-add" type="button" onClick={() => void addSelectedToWatchlist()}>Takip listene ekle</button>
              {watchlistMessage && <p className="watchlist-message" aria-live="polite">{watchlistMessage}</p>}
              <div className="market-decision-context"><span>Karar bileşenleri</span>{Object.entries(detail.decision).filter(([key]) => DECISION_LABELS[key]).slice(0, 4).map(([key, value]) => <p key={key}>{DECISION_LABELS[key]}<b>{text(value)}</b></p>)}</div>
            </>}
          </> : <p>Öne çıkan hisse bulunamadı.</p>}
        </div>
      </div>
      {center.movers.length > 0 && <section className="market-movers" aria-label="Günlük Büyük Hareketler"><div className="subsection-title"><span>GÜNLÜK BÜYÜK HAREKETLER</span><b>HAREKETLİLER</b></div><p>{center.movers.slice(0, 6).map((item) => tickerOf(item)).filter(Boolean).join("  ·  ")}</p></section>}
    </>}
  </section>;
}
