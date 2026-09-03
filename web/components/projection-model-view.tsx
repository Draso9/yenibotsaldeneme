"use client";

import { useMemo } from "react";
import type { ProjectionBand, ProjectionResponse } from "../lib/projection";

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
  return Number.isFinite(parsed)
    ? parsed.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : "—";
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

const projectionModelDimensions = [
  "Güncel Fiyat",
  "ATR Modeli",
  "Volatilite Modeli",
  "Karma Model",
  "45G Karma Bant",
  "Geniş Risk Bandı",
  "Model Güven Skoru",
] as const;

type ProjectionModelViewProps = Readonly<{
  projection: ProjectionResponse;
  ticker: string;
  availableTickers: string[];
  onTickerChange: (ticker: string) => void;
  backHref: string;
}>;

export function ProjectionModelView({ projection, ticker, availableTickers, onTickerChange, backHref }: ProjectionModelViewProps) {
  const rangeStyle = useMemo(() => {
    const downside = projection.bands.find((item) => item.kind === "downside");
    const upside = projection.bands.find((item) => item.kind === "upside");
    const low = downside?.extreme ?? number(projection.model.alt_2s);
    const high = upside?.extreme ?? number(projection.model.ust_2s);
    const current = number(projection.model.fiyat);
    if (!(high > low) || !Number.isFinite(current)) return { left: "50%", width: "0%" };
    const position = Math.max(0, Math.min(100, ((current - low) / (high - low)) * 100));
    return { left: `${position}%`, width: `${Math.max(2, Math.min(100, position))}%` };
  }, [projection]);

  return <main className="projection-page" aria-label={`${ticker} projeksiyon senaryo analizi`}>
    <div className="projection-path"><a className="projection-back" href={backHref}>← Detaylı Analiz</a><span>Akıllı Tarama → Detaylı Analiz → Projeksiyon → {ticker}</span></div>

    <section className="projection-primary-hero projection-hero projection-panel">
      <div className="projection-lab-copy">
        <div className="projection-title-line"><span className="projection-symbol-dot" /><p className="eyebrow">IZFIN PROJECTION LAB</p></div>
        <h1>{ticker}</h1>
        <p className="projection-muted"><b>Projeksiyon & Senaryo Analizi</b> · Seçilen varlık için yaklaşık {projection.horizon_days} günlük hareket bandı ve koşullu teknik senaryolar.</p>
        <div className="projection-model-inline" aria-label="Projeksiyon model kapsamı">
          <span className="projection-mini-badge">45G MODEL</span>
          <strong>ATR + Tarihsel Volatilite</strong>
          <span>45 günlük karma fiyat hareket bandı</span>
        </div>
        {availableTickers.length > 1 && <label className="projection-symbol-switcher">
          <span>TARAMADAKİ VARLIK</span>
          <select value={ticker} onChange={(event) => onTickerChange(event.target.value)}>
            {availableTickers.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>}
      </div>
      <div className="projection-hero-stats">
        <div><span>Güncel Fiyat</span><strong>{price(projection.model.fiyat)}</strong></div>
        <div><span>Karma Model</span><strong className="projection-positive">±{price(projection.model.karma_hareket)}</strong></div>
        <div><span>Model Güven Skoru</span><strong>{text(projection.model.guven_skoru)}<small>/100</small></strong></div>
      </div>
    </section>

    <section className="projection-workspace projection-primary-workspace">
      <article className="projection-primary-range projection-panel projection-range-card" aria-labelledby="projection-primary-range-title">
        <div className="projection-section-head"><div><p className="eyebrow">45G KARMA BANT</p><h2 id="projection-primary-range-title">{projection.horizon_days} günlük hareket bandı</h2></div><span className="projection-mini-badge">Model bandı · hedef fiyat vaadi değil</span></div>
        <div className="projection-range-labels"><span>{price(projection.model.alt_2s)}</span><span>{price(projection.model.fiyat)}</span><span>{price(projection.model.ust_2s)}</span></div>
        <div className="projection-range-track">
          <div className="projection-range-fill" style={{ width: rangeStyle.width }} />
          <i className="projection-range-current" style={{ left: rangeStyle.left }} />
        </div>
        <div className="projection-range-zones"><span>Geniş aşağı risk</span><span>Mevcut fiyat</span><span>Geniş yukarı alan</span></div>
      </article>

      <article className="projection-primary-direction projection-panel projection-direction-card">
        <div className="projection-section-head"><div><p className="eyebrow">ALGORİTMİK YÖN ÖZETİ</p><h2>Algoritmik Yön Özeti</h2></div><span className={`projection-direction projection-direction-${text(projection.scenario.yon_class, "neutral")}`}>{text(projection.scenario.yon)}</span></div>
        <strong className="projection-direction-title">{text(projection.scenario.yon_title)}</strong>
        <p>{text(projection.scenario.model_yorumu)}</p>
        <div className="projection-confidence-track"><span style={{ width: `${Math.max(0, Math.min(100, projection.metrics.guven_ilerleme * 100))}%` }} /></div>
        <small>Mevcut sistem sinyali: {text(projection.scenario.sinyal)} · Model güven skoru {text(projection.model.guven_skoru)}/100</small>
      </article>
    </section>

    <section className="projection-primary-scenarios projection-panel projection-range-card" aria-labelledby="projection-scenario-title">
      <div className="projection-section-head"><div><p className="eyebrow">OLUMLU / OLUMSUZ SENARYOLAR</p><h2 id="projection-scenario-title">Teknik Senaryolar</h2></div><span className="projection-mini-badge">Koşullu tetik · risk iptali</span></div>
      <div className="projection-scenario-grid" aria-label="Teknik senaryolar">
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
      </div>
    </section>

    <details className="projection-disclosure projection-panel projection-model-details">
      <summary>
        <span>Model karşılaştırması ve fiyat bantları</span>
        <small>ATR, volatilite, tüm model bantları ve model uyumu</small>
      </summary>
      <div className="projection-disclosure-body">
        <section className="projection-model-comparison projection-range-card" aria-label="Model Karşılaştırması">
          <div className="projection-section-head">
            <div><p className="eyebrow">MODEL KARŞILAŞTIRMASI</p><h2>Model Karşılaştırması</h2><p className="projection-muted">ATR, tarihsel volatilite ve karma model aynı 45G senaryo çerçevesinde karşılaştırılır.</p></div>
            <span className="projection-mini-badge">{projection.horizon_days}G</span>
          </div>
          <div className="projection-secondary-metrics" aria-label="Projeksiyon model boyutları">
            {projectionModelDimensions.map((label) => <div key={label}><span>{label}</span></div>)}
          </div>
          <div className="projection-metric-list">
            {projection.metrics.birincil.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><strong>{metricValue(item)}</strong></div>)}
          </div>
          <div className="projection-secondary-metrics">
            {projection.metrics.ikincil.map((item, index) => <div key={`${text(item.label)}-${index}`}><span>{text(item.label)}</span><strong>{metricValue(item)}</strong></div>)}
            <div><span>Model uyumu</span><strong>%{Math.round(number(projection.model.model_uyumu) * 100)}</strong></div>
          </div>
          <p className="projection-volatility">{projection.metrics.volatilite_aciklamasi}</p>
        </section>

        <section className="projection-range-card" aria-labelledby="projection-band-title">
          <div className="projection-section-head"><div><p className="eyebrow">45G FİYAT BANTLARI</p><h2 id="projection-band-title">Olası hareket alanı</h2></div><span className="projection-mini-badge">Model bandı · hedef fiyat vaadi değil</span></div>
          <div className="projection-band-grid" aria-label="Model bantları">
            {projection.bands.map((band) => <article className={`projection-band-card ${bandTone(band)}`} key={band.kind}>
              <div className="projection-band-head"><span>{band.label}</span><b>{pct(band.change_pct)}</b></div>
              <strong className="projection-target">{price(band.target)}</strong>
              <div className="projection-band-meta"><span>{band.kind === "base" ? "Referans fiyat" : "1σ hedef"}</span><span>{band.kind === "base" ? `${projection.horizon_days}G baz` : `Geniş uç ${price(band.extreme)}`}</span></div>
            </article>)}
          </div>
        </section>
      </div>
    </details>

    <details className="projection-disclosure projection-panel projection-level-details">
      <summary>
        <span>Teknik seviyeler ve model ayrıntıları</span>
        <small>Destek, direnç, stop ve hedef seviyeleri</small>
      </summary>
      <div className="projection-disclosure-body">
        <section className="projection-range-card">
          <div className="projection-section-head"><div><p className="eyebrow">TEKNİK SEVİYELER</p><h2>Seviyeler ve risk iptali</h2></div><span className="projection-mini-badge">{text(projection.scenario.sinyal)}</span></div>
          <div className="projection-level-grid">
            <div><span>Destek</span><strong>{price(projection.scenario.destek)}</strong></div>
            <div><span>Direnç</span><strong>{price(projection.scenario.direnc)}</strong></div>
            <div><span>Stop</span><strong>{price(projection.scenario.stop)}</strong></div>
            <div><span>TP1</span><strong>{price(projection.scenario.tp1)}</strong></div>
            <div><span>TP2</span><strong>{price(projection.scenario.tp2)}</strong></div>
            <div><span>Model farkı</span><strong>{pct(projection.scenario.model_farki)}</strong></div>
          </div>
        </section>
      </div>
    </details>

    <section className="projection-disclaimer">
      <span>MODEL KAPSAMI</span>
      <p><b>Model kapsamı</b> · Bu çıktı seçili tamamlanmış taramanın ATR ve tarihsel volatilite verisinden üretilen yaklaşık hareket bandı ve koşullu teknik senaryolardır. Kesin hedef fiyat, başarı olasılığı, getiri garantisi veya yatırım tavsiyesi değildir.</p>
    </section>
  </main>;
}