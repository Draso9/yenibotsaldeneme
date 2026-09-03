"use client";

import { confidenceScore, confidenceExplanation } from "../lib/signal-labels";

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

function numeric(value: unknown): number { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : -Infinity; }
function signedPct(value: unknown): string { const parsed = Number(value); return Number.isFinite(parsed) ? `${parsed >= 0 ? "+" : ""}${parsed.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%` : "—"; }
function decisionCount(value: unknown): string { const parsed = Number(value); return Number.isFinite(parsed) ? String(parsed) : "0"; }
function factorWidth(value: unknown): string { const parsed = Number(value); return `${Math.max(0, Math.min(100, Number.isFinite(parsed) ? parsed : 0))}%`; }
const DECISION_LABELS: Record<string, string> = { karar: "Karar", guven: "Güven puanı", mtf_uyum: "MTF uyumu", risk: "Risk", giris_puani: "Giriş" };

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
    {center?.empty && <div className="market-center-empty market-center-state">Bu taramada Piyasa Merkezi için gösterilecek sonuç bulunamadı.</div>}
    {center && !center.empty && <>
      <div className="market-decision-head"><div><p className="eyebrow">IZFIN KARAR MERKEZİ</p><h3>Son Tarama Özeti</h3><small>{text(center.metrics.kaynak)} · Son taranan evrene göre</small></div><strong className={`market-mode-badge is-${text(center.decision.mod_cls, "neutral")}`}>{text(center.decision.mod)} · {text(center.metrics.pulse)}/100</strong></div>
      <div className="market-decision-kpis"><span><b>{decisionCount(center.decision.alim_tarafi)}</b>ALIM TARAFI<small>AL / Güçlü AL</small></span><span><b>{decisionCount(center.decision.guclu_al)}</b>GÜÇLÜ SETUP<small>yüksek öncelik</small></span><span><b>{decisionCount(center.decision.teyit)}</b>TEYİT BEKLEYEN<small>henüz tamamlanmadı</small></span><span><b>{decisionCount(center.decision.yuksek_risk)}</b>YÜKSEK RİSK<small>dikkat gerektiriyor</small></span></div>
      <div className="market-factor-grid">{[["TREND", center.metrics.trend], ["MOMENTUM", center.metrics.momentum], ["PARA AKIŞI", center.metrics.flow], ["RİSK", center.metrics.risk]].map(([name, value]) => <div key={String(name)}><span>{text(name)}<b>{text(value)}</b></span><i><em style={{ width: factorWidth(value) }} /></i></div>)}</div>
      <div className="market-system-comment"><span>SİSTEM YORUMU</span><p>{text(center.decision.yorum)}</p></div>
      <div className="market-columns">
        <div className="market-signals">
          <div className="subsection-title"><span>Son taramada dikkat çekenler</span><b>{center.top_signals.length}</b></div>
          <div className="market-signal-table" role="table" aria-label="Son taramada dikkat çekenler">
            <div className="market-signal-head" role="row"><span>Sembol</span><span>Fiyat</span><span>IZFIN kararı</span><span>Skor</span><span title={confidenceExplanation}>Güven puanı</span><span>MTF</span><span>Risk</span></div>
            {center.top_signals.slice(0, 7).map((item, index) => {
              const ticker = tickerOf(item);
              if (!ticker) return null;
              return <a className="market-signal-row" role="row" href={stockDetailHref(jobId, ticker)} key={`${ticker}-${index}`}>
                <strong>{ticker}</strong><span>{text(item.fiyat ?? item.price)}</span><span>{text(item.sinyal)}</span><span>{text(item.skor)}</span><span>{confidenceScore(item.guven)}</span><span>%{text(item.mtf)}</span><span>{text(item.risk)}</span>
              </a>;
            })}
          </div>
        </div>
        <div className="market-focus-card">
          <div className="subsection-title"><span>SON TARAMADA ÖNE ÇIKAN</span><b>SON TARAMA</b></div>
          {selectedTicker ? <>
            <h3>{selectedTicker}</h3>
            {!detail && !detailError && <p>Detay yükleniyor…</p>}
            {detailError && <p role="alert">{detailError}</p>}
            {detail && <>
              <div className="focus-kv"><span>IZFIN Skor<b>{text(detail.score.nihai)}</b></span><span title={confidenceExplanation}>Güven puanı<b>{confidenceScore(detail.decision.guven)}</b></span><span>MTF<b>%{text(detail.decision.mtf_uyum)}</b></span><span>Risk<b>{text(detail.decision.risk)}</b></span></div><p className="market-focus-signal">{text(detail.signal)}</p>
              <a className="detail-open" href={stockDetailHref(jobId, selectedTicker)}>Detaylı analizi aç →</a>
              <div className="market-decision-context"><span>Karar bileşenleri</span>{Object.entries(detail.decision).filter(([key]) => DECISION_LABELS[key]).slice(0, 4).map(([key, value]) => <p key={key}>{DECISION_LABELS[key]}<b>{key === "guven" ? confidenceScore(value) : text(value)}</b></p>)}</div>
            </>}
          </> : <p>Öne çıkan hisse bulunamadı.</p>}
        </div>
      </div>
      {center.movers.length > 0 && <section className="market-movers" aria-label="Günlük Büyük Hareketler"><div className="subsection-title"><span>Günlük Büyük Hareketler</span><b>HAREKETLİLER</b></div><div className="market-mover-table"><div><span>VARLIK</span><span>FİYAT</span><span>DEĞİŞİM</span></div>{center.movers.slice(0, 6).map((item, index) => { const ticker = tickerOf(item); const change = numeric(item.degisim); if (!ticker) return null; return <a href={stockDetailHref(jobId, ticker)} key={`${ticker}-${index}`}><b>{ticker}</b><span>{text(item.fiyat)}</span><strong className={change >= 0 ? "positive" : "negative"}>{signedPct(item.degisim)}</strong></a>; })}</div></section>}
      <p className="market-disclosure">Piyasa modu tüm piyasanın resmi breadth göstergesi değildir; IZFIN’in son taramada analiz ettiği listenin teknik bileşiminden üretilir.</p>
    </>}
  </section>;
}
