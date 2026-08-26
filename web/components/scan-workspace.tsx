"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";
import { MarketCenterPanel } from "./market-center";
import { stockDetailHref } from "../lib/stock-detail-route";

type ScanResultRow = Record<string, unknown>;
type ScanSummary = { sonuclar: ScanResultRow[]; basarisiz_taramalar: string[]; boga_sayisi: number; alim_firsati: number };
type ScanJob = { job_id: string; status: "queued" | "running" | "completed" | "failed"; stage: string; completed: number; total: number; result?: ScanSummary; error?: string };
type ScanHistoryItem = Pick<ScanJob, "job_id" | "status" | "stage" | "completed" | "total"> & { tickers: string[]; created_at?: string | null };
type Watchlist = { tickers: string[]; recovered: boolean };
type Profiles = { profiles: Record<string, string[]> };
type Universe = { profil: string; tickers: string[]; chipleri_goster: boolean; secim_ozeti: { varlik_adedi: number } };
type SymbolSuggestion = { symbol: string; name: string; exchange: string; quote_type: string };
type ResultFilter = "Tümü" | "AL Sinyalleri" | "Uzun Vadeli Adaylar" | "Teyit Bekleyenler";
type SortDirection = "asc" | "desc";

const resultColumns = ["Varlık", "Fiyat", "Nihai Sinyal", "Gelişmiş Skor", "Güven", "🎯 Giriş Kalitesi", "MTF Uyum", "Risk", "Para Akışı", "PEG / Değerleme", "Seans Dışı"];
const filters: ResultFilter[] = ["Tümü", "AL Sinyalleri", "Uzun Vadeli Adaylar", "Teyit Bekleyenler"];

function normalizeTickers(values: string[]): string[] { return [...new Set(values.map((item) => item.trim().toUpperCase()).filter(Boolean))]; }
function signal(row: ScanResultRow) { return String(row["Nihai Sinyal"] ?? "Analiz tamamlandı"); }
function ticker(row: ScanResultRow) { return String(row.Varlık ?? row.ticker ?? "").trim().toUpperCase(); }
function isBuy(row: ScanResultRow) { const value = signal(row).toLocaleUpperCase("tr-TR"); return value.includes("AL") && !value.includes("KÂR AL") && !value.includes("KAR AL"); }
function isConfirmation(row: ScanResultRow) { const value = signal(row).toLocaleUpperCase("tr-TR"); return ["TEYİT", "İZLE", "BEKLE"].some((term) => value.includes(term)); }
function isLongTerm(row: ScanResultRow) { return String(row["Teknik Profil"] ?? "").toLocaleUpperCase("tr-TR").includes("UZUN VADELİ ADAY"); }
function formatHistoryTime(value?: string | null) { if (!value) return "Yakın zamanda"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "Yakın zamanda" : new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(date); }
function sortValue(value: unknown): number | string {
  const raw = String(value ?? ""); const risk = { "ÇOK YÜKSEK": 4, YÜKSEK: 3, ORTA: 2, DÜŞÜK: 1 };
  const riskValue = Object.entries(risk).find(([label]) => raw.toLocaleUpperCase("tr-TR").includes(label)); if (riskValue) return riskValue[1];
  const numeric = raw.replace(",", ".").match(/[-+]?\d+(?:\.\d+)?/); return numeric ? Number(numeric[0]) : raw.toLocaleLowerCase("tr-TR");
}

export function ScanWorkspace() {
  const { user, getIdToken } = useIzfinAuth();
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [profiles, setProfiles] = useState<Record<string, string[]>>({});
  const [profile, setProfile] = useState("Kendi Listem");
  const [universe, setUniverse] = useState<Universe | null>(null);
  const [symbolDraft, setSymbolDraft] = useState(""); const [symbolSearch, setSymbolSearch] = useState(""); const [suggestions, setSuggestions] = useState<SymbolSuggestion[]>([]); const [selectedSuggestion, setSelectedSuggestion] = useState<SymbolSuggestion | null>(null); const [searchingSymbols, setSearchingSymbols] = useState(false); const [searchedQuery, setSearchedQuery] = useState(""); const [job, setJob] = useState<ScanJob | null>(null);
  const [history, setHistory] = useState<ScanHistoryItem[]>([]); const [error, setError] = useState(""); const [historyError, setHistoryError] = useState("");
  const [activeFilter, setActiveFilter] = useState<ResultFilter>("Tümü");
  const [guideDismissed, setGuideDismissed] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!user) return;
    try { const token = await getIdToken(); if (!token) return; setHistory((await izfinApiFetch<{ jobs: ScanHistoryItem[] }>("/api/v1/scan/jobs", token)).jobs); setHistoryError(""); }
    catch { setHistoryError("Tarama geçmişi şu anda alınamıyor."); }
  }, [getIdToken, user]);
  const loadWorkspace = useCallback(async () => {
    if (!user) return;
    try { const token = await getIdToken(); if (!token) return; const [list, availableProfiles] = await Promise.all([izfinApiFetch<Watchlist>("/api/v1/watchlist", token), izfinApiFetch<Profiles>("/api/v1/scan/profiles", token)]); setWatchlist(list); setProfiles(availableProfiles.profiles); setError(""); }
    catch { setError("Kişisel liste veya tarama profilleri şu anda yüklenemedi."); }
  }, [getIdToken, user]);
  const loadUniverse = useCallback(async () => {
    if (!user || !watchlist) return;
    try { const token = await getIdToken(); if (!token) return; setUniverse(await izfinApiFetch<Universe>("/api/v1/scan/universe", token, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profil: profile, kisisel_liste: watchlist.tickers, preset_options: profiles }) })); }
    catch { setError("Tarama evreni hazırlanamadı."); }
  }, [getIdToken, profile, profiles, user, watchlist]);
  useEffect(() => { void Promise.all([loadWorkspace(), loadHistory()]); }, [loadHistory, loadWorkspace]);
  useEffect(() => { if (user) setGuideDismissed(window.localStorage.getItem(`izfin:first-scan-guide:${user.uid}`) === "done"); }, [user]);
  useEffect(() => { void loadUniverse(); }, [loadUniverse]);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timeout = window.setTimeout(() => void (async () => { try { const token = await getIdToken(); if (!token) return; const updated = await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${job.job_id}`, token); setJob(updated); if (["completed", "failed"].includes(updated.status)) void loadHistory(); } catch { setError("Tarama durumu güncellenemedi."); } })(), 1000);
    return () => window.clearTimeout(timeout);
  }, [getIdToken, job, loadHistory]);

  async function replaceWatchlist(nextTickers: string[]) {
    const normalized = normalizeTickers(nextTickers); if (!normalized.length) { setError("Kişisel listede en az bir sembol kalmalı."); return; }
    try { const token = await getIdToken(); if (!token) return; const saved = await izfinApiFetch<Watchlist>("/api/v1/watchlist", token, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers: normalized }) }); setWatchlist(saved); setProfile("Kendi Listem"); setSymbolDraft(""); setError(""); }
    catch { setError("Kişisel liste kaydedilemedi."); }
  }
  function addSymbol(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!symbolDraft.trim()) { setError("Eklenecek sembolü yazın."); return; } void replaceWatchlist([...(watchlist?.tickers ?? []), ...symbolDraft.split(/[\s,]+/)]); }
  async function findSymbols(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const query = symbolSearch.trim(); setSelectedSuggestion(null); setSuggestions([]); setSearchedQuery(query);
    if (!query) { setError("Aramak istediğin hisseyi veya şirketi yazın."); return; }
    try { const token = await getIdToken(); if (!token) return; setSearchingSymbols(true); setError(""); const result = await izfinApiFetch<{ suggestions: SymbolSuggestion[] }>(`/api/v1/scan/symbols?q=${encodeURIComponent(query)}`, token); setSuggestions(result.suggestions); }
    catch { setError("Sembol araması şu anda alınamıyor."); } finally { setSearchingSymbols(false); }
  }
  function addSelectedSuggestion() { if (selectedSuggestion) void replaceWatchlist([...(watchlist?.tickers ?? []), selectedSuggestion.symbol]); }
  function removeSymbol(value: string) { void replaceWatchlist((watchlist?.tickers ?? []).filter((item) => item !== value)); }
  async function submit() {
    setError(""); setActiveFilter("Tümü"); if (!universe?.tickers.length) { setError("Taramayı başlatmadan önce en az bir varlık seçin."); return; }
    try { const token = await getIdToken(); if (!token) return; setJob(await izfinApiFetch<ScanJob>("/api/v1/scan/jobs", token, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers: universe.tickers }) })); void loadHistory(); }
    catch { setError("Tarama başlatılamadı. Lütfen tekrar deneyin."); }
  }
  async function openHistoryJob(jobId: string) { try { const token = await getIdToken(); if (!token) return; setJob(await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${jobId}`, token)); document.getElementById("scan-result")?.scrollIntoView({ behavior: "smooth", block: "start" }); } catch { setError("Bu tarama sonucu artık açılamıyor."); } }
  function dismissGuide() { if (user) window.localStorage.setItem(`izfin:first-scan-guide:${user.uid}`, "done"); setGuideDismissed(true); }

  if (!user) return null;
  const running = job?.status === "queued" || job?.status === "running";
  return <section className="scan-workspace" aria-label="Akıllı tarama">
    <div className="section-heading"><div><p className="eyebrow">IZFIN SCANNER</p><h2>Akıllı Tarama Merkezi</h2></div><span className="section-index">SIGNATURE SCAN</span></div>
    <p className="scan-intro">Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p>
    {!guideDismissed && !job && history.length === 0 && watchlist && <FirstScanGuide tickerCount={watchlist.tickers.length} onDismiss={dismissGuide} />}
    <div id="scan-control" className="scan-control-grid"><section className="scan-control-card"><p className="eyebrow">KİŞİSEL LİSTE</p><h3>Kişisel Listemi Yönet</h3><p>Kalıcı takip listen, Kendi Listem profilinin tarama evrenidir.</p>{watchlist ? <><form className="symbol-search-form" onSubmit={findSymbols}><label>Hisse / şirket ara<input value={symbolSearch} onChange={(event) => setSymbolSearch(event.target.value)} placeholder="Örn. APP, Apple, NVDA, THYAO..." /></label><button type="submit" disabled={searchingSymbols}>{searchingSymbols ? "Aranıyor…" : "Ara"}</button></form>{searchedQuery && !searchingSymbols && <p className="symbol-search-meta">{suggestions.length ? `🔎 ${suggestions.length} eşleşme bulundu` : "Bu aramayla eşleşen piyasa sembolü bulunamadı."}</p>}{suggestions.length > 0 && <div className="symbol-suggestions" aria-label="Arama sonuçları">{suggestions.map((item) => <button className={selectedSuggestion?.symbol === item.symbol ? "active" : ""} key={`${item.symbol}-${item.exchange}`} type="button" onClick={() => setSelectedSuggestion(item)}><b>{item.symbol}</b><span>{item.name || "Piyasa sembolü"}</span><small>{[item.exchange, item.quote_type].filter(Boolean).join(" · ")}</small></button>)}</div>}{selectedSuggestion && <div className="symbol-selection-preview"><div><b>{selectedSuggestion.symbol}</b><span>{selectedSuggestion.name || "Piyasa sembolü"}</span></div><button type="button" disabled={watchlist.tickers.includes(selectedSuggestion.symbol)} onClick={addSelectedSuggestion}>{watchlist.tickers.includes(selectedSuggestion.symbol) ? "Listende" : `＋ ${selectedSuggestion.symbol} Listeme Ekle`}</button></div>}<div className="ticker-list">{watchlist.tickers.map((item) => <button key={item} type="button" onClick={() => removeSymbol(item)} aria-label={`${item} sembolünü listeden sil`}>{item} <span>×</span></button>)}</div><form className="watchlist-form scan-watchlist-form" onSubmit={addSymbol}><label>Sembol ekle<input value={symbolDraft} onChange={(event) => setSymbolDraft(event.target.value)} placeholder="örn. THYAO.IS" /></label><button type="submit">Manuel ekle</button></form></> : <p className="scan-empty">Kişisel liste yükleniyor…</p>}</section>
      <section className="scan-control-card"><p className="eyebrow">TARAMA EVRENİ</p><h3>Evreni hazırla ve taramayı başlat</h3><label className="scan-profile-label">Profil<select value={profile} onChange={(event) => setProfile(event.target.value)}><option>Kendi Listem</option>{Object.keys(profiles).map((name) => <option key={name}>{name}</option>)}</select></label><div className="active-universe"><span>AKTİF TARAMA EVRENİ</span><strong>{universe?.profil ?? profile}</strong><b>{universe?.secim_ozeti.varlik_adedi ?? 0} VARLIK</b></div>{universe?.chipleri_goster && <div className="scan-universe-chips">{universe.tickers.map((item) => <span key={item}>{item}</span>)}</div>}<button className="scan-launch" disabled={running || !universe?.tickers.length} type="button" onClick={() => void submit()}>{running ? "Tarama sürüyor…" : "AKILLI TARAMAYI BAŞLAT"}</button><small>Tarama; IZFIN skor, güven, giriş kalitesi, MTF, risk ve para akışı katmanlarını birlikte çalıştırır.</small></section></div>
    {error && <p role="alert">{error}</p>}{job && <p className="job-progress" aria-live="polite">Durum: <strong>{job.stage}</strong> · {job.completed}/{job.total}</p>}{job?.status === "failed" && <p role="alert">{job.error ?? "Tarama tamamlanamadı."}</p>}{job?.status === "completed" && job.result && <><ScanResult jobId={job.job_id} summary={job.result} activeFilter={activeFilter} onFilterChange={setActiveFilter} /><MarketCenterPanel jobId={job.job_id} /></>}
    <aside className="scan-history" aria-label="Tarama geçmişi"><div className="scan-history-head"><div><p className="eyebrow">KAYITLI TARAMALAR</p><h3>Tarama geçmişi</h3></div><button type="button" onClick={() => void loadHistory()}>Yenile</button></div>{historyError ? <p role="alert">{historyError}</p> : history.length === 0 ? <p className="scan-empty">Henüz kaydedilmiş bir taraman yok. İlk sonucu burada yeniden açabilirsin.</p> : <div className="scan-history-list">{history.map((item) => <button key={item.job_id} type="button" onClick={() => void openHistoryJob(item.job_id)}><span><b>{item.tickers.join(", ") || "Sembol grubu"}</b><small>{formatHistoryTime(item.created_at)} · {item.total} sembol</small></span><span className={`scan-history-status is-${item.status}`}>{item.status === "completed" ? "Hazır" : item.status === "failed" ? "Tamamlanamadı" : "Sürüyor"}</span><em>Son taramayı aç →</em></button>)}</div>}</aside>
  </section>;
}

function FirstScanGuide({ tickerCount, onDismiss }: Readonly<{ tickerCount: number; onDismiss: () => void }>) {
  return <section className="first-scan-guide" aria-label="İlk tarama rehberi"><div className="first-scan-head"><div><p className="eyebrow">İLK TARAMA REHBERİ</p><h3>Bir sonucu 30 saniyede değerlendir</h3><p>Önce merkezi kararı, sonra kararın güvenini ve risk planını okuyun.</p></div><button type="button" onClick={onDismiss}>Rehberi kapat</button></div><div className="first-scan-steps"><article><span>1 · TARAMA</span><b>Evreni seçin</b><small>{tickerCount} kayıtlı varlığın var. Kendi Listem veya hazır bir profil ile başla.</small></article><article><span>2 · KARAR</span><b>Aksiyonu okuyun</b><small>İlk referansın puan değil, Merkezi Karar olsun.</small></article><article><span>3 · TEYİT</span><b>Nedeni kontrol edin</b><small>Güven, giriş kalitesi ve MTF uyumunu birlikte değerlendir.</small></article><article><span>4 · PLAN</span><b>Riski belirleyin</b><small>Destek, stop ve hedefleri işlemden önce planla.</small></article></div><div className="first-scan-note"><b>Ana kural:</b> Skorlar karar vermez; kararı açıklar. İşlem yönünü trend, momentum, para akışı, zamanlama ve risk filtrelerini birlikte değerlendiren Merkezi Karar belirler.<a href="#scan-control">Tarama kontrolüne git →</a></div></section>;
}

function ScanResult({ jobId, summary, activeFilter, onFilterChange }: Readonly<{ jobId: string; summary: ScanSummary; activeFilter: ResultFilter; onFilterChange: (filter: ResultFilter) => void }>) {
  const [sort, setSort] = useState<{ column: string; direction: SortDirection }>({ column: "Gelişmiş Skor", direction: "desc" });
  const [focusMode, setFocusMode] = useState(false);
  const results = useMemo(() => summary.sonuclar.filter((row) => activeFilter === "Tümü" || (activeFilter === "AL Sinyalleri" ? isBuy(row) : activeFilter === "Uzun Vadeli Adaylar" ? isLongTerm(row) : isConfirmation(row))).sort((left, right) => { const a = sortValue(left[sort.column]); const b = sortValue(right[sort.column]); const comparison = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "tr"); return sort.direction === "asc" ? comparison : -comparison; }), [activeFilter, sort, summary.sonuclar]);
  function updateSort(column: string) { setSort((current) => ({ column, direction: current.column === column && current.direction === "desc" ? "asc" : "desc" })); }
  return <div id="scan-result" className={`scan-result scan-summary${focusMode ? " is-focus" : ""}`} aria-label="Tarama sonucu"><div className="scan-result-header"><div><p className="eyebrow">TARAMA SONUCU</p><h3>Akıllı Tarama Sonuçları</h3></div><div className="scan-result-actions"><button type="button" onClick={() => setFocusMode((value) => !value)}>{focusMode ? "↙ Geniş Görünümden Çık" : "⛶ Tabloyu Genişlet"}</button><span>{summary.sonuclar.length} sembol</span></div></div>{focusMode && <div className="scan-focus-meta"><b>Geniş sonuç görünümü</b><span>{results.length} sonuç · {activeFilter} filtresi · bir sütuna dokunarak sırala</span></div>}<div className="scan-metrics"><span><b>{summary.sonuclar.length}</b>Taranan Varlık</span><span><b>{summary.boga_sayisi}</b>Boğa Trendinde (200G)</span><span><b>{summary.alim_firsati}</b>Alım Fırsatları & Kırılımlar</span></div><div className="result-filter" aria-label="Gösterilecek sonuçlar"><span>Gösterilecek sonuçlar</span>{filters.map((filter) => <button className={activeFilter === filter ? "active" : ""} key={filter} type="button" onClick={() => onFilterChange(filter)}>{filter}</button>)}</div><p className="scan-filter-summary">{results.length} sonuç gösteriliyor · Filtre: {activeFilter}</p>{summary.basarisiz_taramalar.length > 0 && <p>Veri/hesaplama sorunu nedeniyle es geçilen varlıklar: {summary.basarisiz_taramalar.join(", ")}</p>}{summary.sonuclar.length === 0 ? <p className="scan-empty">Veriler çekilemedi. Farklı bir profil veya varlık grubu seçip tekrar deneyin.</p> : results.length === 0 ? <p className="scan-empty">Bu filtreye uyan sonuç yok. Diğer filtrelerden birini seçebilir veya taramayı daha sonra yenileyebilirsin.</p> : <div className="scan-result-table-wrap"><table className="scan-result-table"><thead><tr>{resultColumns.map((column) => <th key={column}><button type="button" onClick={() => updateSort(column)}>{column} <span>{sort.column === column ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span></button></th>)}</tr></thead><tbody>{results.map((row, index) => { const symbol = ticker(row); return <tr key={`${symbol}-${index}`}>{resultColumns.map((column) => <td key={column} className={column === "Nihai Sinyal" ? "scan-signal-cell" : ""}>{column === "Varlık" && symbol ? <a href={stockDetailHref(jobId, symbol)}>{symbol}</a> : String(row[column] ?? "—")}</td>)}</tr>; })}</tbody></table></div>}</div>;
}



