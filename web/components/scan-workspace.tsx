"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";
import { MarketCenterPanel } from "./market-center";
import { stockDetailHref } from "../lib/stock-detail-route";

type ScanSummary = { sonuclar: Array<Record<string, unknown>>; basarisiz_taramalar: string[]; boga_sayisi: number; alim_firsati: number };
type ScanJob = { job_id: string; status: "queued" | "running" | "completed" | "failed"; stage: string; completed: number; total: number; result?: ScanSummary; error?: string };
type ScanHistoryItem = Pick<ScanJob, "job_id" | "status" | "stage" | "completed" | "total"> & { tickers: string[]; created_at?: string | null };
type ScanHistory = { jobs: ScanHistoryItem[] };
type ResultFilter = "all" | "buy" | "bullish";

const starterSets = [
  { label: "Banka", symbols: "AKBNK.IS, GARAN.IS, YKBNK.IS" },
  { label: "Likidite", symbols: "THYAO.IS, ASELS.IS, TUPRS.IS" },
];

function normalizeTickers(value: string): string[] {
  return [...new Set(value.split(/[\s,]+/).map((item) => item.trim().toUpperCase()).filter(Boolean))];
}

function resultDecision(result: Record<string, unknown>) {
  return String(result.Karar ?? result.decision ?? "Analiz tamamlandı");
}

function isBuy(result: Record<string, unknown>) {
  return resultDecision(result).toLocaleUpperCase("tr-TR").includes("ALIM");
}

function isBullish(result: Record<string, unknown>) {
  const decision = resultDecision(result).toLocaleUpperCase("tr-TR");
  return decision.includes("BOĞA") || decision.includes("ALIM");
}

function formatHistoryTime(value?: string | null) {
  if (!value) return "Yakın zamanda";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Yakın zamanda" : new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function ScanWorkspace() {
  const { user, getIdToken } = useIzfinAuth();
  const [symbols, setSymbols] = useState("THYAO.IS, AKBNK.IS");
  const [job, setJob] = useState<ScanJob | null>(null);
  const [history, setHistory] = useState<ScanHistoryItem[]>([]);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [activeFilter, setActiveFilter] = useState<ResultFilter>("all");
  const tickers = useMemo(() => normalizeTickers(symbols), [symbols]);

  const loadHistory = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getIdToken();
      if (!token) return;
      const response = await izfinApiFetch<ScanHistory>("/api/v1/scan/jobs", token);
      setHistory(response.jobs);
      setHistoryError("");
    } catch { setHistoryError("Tarama geçmişi şu anda alınamıyor."); }
  }, [getIdToken, user]);

  useEffect(() => { void loadHistory(); }, [loadHistory]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timeout = window.setTimeout(() => void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const updated = await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${job.job_id}`, token);
        setJob(updated);
        if (["completed", "failed"].includes(updated.status)) void loadHistory();
      } catch { setError("Tarama durumu güncellenemedi."); }
    })(), 1000);
    return () => window.clearTimeout(timeout);
  }, [getIdToken, job, loadHistory]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setActiveFilter("all");
    if (!tickers.length) { setError("En az bir BIST sembolü girin."); return; }
    try {
      const token = await getIdToken();
      if (!token) return;
      setJob(await izfinApiFetch<ScanJob>("/api/v1/scan/jobs", token, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers }),
      }));
      void loadHistory();
    } catch { setError("Tarama başlatılamadı. Lütfen tekrar deneyin."); }
  }

  async function openHistoryJob(jobId: string) {
    setError("");
    try {
      const token = await getIdToken();
      if (!token) return;
      setJob(await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${jobId}`, token));
      document.getElementById("scan-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch { setError("Bu tarama sonucu artık açılamıyor."); }
  }

  if (!user) return null;
  const running = job?.status === "queued" || job?.status === "running";
  return <section className="scan-workspace" aria-label="Akıllı tarama">
    <div className="section-heading"><div><p className="eyebrow">AKILLI TARAMA</p><h2>Tarama çalışma alanı</h2></div><span className="section-index">02</span></div>
    <p className="scan-intro">Kendi BIST sembol grubunu çalıştır; sonuçları karar yönüne göre daralt ve geçmişteki taramayı yeniden aç.</p>
    <form className="scan-form" onSubmit={submit}><label>Semboller<input value={symbols} onChange={(event) => setSymbols(event.target.value)} aria-describedby="scan-symbol-count" /></label><button disabled={running} type="submit">{running ? "Tarama sürüyor…" : `${tickers.length} sembolü tara`}</button></form>
    <div className="scan-config" aria-label="Tarama ayarları"><span id="scan-symbol-count">Aktif evren: <b>{tickers.length}</b> sembol</span><div className="scan-presets"><span>Hızlı başlangıç:</span>{starterSets.map((set) => <button key={set.label} type="button" onClick={() => setSymbols(set.symbols)}>{set.label}</button>)}<button type="button" onClick={() => setSymbols("")}>Temizle</button></div></div>
    {error && <p role="alert">{error}</p>}
    {job && <p className="job-progress" aria-live="polite">Durum: <strong>{job.stage}</strong> · {job.completed}/{job.total}</p>}
    {job?.status === "failed" && <p role="alert">{job.error ?? "Tarama tamamlanamadı."}</p>}
    {job?.status === "completed" && job.result && <><ScanResult jobId={job.job_id} summary={job.result} activeFilter={activeFilter} onFilterChange={setActiveFilter} /><MarketCenterPanel jobId={job.job_id} /></>}
    <aside className="scan-history" aria-label="Tarama geçmişi">
      <div className="scan-history-head"><div><p className="eyebrow">KAYITLI TARAMALAR</p><h3>Tarama geçmişi</h3></div><button type="button" onClick={() => void loadHistory()}>Yenile</button></div>
      {historyError ? <p role="alert">{historyError}</p> : history.length === 0 ? <p className="scan-empty">Henüz kaydedilmiş bir taraman yok. İlk sonucu burada yeniden açabilirsin.</p> : <div className="scan-history-list">{history.map((item) => <button key={item.job_id} type="button" onClick={() => void openHistoryJob(item.job_id)}><span><b>{item.tickers.join(", ") || "Sembol grubu"}</b><small>{formatHistoryTime(item.created_at)} · {item.total} sembol</small></span><span className={`scan-history-status is-${item.status}`}>{item.status === "completed" ? "Hazır" : item.status === "failed" ? "Tamamlanamadı" : "Sürüyor"}</span><em>Son taramayı aç →</em></button>)}</div>}
    </aside>
  </section>;
}

function ScanResult({ jobId, summary, activeFilter, onFilterChange }: Readonly<{ jobId: string; summary: ScanSummary; activeFilter: ResultFilter; onFilterChange: (filter: ResultFilter) => void }>) {
  const results = summary.sonuclar.filter((result) => activeFilter === "all" || (activeFilter === "buy" ? isBuy(result) : isBullish(result)));
  return <div id="scan-result" className="scan-result scan-summary" aria-label="Tarama sonucu"><div className="scan-result-header"><div><p className="eyebrow">TARAMA SONUCU</p><h3>Karar özeti hazır</h3></div><span>{summary.sonuclar.length} sembol</span></div><div className="scan-metrics"><span><b>{summary.sonuclar.length}</b> sonuç</span><span><b>{summary.boga_sayisi}</b> boğa</span><span><b>{summary.alim_firsati}</b> alım fırsatı</span></div>
    <div className="result-filter" aria-label="Sonuç görünümü"><span>Sonuç görünümü</span><button className={activeFilter === "all" ? "active" : ""} type="button" onClick={() => onFilterChange("all")}>Tümü</button><button className={activeFilter === "buy" ? "active" : ""} type="button" onClick={() => onFilterChange("buy")}>Alım</button><button className={activeFilter === "bullish" ? "active" : ""} type="button" onClick={() => onFilterChange("bullish")}>Boğa</button></div>
    {summary.basarisiz_taramalar.length > 0 && <p>Atlananlar: {summary.basarisiz_taramalar.join(", ")}</p>}
    {summary.sonuclar.length === 0 ? <p className="scan-empty">Tarama tamamlandı ancak gösterilecek sonuç bulunamadı.</p> : results.length === 0 ? <p className="scan-empty">Bu görünümle eşleşen sonuç yok. Tüm sonuçlara dönmeyi deneyin.</p> : <div className="result-list">{results.slice(0, 12).map((result, index) => {
      const ticker = String(result.Varlık ?? result.ticker ?? "").trim().toUpperCase(); const decision = resultDecision(result); const key = `${ticker || "symbol"}-${index}`;
      return ticker ? <a href={stockDetailHref(jobId, ticker)} key={key}><strong>{ticker}</strong><span>{decision} <b>Detayı aç →</b></span></a> : <div key={key}><strong>Sembol</strong><span>{decision}</span></div>;
    })}</div>}
  </div>;
}
