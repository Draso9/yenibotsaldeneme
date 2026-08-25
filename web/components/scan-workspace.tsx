"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";

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
    <p className="eyebrow">AKILLI TARAMA</p><h2>Tarama başlat</h2>
    <form className="scan-form" onSubmit={submit}><label>Semboller<input value={symbols} onChange={(event) => setSymbols(event.target.value)} /></label><button disabled={running} type="submit">{running ? "Tarama sürüyor…" : `${tickers.length} sembolü tara`}</button></form>
    {error && <p role="alert">{error}</p>}
    {job && <p className="job-progress">Durum: <strong>{job.stage}</strong> · {job.completed}/{job.total}</p>}
    {job?.status === "failed" && <p role="alert">{job.error ?? "Tarama tamamlanamadı."}</p>}
    {job?.result && <ScanResult summary={job.result} />}
  </section>;
}

function ScanResult({ summary }: Readonly<{ summary: ScanSummary }>) {
  return <div className="scan-result"><div className="scan-metrics"><span><b>{summary.sonuclar.length}</b> sonuç</span><span><b>{summary.boga_sayisi}</b> boğa</span><span><b>{summary.alim_firsati}</b> alım fırsatı</span></div>
    {summary.basarisiz_taramalar.length > 0 && <p>Atlananlar: {summary.basarisiz_taramalar.join(", ")}</p>}
    <div className="result-list">{summary.sonuclar.slice(0, 12).map((result, index) => <div key={`${String(result.Varlık ?? result.ticker ?? index)}-${index}`}><strong>{String(result.Varlık ?? result.ticker ?? "Sembol")}</strong><span>{String(result.Karar ?? result.decision ?? "Analiz tamamlandı")}</span></div>)}</div>
  </div>;
}
