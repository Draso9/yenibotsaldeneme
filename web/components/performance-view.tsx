"use client";

import { useMemo, useState } from "react";
import { PerformanceMobileCards } from "./performance-mobile-cards";
import type {
  PerformancePositionsResponse,
  PerformanceScorecardResponse,
} from "../lib/performance";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function number(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function pctClass(value: unknown): string {
  const parsed = number(value);
  if (parsed === null || parsed === 0) return "neutral";
  return parsed > 0 ? "positive" : "negative";
}

function pct(value: unknown): string {
  const parsed = number(value);
  if (parsed === null) return "—";
  return `${parsed > 0 ? "+" : ""}${parsed.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}%`;
}

function price(value: unknown): string {
  const parsed = number(value);
  return parsed === null
    ? "—"
    : parsed.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function rowKey(row: Record<string, unknown>, index: number): string {
  return `${text(row["Varlık"])}-${text(row["İlk Alım Tarihi"], text(row["Sinyal Tarihi"], String(index)))}`;
}

function scorecardValue(column: string, value: unknown): string {
  if (column.includes("%")) return pct(value);
  return text(value);
}

export function PerformancePositionTrackingView({ tracking }: { tracking: PerformancePositionsResponse }) {
  const [selectedClosedIndex, setSelectedClosedIndex] = useState<number | null>(null);
  const closedSummary = tracking.closed_summary;
  const selectedClosed = selectedClosedIndex === null ? null : tracking.closed[selectedClosedIndex] ?? null;

  return <>
    <section className="performance-kpi-strip" aria-label="Pozisyon takip KPI'ları">
      {tracking.kpis.map((item) => <article className="performance-panel performance-track-kpi" key={item.label}><span>{item.label}</span><strong>{item.value}</strong></article>)}
    </section>

    <section className="performance-panel performance-table-card">
      <div className="performance-section-title"><div><p className="eyebrow">AKTİF ALIM POZİSYONLARI</p><h2>Devam eden sinyal dönemleri</h2></div><span>{tracking.active.length} aktif</span></div>
      <div className="performance-mobile-section"><PerformanceMobileCards rows={tracking.active} variant="active" /></div>
      {tracking.active.length === 0 ? <p className="performance-table-empty">Şu anda açık alım pozisyonu bulunmuyor.</p> : <div className="performance-table-scroll performance-position-table"><table className="performance-table">
        <thead><tr><th>İlk alım</th><th>Varlık</th><th>İlk sinyal</th><th>Güncel sinyal</th><th>İlk fiyat</th><th>Güncel fiyat</th><th>K/Z</th><th>Geçen gün</th><th>Durum</th></tr></thead>
        <tbody>{tracking.active.map((row, index) => <tr key={rowKey(row, index)}>
          <td>{text(row["İlk Alım Tarihi"])}</td><td><b>{text(row["Varlık"])}</b></td><td>{text(row["İlk Sinyal"])}</td><td>{text(row["Güncel Sinyal"])}</td><td>{price(row["İlk Alım Fiyatı"])}</td><td>{price(row["Güncel Fiyat"])}</td><td className={pctClass(row["Kâr / Zarar %"])}>{pct(row["Kâr / Zarar %"])}</td><td>{text(row["Geçen Gün"])}</td><td>{text(row.Durum)}</td>
        </tr>)}</tbody>
      </table></div>}
      <p className="performance-table-note">İlk giriş fiyatı aynı alım dönemi boyunca sabit kalır; sinyal türündeki değişim yeni pozisyon açmaz.</p>
    </section>

    <section className="performance-closed-summary">
      <article className="performance-panel performance-closed-card"><span>KAPANMIŞ ALIM DÖNEMİ</span><strong>{closedSummary.adet}</strong><small>Tamamlanan dönem</small></article>
      <article className="performance-panel performance-closed-card"><span>FARKLI HİSSE</span><strong>{closedSummary.unique_tickers}</strong><small>Örneklem çeşitliliği</small></article>
      <article className="performance-panel performance-closed-card"><span>POZİTİF KAPANIŞ</span><strong>{pct(closedSummary.win_rate)}</strong><small>Win rate</small></article>
      <article className="performance-panel performance-closed-card"><span>ORT. GETİRİ</span><strong className={pctClass(closedSummary.avg_ret)}>{pct(closedSummary.avg_ret)}</strong><small>Kapalı dönem ortalaması</small></article>
      <article className="performance-panel performance-closed-card"><span>MEDYAN GETİRİ</span><strong className={pctClass(closedSummary.median_ret)}>{pct(closedSummary.median_ret)}</strong><small>Uç değerlerden arındırılmış merkez</small></article>
      <article className="performance-panel performance-closed-card"><span>MEDYAN SÜRE</span><strong>{closedSummary.median_days === null ? "—" : `${text(closedSummary.median_days)} gün`}</strong><small>Taşıma süresi</small></article>
      <article className="performance-panel performance-closed-card"><span>TP1 GÖRÜLME</span><strong>{pct(closedSummary.tp1_rate)}</strong><small>İlk hedefe ulaşan dönemler</small></article>
      <article className="performance-panel performance-closed-card"><span>STOP GÖRÜLME</span><strong>{pct(closedSummary.stop_rate)}</strong><small>İlk stopu gören dönemler</small></article>
    </section>

    <section className="performance-panel performance-table-card">
      <div className="performance-section-title"><div><p className="eyebrow">KAPANMIŞ POZİSYON GEÇMİŞİ</p><h2>Gerçekleşmiş alım dönemleri</h2></div><span>{tracking.closed.length} kayıt</span></div>
      <div className="performance-mobile-section"><PerformanceMobileCards rows={tracking.closed} variant="closed" onInspectClosed={setSelectedClosedIndex} /></div>
      {tracking.closed.length === 0 ? <p className="performance-table-empty">Henüz kapanmış alım dönemi bulunmuyor.</p> : <div className="performance-table-scroll performance-position-table"><table className="performance-table performance-table-wide">
        <thead><tr><th>İlk alım</th><th>Kapanış</th><th>Varlık</th><th>Son sinyal</th><th>Kapanış nedeni</th><th>Giriş</th><th>Kapanış</th><th>K/Z</th><th>Gün</th><th>Maks. kâr</th><th>Maks. düşüş</th><th>İlk stop</th><th>İlk TP1</th><th>TP1</th><th>TP2</th><th>TP3</th><th>Stop</th><th>Detay</th></tr></thead>
        <tbody>{tracking.closed.map((row, index) => <tr key={rowKey(row, index)}>
          <td>{text(row["İlk Alım Tarihi"])}</td><td>{text(row["Kapanış Tarihi"])}</td><td><b>{text(row["Varlık"])}</b></td><td>{text(row["Son Alım Sinyali"])}</td><td>{text(row["Kapanış Nedeni"])}</td><td>{price(row["İlk Alım Fiyatı"])}</td><td>{price(row["Kapanış Fiyatı"])}</td><td className={pctClass(row["Kâr / Zarar %"])}>{pct(row["Kâr / Zarar %"])}</td><td>{text(row["Pozisyonda Gün"])}</td><td className={pctClass(row["Maks. Kâr %"])}>{pct(row["Maks. Kâr %"])}</td><td className={pctClass(row["Maks. Düşüş %"])}>{pct(row["Maks. Düşüş %"])}</td><td>{price(row["İlk Stop"])}</td><td>{price(row["İlk TP1"])}</td><td>{text(row.TP1)}</td><td>{text(row.TP2)}</td><td>{text(row.TP3)}</td><td>{text(row.Stop)}</td><td><button className="performance-detail-button" type="button" onClick={() => setSelectedClosedIndex(index)}>{selectedClosedIndex === index ? "Açık" : "İncele"}</button></td>
        </tr>)}</tbody>
      </table></div>}
      <p className="performance-table-note">Maksimum hareketler ve hedef temasları yalnızca ilgili pozisyon dönemi için mevcut kayıtlarla gösterilir; eksik eski ölçümler “—” kalır.</p>
    </section>

    {closedSummary.reason_counts.length > 0 && <section className="performance-panel performance-insight-card"><p className="eyebrow">EN SIK KAPANIŞ NEDENLERİ</p><div className="performance-definition-grid">{closedSummary.reason_counts.map(([reason, count]) => <article className="performance-panel" key={reason}><b>{reason}</b><span>{count} dönem</span></article>)}</div></section>}

    {selectedClosed && <section className="performance-panel performance-drilldown" aria-label="Kapanmış pozisyon detayı"><div className="performance-section-title"><div><p className="eyebrow">DÖNEM DETAYI</p><h2>{text(selectedClosed["Varlık"])} · {text(selectedClosed["Kapanış Nedeni"])}</h2></div><button type="button" onClick={() => setSelectedClosedIndex(null)}>Kapat ×</button></div><div className="performance-drilldown-grid"><span><small>İlk alım / kapanış</small><b>{text(selectedClosed["İlk Alım Tarihi"])} → {text(selectedClosed["Kapanış Tarihi"])}</b></span><span><small>Giriş / kapanış fiyatı</small><b>{price(selectedClosed["İlk Alım Fiyatı"])} → {price(selectedClosed["Kapanış Fiyatı"])}</b></span><span><small>Gerçekleşen getiri</small><b className={pctClass(selectedClosed["Kâr / Zarar %"])}>{pct(selectedClosed["Kâr / Zarar %"])}</b></span><span><small>Pozisyonda kalma</small><b>{text(selectedClosed["Pozisyonda Gün"])} gün</b></span><span><small>İlk risk planı</small><b>Stop {price(selectedClosed["İlk Stop"])} · TP1 {price(selectedClosed["İlk TP1"])}</b></span><span><small>Hedef temasları</small><b>TP1 {text(selectedClosed.TP1)} · TP2 {text(selectedClosed.TP2)} · TP3 {text(selectedClosed.TP3)} · Stop {text(selectedClosed.Stop)}</b></span></div></section>}

    {closedSummary.yorumlar.length > 0 && <section className="performance-panel performance-insight-card"><p className="eyebrow">IZFIN GEÇMİŞ PERFORMANS ÖZETİ</p><div className="performance-insight-head"><h2>Sistem geçmişte ne yaptı?</h2><div><span><b>En iyi</b> {text(closedSummary.best_txt)}</span><span><b>En zayıf</b> {text(closedSummary.worst_txt)}</span></div></div><ul>{closedSummary.yorumlar.map((item, index) => <li key={index}>{item}</li>)}</ul></section>}
  </>;
}

export function PerformanceScorecardView({ scorecard }: { scorecard: PerformanceScorecardResponse }) {
  const scoreSummaryColumns = useMemo(() => Object.keys(scorecard.ozet[0] ?? {}), [scorecard]);
  const scoreDetailColumns = useMemo(() => Object.keys(scorecard.detay[0] ?? {}), [scorecard]);

  return <>
    <section className="performance-scorecard-heading"><div><p className="eyebrow">IZFIN PERFORMANS KARNESİ</p><h2>{scorecard.gun} işlem günlük sinyal ölçümü</h2></div><span>{scorecard.kayit_adedi} kayıt</span></section>
    <section className="performance-overview-grid">
      <article className="performance-panel performance-summary-card"><span>KAYIT HAVUZU</span><strong>{scorecard.kayit_adedi}</strong><small>{scorecard.gun} işlem günlük pencere</small></article>
      <article className={`performance-panel performance-summary-card${scorecard.kucuk_orneklem ? " is-warning" : ""}`}><span>ÖRNEKLEM</span><strong>{scorecard.kucuk_orneklem ? "SINIRLI" : "YETERLİ"}</strong><small>{scorecard.kucuk_orneklem ? "Temkinli yorumla" : "Karne değerlendirmeye uygun"}</small></article>
      <article className="performance-panel performance-summary-card"><span>DÖNEM</span><strong>{scorecard.gun}G</strong><small>Sinyal sonrası işlem günü</small></article>
    </section>

    {scorecard.kucuk_orneklem && <section className="performance-panel performance-sample-warning" role="note"><strong>Örneklem henüz küçük</strong><p>Başarı oranlarını karar vermek için kullanmadan önce en az 30, tercihen 100+ bağımsız sinyal biriktirmek daha sağlıklıdır.</p></section>}

    {scorecard.bos_mesaj ? <section className="performance-panel performance-empty-state"><p>{scorecard.bos_mesaj}</p><a href="/scan">Yeni tarama başlat →</a></section> : <section className="performance-metric-grid">{scorecard.metrikler.map((metric, index) => <article className="performance-panel performance-metric-card" key={`${metric.label}-${index}`}><span>{metric.label}</span><strong>{metric.value}</strong><i /></article>)}</section>}

    <section className="performance-lower-grid">
      <article className="performance-panel performance-context-card"><p className="eyebrow">KARNE OKUMASI</p><h2>Sonuç kalitesi</h2><p>{scorecard.kucuk_orneklem ? "Oranlar yeni sonuçlarla hızlı değişebilir; tek başına başarı kanıtı sayılmaz." : "Örneklem daha dengeli bir toplu değerlendirme sunuyor."}</p><div className="performance-quality-bar"><span style={{ width: `${Math.min(100, Math.max(8, scorecard.kayit_adedi))}%` }} /></div>{scorecard.medyan_alfa_mesaji && <small>{scorecard.medyan_alfa_mesaji}</small>}</article>
      <article className="performance-panel performance-context-card"><p className="eyebrow">ÖLÇÜM KAPSAMI</p><h2>Karne neyi ölçüyor?</h2><p><b>Ölçüm kapsamı</b> · 20G / 60G / 120G seçimi yalnızca sinyal sonrası ölçüm ufkunu değiştirir. Aktif ve kapanmış pozisyon tabloları tüm kayıtlı dönemleri gösterir.</p><p>ABD hisseleri NASDAQ, BIST hisseleri BIST100 ile karşılaştırılır; “Benchmark Üstü” göreceli performansı ifade eder.</p></article>
    </section>

    {scorecard.ozet.length > 0 && <section className="performance-panel performance-table-card"><div className="performance-section-title"><div><p className="eyebrow">VARLIK BAZLI KARNE</p><h2>Hangi hissede nasıl sonuç verdi?</h2></div><span>{scorecard.ozet.length} varlık</span></div><div className="performance-table-scroll"><table className="performance-table"><thead><tr>{scoreSummaryColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{scorecard.ozet.map((row, index) => <tr key={rowKey(row, index)}>{scoreSummaryColumns.map((column) => <td className={column.includes("Getiri") || column.includes("Farkı") ? pctClass(row[column]) : ""} key={column}>{scorecardValue(column, row[column])}</td>)}</tr>)}</tbody></table></div></section>}

    {scorecard.detay.length > 0 && <details className="performance-panel performance-score-detail"><summary>Sinyal bazlı ölçüm geçmişini aç <span>{scorecard.detay.length} kayıt</span></summary><p>Her satır, seçili ufku tamamlayan mevcut bir IZFIN sinyalinin dondurulmuş sonucudur.</p><div className="performance-table-scroll"><table className="performance-table"><thead><tr>{scoreDetailColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{scorecard.detay.map((row, index) => <tr key={rowKey(row, index)}>{scoreDetailColumns.map((column) => <td className={column.includes("Getiri") || column.includes("Farkı") ? pctClass(row[column]) : ""} key={column}>{scorecardValue(column, row[column])}</td>)}</tr>)}</tbody></table></div></details>}

    <section className="performance-definition-grid" aria-label="Performans KPI tanımları"><article className="performance-panel"><b>Pozitif Sonuç</b><span>Seçili işlem günü sonunda getirisi sıfırın üzerinde kalan ölçümlerin oranı.</span></article><article className="performance-panel"><b>Medyan Getiri</b><span>Uç kazanç ve kayıpların etkisini azaltan ortanca sinyal getirisi.</span></article><article className="performance-panel"><b>Benchmark Üstü</b><span>Aynı ufukta ilgili piyasa referansından daha iyi sonuç veren sinyallerin oranı.</span></article></section>
  </>;
}
