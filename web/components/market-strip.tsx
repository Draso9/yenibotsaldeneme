"use client";

import { useEffect, useState } from "react";
import { fetchMarketStrip, type MarketStripResponse } from "../lib/market-strip";

const MARKET_STRIP_REVALIDATE_MS = 60_000;
const MARKET_STRIP_FRESHNESS_TICK_MS = 1_000;

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
  const [stale, setStale] = useState(false);
  const [lastSuccessfulAt, setLastSuccessfulAt] = useState<number | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    let active = true;

    const refreshSnapshot = () => {
      void fetchMarketStrip()
        .then((result) => {
          if (!active) return;
          const receivedAt = Date.now();
          setSnapshot(result);
          setLastSuccessfulAt(receivedAt);
          setNowMs(receivedAt);
          setStale(false);
        })
        .catch(() => {
          if (active) setStale(true);
        });
    };

    refreshSnapshot();
    const revalidateTimer = window.setInterval(refreshSnapshot, MARKET_STRIP_REVALIDATE_MS);
    const freshnessTimer = window.setInterval(() => {
      if (active) setNowMs(Date.now());
    }, MARKET_STRIP_FRESHNESS_TICK_MS);
    window.addEventListener("focus", refreshSnapshot);
    window.addEventListener("online", refreshSnapshot);

    return () => {
      active = false;
      window.clearInterval(revalidateTimer);
      window.clearInterval(freshnessTimer);
      window.removeEventListener("focus", refreshSnapshot);
      window.removeEventListener("online", refreshSnapshot);
    };
  }, []);

  const elapsedSinceSuccessSeconds = lastSuccessfulAt === null
    ? 0
    : Math.max(0, (nowMs - lastSuccessfulAt) / 1000);
  const displayedFreshness = snapshot?.gecikme_sn === null || snapshot?.gecikme_sn === undefined
    ? null
    : snapshot.gecikme_sn + elapsedSinceSuccessSeconds;

  if (!snapshot && stale) return <section className="market-strip market-strip-unavailable" aria-label="Piyasa özeti">
    <div className="market-strip-status">
      <span className="eyebrow">PİYASALAR</span>
      <strong>Piyasa verisi şu anda alınamıyor</strong>
      <small>Bağlantı yeniden kurulduğunda güncel özet burada görünecek.</small>
    </div>
  </section>;

  return <section className={`market-strip${stale ? " market-strip-stale" : ""}`} aria-label="Piyasa özeti">
    <div className="market-strip-status">
      <span className="eyebrow">PİYASALAR</span>
      <strong>{snapshot?.durum ?? "Veri hazırlanıyor"}</strong>
      <small>{snapshot
        ? `${freshness(displayedFreshness)} · ${snapshot.yerel_saat}${stale ? " · Son yenileme başarısız; son geçerli veri gösteriliyor" : ""}`
        : "Güncel piyasa özeti hazırlanıyor…"}</small>
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
