"use client";

import { FormEvent, useEffect, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";

type WatchlistResponse = { tickers: string[]; recovered: boolean };

export function Dashboard() {
  const { user, getIdToken } = useIzfinAuth();
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) { setWatchlist(null); return; }
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await izfinApiFetch<WatchlistResponse>("/api/v1/watchlist", token);
        if (active) { setWatchlist(result); setDraft(result.tickers.join(", ")); }
      } catch {
        if (active) setError("Takip listesi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, user]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const tickers = [...new Set(draft.split(",").map((value) => value.trim().toUpperCase()).filter(Boolean))];
    if (!tickers.length) { setError("En az bir sembol girin."); return; }
    try {
      const token = await getIdToken();
      if (!token) return;
      const result = await izfinApiFetch<WatchlistResponse>("/api/v1/watchlist", token, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers }),
      });
      setWatchlist(result); setDraft(result.tickers.join(", "));
    } catch { setError("Takip listesi kaydedilemedi."); }
  }

  if (!user) return null;
  return <section className="dashboard" aria-label="Kişisel takip listesi">
    <div className="section-heading"><div><p className="eyebrow">KİŞİSEL ALAN</p><h2>Takip Listen</h2></div><span className="section-index">LISTE</span></div>
    {error && <p role="alert">{error}</p>}
    {!error && !watchlist && <p>Liste yükleniyor…</p>}
    {watchlist && <><div className="ticker-list">{watchlist.tickers.map((ticker) => <span key={ticker}>{ticker}</span>)}</div>
      <form className="watchlist-form" onSubmit={save}><label>Semboller (virgülle ayırın)<input value={draft} onChange={(event) => setDraft(event.target.value)} /></label><button type="submit">Listeyi kaydet</button></form></>}
  </section>;
}
