"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";
import { MarketCenterPanel } from "./market-center";
import { stockDetailHref } from "../lib/stock-detail-route";

type ScanSummary = { sonuclar: Array<Record<string, unknown>>; basarisiz_taramalar: string[]; boga_sayisi: number; alim_firsati: number };
type ScanJob = { job_id: string; status: "queued" | "running" | "completed" | "failed"; stage: string; completed: number; total: number; result?: ScanSummary; error?: string };

function normalizeTickers(value: string): string[] {
  return [...new Set(value.split(/[\s,]+/).map((item) => item.trim().toUpperCase()).filter(Boolean))];
}

export function ScanWorkspace() {
  const { user, getIdToken } = useIzfinAuth();
  const [symbols, setSymbols] = useState("THYAO.IS, AKBNK.IS");
  const [job, setJob] = useState<ScanJob | null>(null);
  const [error, setError] = useState("");
  const tickers = useMemo(() => normalizeTickers(symbols), [symbols]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timeout = window.setTimeout(() => void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        setJob(await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${job.job_id}`, token));
      } catch { setError("Tarama durumu güncellenemedi."); }
    })(), 1000);
    return () => window.clearTimeout(timeout);
  }, [getIdToken, job]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!tickers.length) { setError("En az bir BIST sembolü girin."); return; }
    try {
      const token = await getIdToken();
      if (!token) return;
      setJob(await izfinApiFetch<ScanJob>("/api/v1/scan/jobs", token, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers }),
      }));
    } catch { setError("Tarama başlatılamadı. Lütfen tekrar deneyin."); }
  }

  if (!user) return null;
  const running = job?.status === "queued" || job?.status === "running";
  return <section className="scan-workspace" aria-label="Akıllı tarama">
    <div className="section-heading">
      <div><p className="eyebrow">AKILLI TARAMA</p><h2>Tarama çalışma alanı</h2></div>
      <span className="section-index">02</span>
    </div>
    <form className="scan-form" onSubmit={submit}><label>Semboller<input value={symbols} onChange={(event) => setSymbols(event.target.value)} /></label><button disabled={running} type="submit">{running ? "Tarama sürüyor…" : `${tickers.length} sembolü tara`}</button></form>
    {error && <p role="alert">{error}</p>}
    {job && <p className="job-progress" aria-live="polite">Durum: <strong>{job.stage}</strong> · {job.completed}/{job.total}</p>}
    {job?.status === "failed" && <p role="alert">{job.error ?? "Tarama tamamlanamadı."}</p>}
    {job?.status === "completed" && job.result && <>
      <ScanResult jobId={job.job_id} summary={job.result} />
      <MarketCenterPanel jobId={job.job_id} />
    </>}
  </section>;
}

function ScanResult({ jobId, summary }: Readonly<{ jobId: string; summary: ScanSummary }>) {
  return <div className="scan-result scan-summary" aria-label="Tarama sonucu"><div className="scan-result-header"><div><p className="eyebrow">TARAMA SONUCU</p><h3>Karar özeti hazır</h3></div><span>{summary.sonuclar.length} sembol</span></div><div className="scan-metrics"><span><b>{summary.sonuclar.length}</b> sonuç</span><span><b>{summary.boga_sayisi}</b> boğa</span><span><b>{summary.alim_firsati}</b> alım fırsatı</span></div>
    {summary.basarisiz_taramalar.length > 0 && <p>Atlananlar: {summary.basarisiz_taramalar.join(", ")}</p>}
    {summary.sonuclar.length === 0 ? <p className="scan-empty">Tarama tamamlandı ancak gösterilecek sonuç bulunamadı.</p> : <div className="result-list">{summary.sonuclar.slice(0, 12).map((result, index) => {
      const ticker = String(result.Varlık ?? result.ticker ?? "").trim().toUpperCase();
      const decision = String(result.Karar ?? result.decision ?? "Analiz tamamlandı");
      const key = `${ticker || "symbol"}-${index}`;
      return ticker ? <a href={stockDetailHref(jobId, ticker)} key={key}><strong>{ticker}</strong><span>{decision} <b>Detayı aç →</b></span></a> : <div key={key}><strong>Sembol</strong><span>{decision}</span></div>;
    })}</div>}
  </div>;
}
