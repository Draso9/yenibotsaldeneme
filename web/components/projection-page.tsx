"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchProjection, type ProjectionBand, type ProjectionResponse } from "../lib/projection";
import { fetchScanJobContext, resolveTicker, resultTickers } from "../lib/scan-context";
import { stockDetailHref } from "../lib/stock-detail-route";
import { useAnalysisContext } from "./analysis-context-provider";
import { useIzfinAuth } from "./auth-provider";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function number(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function price(value: unknown): string {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
}

function pct(value: unknown): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return `${parsed > 0 ? "+" : ""}${parsed.toLocaleString("tr-TR", { maximumFractionDigits: 1 })}%`;
}

function metricValue(item: Record<string, unknown>): string {
  const delta = text(item.delta, "");
  return `${text(item.value)}${delta ? ` · ${delta}` : ""}`;
}

function bandTone(band: ProjectionBand): string {
  if (band.kind === "downside") return "projection-band-down";
  if (band.kind === "upside") return "projection-band-up";
  return "projection-band-base";
}

export function ProjectionPage({ jobId, ticker }: Readonly<{ jobId: string; ticker: string }>) {
  const { loading, user, getIdToken } = useIzfinAuth();
  const {
    activeScanJobId,
    latestCompletedScanJobId,
    selectedTicker,
    setActiveScan,
    setSelectedTicker,
    refreshLatestCompletedScan,
  } = useAnalysisContext();
  const explicitJobId = String(jobId || "").trim();
  const explicitTicker = String(ticker || "").trim().toUpperCase();
  const [resolvedJobId, setResolvedJobId] = useState(explicitJobId);
  const [resolvedTicker, setResolvedTicker] = useState(explicitTicker);
  const [availableTickers, setAvailableTickers] = useState<string[]>([]);
  const [contextLoading, setContextLoading] = useState(true);
  const [contextRefreshAttempted, setContextRefreshAttempted] = useState(false);
  const [projection, setProjection] = useState<ProjectionResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setContextRefreshAttempted(false);
  }, [user?.uid]);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;

    void (async () => {
      const candidateJobId = explicitJobId || activeScanJobId || latestCompletedScanJobId;
      if (!candidateJobId) {
        if (!contextRefreshAttempted) {
          setContextLoading(true);
          try { await refreshLatestCompletedScan(); } catch { /* guided state below after one server-truth attempt */ }
          if (active) setContextRefreshAttempted(true);
          return;
        }
        if (active) {
          setResolvedJobId("");
          setResolvedTicker("");
          setAvailableTickers([]);
          setContextLoading(false);
        }
        return;
      }

      setContextLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        if (!token) return;

        let candidate = await fetchScanJobContext(candidateJobId, token);
        let finalJobId = candidateJobId;
        if (candidate.status !== "completed") {
          const fallbackJobId = latestCompletedScanJobId;
          if (!explicitJobId && fallbackJobId && fallbackJobId !== candidateJobId) {
            candidate = await fetchScanJobContext(fallbackJobId, token);
            finalJobId = fallbackJobId;
          }
        }

        if (candidate.status !== "completed") {
          if (active) {
            setResolvedJobId("");
            setResolvedTicker("");
            setAvailableTickers([]);
            setError("Seçili tarama henüz projeksiyon için hazır değil.");
          }
          return;
        }

        const tickers = resultTickers(candidate);
        if (!tickers.length) {
          if (active) {
            setResolvedJobId("");
            setResolvedTicker("");
            setAvailableTickers([]);
            setError("Bu tamamlanmış taramada projeksiyon için kullanılabilir teknik veri yok.");
          }
          return;
        }
        const nextTicker = resolveTicker(explicitTicker, selectedTicker, tickers);
        if (!active) return;
        setResolvedJobId(finalJobId);
        setAvailableTickers(tickers);
        setResolvedTicker(nextTicker);
        setActiveScan(finalJobId);
        if (nextTicker) setSelectedTicker(nextTicker);
      } catch {
        if (active) setError("Son tamamlanan tarama bağlamı yüklenemedi.");
      } finally {
        if (active) setContextLoading(false);
      }
    })();

    return () => { active = false; };
  }, [activeScanJobId, contextRefreshAttempted, explicitJobId, explicitTicker, getIdToken, latestCompletedScanJobId, loading, refreshLatestCompletedScan, selectedTicker, setActiveScan, setSelectedTicker, user]);

  useEffect(() => {
    if (loading || contextLoading || !user || !resolvedJobId || !resolvedTicker) return;
    let active = true;
    setProjection(null);
    setError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchProjection(resolvedJobId, resolvedTicker, token);
        if (active) setProjection(result);
      } catch {
        if (active) setError("Projeksiyon bu tarama için yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [contextLoading, getIdToken, loading, resolvedJobId, resolvedTicker, user]);

  const rangeStyle = useMemo(() => {
    if (!projection) return { left: "50%", width: "0%" };
    const downside = projection.bands.find((item) => item.kind === "downside");
    const upside = projection.bands.find((item) => item.kind === "upside");
    const low = downside?.extreme ?? number(projection.model.alt_2s);
    const high = upside?.extreme ?? number(projection.model.ust_2s);
    const current = number(projection.model.fiyat);
    if (!(high > low) || !Number.isFinite(current)) return { left: "50%", width: "0%" };
    const position = Math.max(0, Math.min(100, ((current - low) / (high - low)) * 100));
    return { left: `${position}%`, width: `${Math.max(2, Math.min(100, position))}%` };
  }, [projection]);

  const backHref = resolvedJobId && resolvedTicker ? stockDetailHref(resolvedJobId, resolvedTicker) : "/";

  if (loading || contextLoading) {
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-status" aria-live="polite"><strong>Analiz bağlamı hazırlanıyor</strong><span>Son tamamlanan taraman ve seçili varlık geri yükleniyor.</span></section></main>;
  }

  if (!user) {
    return <main className="projection-page"><a className="projection-back" href="/">← Ana sayfa</a><section className="projection-panel"><p className="eyebrow">PROJEKSİYON</p><h1>Projeksiyon Merkezi</h1><p>Tarama sonuçlarındaki model bantlarını görmek için IZFIN hesabınla giriş yap.</p></section></main>;
  }

  if (!resolvedJobId && !error) {
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-empty"><p className="eyebrow">PROJEKSİYON</p><h1>Henüz tamamlanmış bir taraman yok</h1><p>45 günlük senaryo analizi, Akıllı Tarama sonucundaki gerçek teknik panel verisini kullanır.</p><a href="/scan">Akıllı Tarama'yı aç →</a></section></main>;
  }

  if (resolvedJobId && availableTickers.length > 1 && !resolvedTicker) {
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-ticker-selector"><p className="eyebrow">SON TAMAMLANAN TARAMA</p><h1>Projeksiyon için hisse seç</h1><p>Son tamamlanan taramandaki varlıklardan birini seç.</p><select value={resolvedTicker} onChange={(event) => { const next = event.target.value; setResolvedTicker(next); setSelectedTicker(next); }}><option value="">Hisse seç…</option>{availableTickers.map((value) => <option value={value} key={value}>{value}</option>)}</select></section></main>;
  }

  if (!resolvedJobId || !resolvedTicker) {
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-status" role="alert"><strong>Projeksiyon bağlamı kullanılamıyor</strong><span>{error || "Tamamlanmış taramadan bir varlık seçilemedi."}</span><a href="/scan">Akıllı Tarama'yı aç →</a></section></main>;
  }

  return <main className="projection-page" aria-label={`${resolvedTicker} projeksiyon senaryo analizi`}>
    <div className="projection-path"><a className="projection-back" href={backHref}>← Detaylı Analiz</a><span>Tarama sonucu / {resolvedTicker} / Projeksiyon</span></div>

    <section className="projection-hero projection-panel">
      <div>
        <div className="projection-title-line"><span className="projection-symbol-dot" /><p className="eyebrow">PROJEKSİYON SENARYO ANALİZİ</p></div>
        <h1>{resolvedTicker}</h1>
        <p className="projection-muted">Mevcut taramadaki teknik panelden üretilen {projection?.horizon_days ?? 45} günlük ATR + tarihsel volatilite modeli.</p>
        {availableTickers.length > 1 && <label className="projection-symbol-switcher">
          <span>TARAMADAKİ VARLIK</span>
          <select value={resolvedTicker} onChange={(event) => { const next = event.target.value; setResolvedTicker(next); setSelectedTicker(next); }}>
            {availableTickers.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>}
      </div>
      {projection && <div className="projection-hero-stats">
        <div><span>Güncel fiyat</span><strong>{price(projection.model.fiyat)}</strong></div>
        <div><span>Karma hareket</span><strong className="projection-positive">±{price(projection.model.karma_hareket)}</strong></div>
        <div><span>Model güveni</span><strong>{text(projection.model.guven_skoru)}<small>/100</small></strong></div>
      </div>}
    </section>

    {!projection && !error && <section className="projection-panel projection-status" aria-live="polite"><strong>Model hazırlanıyor</strong><span>Tarama verisindeki teknik panel ve volatilite bantları işleniyor.</span></section>}
    {error && <section className="projection-panel projection-status" role="alert"><strong>Projeksiyon kullanılamıyor</strong><span>{error}</span></section>}

    {projection && <>
      <section className="projection-band-grid" aria-label="Model bantları">
        {projection.bands.map((band) => <article className={`projection-band-card ${bandTone(band)}`} key={band.kind}>
          <div className="projection-band-head"><span>{band.label}</span><b>{pct(band.change_pct)}</b></div>
          <strong className="projection-target">{price(band.target)}</strong>
          <div className="projection-band-meta"><span>{band.kind === "base" ? "Referans fiyat" : "1σ hedef"}</span><span>{band.kind === "base" ? `${projection.horizon_days}G baz` : `Geniş uç ${price(band.extreme)}`}</span></div>
        </article>)}
      </section>

      <section className="projection-scenario-grid" aria-label="Teknik senaryolar">
        <article className="projection-panel projection-scenario-card projection-scenario-up">
          <div className="projection-scenario-head"><div><p className="eyebrow">POZİTİF SENARYO</p><h2>{projection.technical_scenarios.up.title}</h2></div><span>YUKARI</span></div>
          <div className="projection-scenario-row"><span>Tetik</span><strong>{projection.technical_scenarios.up.trigger}</strong></div>
          <div className="projection-scenario-row"><span>Teknik hedefler</span><strong>{projection.technical_scenarios.up.targets.map(price).join(" → ")}</strong></div>
          <div className="projection-scenario-row"><span>Karma model üst bantları</span><strong>{projection.technical_scenarios.up.model_bands.map(price).join(" → ")}</strong></div>
          <div className="projection-scenario-row"><span>Risk iptali / stop</span><strong>{price(projection.technical_scenarios.up.risk_invalidation)}</strong></div>
        </article>

        <article className="projection-panel projection-scenario-card projection-scenario-down">
          <div className="projection-scenario-head"><div><p className="eyebrow">NEGATİF SENARYO</p><h2>{projection.technical_scenarios.down.title}</h2></div><span>AŞAĞI</span></div>
          <div className="projection-scenario-row"><span>Tetik</span><strong>{projection.technical_scenarios.down.trigger}</strong></div>
          <div className="projection-scenario-row"><span>Karma model aşağı bantları</span><strong>{projection.technical_scenarios.down.model_bands.map(price).join(" → ")}</strong></div>
          <div className="projection-scenario-row"><span>Senaryo geçersizliği</span><strong>{price(projection.technical_scenarios.down.invalidation)} üzeri kalıcılık</strong></div>
        </article>
      </section>

      <section className="projection-workspace">
        <article className="projection-panel projection-range-card">
          <div className="projection-section-head"><div><p className="eyebrow">FİYAT BANTI</p><h2>{projection.horizon_days} günlük karma model</h2></div><span className="projection-confidence">Güven %{text(projection.model.guven_skoru)}</span></div>
          <div className="projection-range-labels"><span>{price(projection.model.alt_2s)}</span><span>{price(projection.model.fiyat)}</span><span>{price(projection.model.ust_2s)}</span></div>
          <div className="projection-range-track">
            <div className="projection-range-fill" style={{ width: rangeStyle.width }} />
            <i className="projection-range-current" style={{ left: rangeStyle.left }} />
          </div>
          <div className="projection-range-zones"><span>Geniş aşağı risk</span><span>Mevcut fiyat</span><span>Geniş yukarı alan</span></div>
          <p className="projection-volatility">{projection.metrics.volatilite_aciklamasi}</p>
        </article>

        <article className="projection-panel projection-direction-card">
          <div className="projection-section-head"><div><p className="eyebrow">ALGORİTMİK YÖN</p><h2>{text(projection.scenario.yon_title)}</h2></div><span className={`projection-direction projection-direction-${text(projection.scenario.yon_class, "neutral")}`}>{text(projection.scenario.yon)}</span></div>
          <p>{text(projection.scenario.model_yorumu)}</p>
          <div className="projection-confidence-track"><span style={{ width: `${Math.max(0, Math.min(100, projection.metrics.guven_ilerleme * 100))}%` }} /></div>
          <small>Mevcut sistem sinyali: {text(projection.scenario.sinyal)} · Model uyumu %{Math.round(number(projection.model.model_uyumu) * 100)}</small>
        </article>
      </section>

      <section className="projection-lower-grid">
        <article className="projection-panel">
          <div className="projection-section-head"><div><p className="eyebrow">MODEL KARŞILAŞTIRMASI</p><h2>Hareket tahmini</h2></div><span className="projection-mini-badge">{projection.horizon_days}G</span></div>
          <div className="projection-metric-list">
            {projection.metrics.birincil.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><strong>{metricValue(item)}</strong></div>)}
          </div>
          <div className="projection-secondary-metrics">
            {projection.metrics.ikincil.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><strong>{metricValue(item)}</strong></div>)}
          </div>
        </article>

        <article className="projection-panel">
          <div className="projection-section-head"><div><p className="eyebrow">TEKNİK SEVİYELER</p><h2>Seviyeler ve risk iptali</h2></div><span className="projection-mini-badge">{text(projection.scenario.sinyal)}</span></div>
          <div className="projection-level-grid">
            <div><span>Destek</span><strong>{price(projection.scenario.destek)}</strong></div>
            <div><span>Direnç</span><strong>{price(projection.scenario.direnc)}</strong></div>
            <div><span>Stop</span><strong>{price(projection.scenario.stop)}</strong></div>
            <div><span>TP1</span><strong>{price(projection.scenario.tp1)}</strong></div>
            <div><span>TP2</span><strong>{price(projection.scenario.tp2)}</strong></div>
            <div><span>Model farkı</span><strong>{pct(projection.scenario.model_farki)}</strong></div>
          </div>
        </article>
      </section>

      <section className="projection-disclaimer">
        <span>MODEL KAPSAMI</span>
        <p><b>Model kapsamı</b> · Bu ekran yalnızca seçtiğin tamamlanmış taramanın ATR ve tarihsel volatilite verisiyle olası fiyat hareket bantlarını gösterir; hedef fiyat veya yatırım tavsiyesi değildir.</p>
      </section>
    </>}
  </main>;
}
