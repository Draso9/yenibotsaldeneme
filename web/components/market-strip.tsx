"use client";

import { useEffect, useState } from "react";
import { fetchMarketStrip, type MarketStripResponse } from "../lib/market-strip";

function price(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("tr-TR", { maximumFractionDigits: Math.abs(value) < 10 ? 3 : 2 });
}

function change(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `%${value >= 0 ? "+" : ""}${value.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function freshness(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "Tazelik —";
  return seconds < 120 ? `Tazelik ~${Math.round(seconds)} sn` : `Tazelik ~${Math.round(seconds / 60)} dk`;
}

export function MarketStrip() {
  const [snapshot, setSnapshot] = useState<MarketStripResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchMarketStrip()
      .then((result) => { if (active) setSnapshot(result); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);

  if (error) return <section className="market-strip market-strip-unavailable" aria-label="Piyasa özeti">
    <div className="market-strip-status">
      <span className="eyebrow">PİYASALAR</span>
      <strong>Piyasa verisi şu anda alınamıyor</strong>
      <small>Bağlantı yeniden kurulduğunda güncel özet burada görünecek.</small>
    </div>
  </section>;

  return <section className="market-strip" aria-label="Piyasa özeti">
    <div className="market-strip-status">
      <span className="eyebrow">PİYASALAR</span>
      <strong>{snapshot?.durum ?? "Veri hazırlanıyor"}</strong>
      <small>{snapshot ? `${freshness(snapshot.gecikme_sn)} · ${snapshot.yerel_saat}` : "Güncel piyasa özeti hazırlanıyor…"}</small>
    </div>
    <div className="market-strip-items">
      {(snapshot?.items ?? []).map((item) => {
        const direction = item.deg === null || item.deg === 0 ? "neutral" : item.deg > 0 ? "up" : "down";
        return <article key={item.ad}>
          <span>{item.ad}</span>
          <strong>{price(item.fiyat)}</strong>
          <b className={direction}>{direction === "up" ? "▲" : direction === "down" ? "▼" : "•"} {change(item.deg)}</b>
          <small>{item.kaynak}</small>
        </article>;
      })}
    </div>
  </section>;
}
