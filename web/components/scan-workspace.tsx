"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IzfinApiError, isRetryableApiError, izfinApiFetch, izfinApiStream } from "../lib/api";
import { fetchMarketStockDetail, type StockDetailResponse } from "../lib/market-center";
import { fetchScanJobContext, resultTickers, type ScanJobContext } from "../lib/scan-context";
import {
  canRetryRecovery,
  normalizeRecoveredScanJob,
  preferActiveRecoveryJob,
  preferRecoveredJob,
  recoverableJob,
  recoveryRetryDelayMs,
} from "../lib/scan-recovery.mjs";
import { useAnalysisContext } from "./analysis-context-provider";
import { useIzfinAuth } from "./auth-provider";
import { ScanDecisionCard } from "./scan-decision-card";
import { ScanMobileResultList } from "./scan-mobile-result-list";
import { ScanQuickControls } from "./scan-quick-controls";
import { ModalSurface } from "./modal-surface";

type ScanResultRow = Record<string, unknown>;
type ScanSummary = { sonuclar: ScanResultRow[]; basarisiz_taramalar: string[]; boga_sayisi: number; alim_firsati: number; teknik_paneller?: Record<string, Record<string, unknown>> };
type ScanJob = Omit<ScanJobContext, "result"> & { result?: ScanSummary };
type ScanRecoveryItem = Pick<ScanJob, "job_id" | "status" | "stage" | "completed" | "total"> & { tickers: string[] };
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
function sortValue(value: unknown): number | string {
  const raw = String(value ?? ""); const risk = { "ÇOK YÜKSEK": 4, YÜKSEK: 3, ORTA: 2, DÜŞÜK: 1 };
  const riskValue = Object.entries(risk).find(([label]) => raw.toLocaleUpperCase("tr-TR").includes(label)); if (riskValue) return riskValue[1];
  const numeric = raw.replace(",", ".").match(/[-+]?\d+(?:\.\d+)?/); return numeric ? Number(numeric[0]) : raw.toLocaleLowerCase("tr-TR");
}

export function ScanWorkspace() {
  const { user, getIdToken } = useIzfinAuth();
  const {
    activeScanJobId,
    activeUniverseProfile,
    setActiveScan,
    setSelectedTicker,
    setActiveUniverseProfile,
    refreshLatestCompletedScan,
  } = useAnalysisContext();
  const [watchlist, setWatchlist] = useState<Watchlist | null>(null);
  const [profiles, setProfiles] = useState<Record<string, string[]>>({});
  const [universe, setUniverse] = useState<Universe | null>(null);
  const [symbolDraft, setSymbolDraft] = useState("");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [suggestions, setSuggestions] = useState<SymbolSuggestion[]>([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState<SymbolSuggestion | null>(null);
  const [searchingSymbols, setSearchingSymbols] = useState(false);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [job, setJob] = useState<ScanJob | null>(null);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState<ResultFilter>("Tümü");
  const [guideDismissed, setGuideDismissed] = useState(false);
  const [scanStarting, setScanStarting] = useState(false);
  const [retryableError, setRetryableError] = useState(false);
  const [pollFailureCount, setPollFailureCount] = useState(0);
  const [recoveryDiscoveryFailures, setRecoveryDiscoveryFailures] = useState(0);
  const jobRef = useRef<ScanJob | null>(null);
  const scanControlRef = useRef<HTMLDivElement | null>(null);
  const symbolSearchInputRef = useRef<HTMLInputElement | null>(null);

  const publishCompletedScan = useCallback(async (completed: ScanJob, fallbackTickers: string[] = []) => {
    setActiveScan(completed.job_id);
    const completedTickers = resultTickers({ ...completed, tickers: completed.tickers ?? fallbackTickers });
    if (completedTickers.length === 1) setSelectedTicker(completedTickers[0]);
    await refreshLatestCompletedScan().catch(() => undefined);
  }, [refreshLatestCompletedScan, setActiveScan, setSelectedTicker]);

  const recoverActiveJob = useCallback((items: ScanRecoveryItem[]) => {
    const activeJob = items.find((item) => item.status === "queued" || item.status === "running");
    if (!activeJob) return;
    setJob((current) => preferActiveRecoveryJob(current, activeJob));
    setError("");
    setRetryableError(false);
    setPollFailureCount(0);
  }, []);

  const validateCachedScanJob = useCallback(async (token: string): Promise<ScanJob | null> => {
    if (!activeScanJobId) return null;
    try {
      return normalizeRecoveredScanJob(await fetchScanJobContext(activeScanJobId, token)) as ScanJob;
    } catch (caught) {
      if (caught instanceof IzfinApiError && [403, 404].includes(caught.status)) return null;
      throw caught;
    }
  }, [activeScanJobId]);

  const loadRecoveryJobs = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Tarama recovery için kimlik belirteci alınamadı.");
      const response = await izfinApiFetch<{ jobs: ScanRecoveryItem[] }>("/api/v1/scan/jobs", token);
      const candidate = recoverableJob(response.jobs);

      if (candidate?.status === "queued" || candidate?.status === "running") {
        recoverActiveJob(response.jobs);
        setRecoveryDiscoveryFailures(0);
        return;
      }

      const cached = await validateCachedScanJob(token);
      if (cached?.status === "queued" || cached?.status === "running") {
        setJob((current) => preferActiveRecoveryJob(current, cached));
        setError("");
        setRetryableError(false);
        setPollFailureCount(0);
        setRecoveryDiscoveryFailures(0);
        return;
      }

      const recovered = cached?.status === "completed"
        ? cached
        : candidate?.status === "completed"
          ? normalizeRecoveredScanJob(await fetchScanJobContext(candidate.job_id, token)) as ScanJob
          : null;

      if (recovered) {
        if (preferRecoveredJob(jobRef.current, recovered) !== recovered) {
          setRecoveryDiscoveryFailures(0);
          return;
        }
        setJob((current) => preferRecoveredJob(current, recovered));
        setError("");
        setRetryableError(false);
        setPollFailureCount(0);
        await publishCompletedScan(recovered);
      }
      setRecoveryDiscoveryFailures(0);
    } catch {
      setRecoveryDiscoveryFailures((current) => current + 1);
    }
  }, [getIdToken, publishCompletedScan, recoverActiveJob, user, validateCachedScanJob]);

  const loadWorkspace = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getIdToken(); if (!token) return;
      const [list, availableProfiles] = await Promise.all([
        izfinApiFetch<Watchlist>("/api/v1/watchlist", token),
        izfinApiFetch<Profiles>("/api/v1/scan/profiles", token),
      ]);
      setWatchlist(list);
      setProfiles(availableProfiles.profiles);
      setError("");
    } catch {
      setError("Kişisel liste veya tarama profilleri şu anda yüklenemedi.");
    }
  }, [getIdToken, user]);

  const loadUniverse = useCallback(async () => {
    if (!user || !watchlist) return;
    try {
      const token = await getIdToken(); if (!token) return;
      setUniverse(await izfinApiFetch<Universe>("/api/v1/scan/universe", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profil: activeUniverseProfile, kisisel_liste: watchlist.tickers, preset_options: profiles }),
      }));
    } catch {
      setError("Tarama evreni hazırlanamadı.");
    }
  }, [activeUniverseProfile, getIdToken, profiles, user, watchlist]);

  useEffect(() => { void Promise.all([loadWorkspace(), loadRecoveryJobs()]); }, [loadRecoveryJobs, loadWorkspace]);
  useEffect(() => {
    if (!user || recoveryDiscoveryFailures === 0 || !canRetryRecovery(recoveryDiscoveryFailures)) return;
    const timeout = window.setTimeout(
      () => void loadRecoveryJobs(),
      recoveryRetryDelayMs(recoveryDiscoveryFailures),
    );
    return () => window.clearTimeout(timeout);
  }, [loadRecoveryJobs, recoveryDiscoveryFailures, user]);
  useEffect(() => { if (user) setGuideDismissed(window.localStorage.getItem(`izfin:first-scan-guide:${user.uid}`) === "done"); }, [user]);
  useEffect(() => { jobRef.current = job; }, [job]);
  useEffect(() => { void loadUniverse(); }, [loadUniverse]);
  useEffect(() => {
    if (scanStarting || !job || !["queued", "running"].includes(job.status) || !canRetryRecovery(pollFailureCount)) return;
    const timeout = window.setTimeout(() => void (async () => {
      try {
        const token = await getIdToken();
        if (!token) throw new Error("Tarama durumu için kimlik belirteci alınamadı.");
        const updated = await izfinApiFetch<ScanJob>(`/api/v1/scan/jobs/${job.job_id}`, token);
        setPollFailureCount(0);
        setError("");
        setJob(updated);
        if (updated.status === "completed") await publishCompletedScan(updated);
        if (["completed", "failed"].includes(updated.status)) void loadRecoveryJobs();
      } catch {
        setPollFailureCount((current) => current + 1);
        setError("Tarama durumu geçici olarak alınamadı; otomatik yeniden deneniyor…");
      }
    })(), recoveryRetryDelayMs(pollFailureCount));
    return () => window.clearTimeout(timeout);
  }, [getIdToken, job, loadRecoveryJobs, pollFailureCount, publishCompletedScan, scanStarting]);

  async function replaceWatchlist(nextTickers: string[]) {
    const normalized = normalizeTickers(nextTickers);
    if (!normalized.length) { setError("Kişisel listede en az bir sembol kalmalı."); return; }
    try {
      const token = await getIdToken(); if (!token) return;
      const saved = await izfinApiFetch<Watchlist>("/api/v1/watchlist", token, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: normalized }),
      });
      setWatchlist(saved);
      setActiveUniverseProfile("Kendi Listem");
      setSymbolDraft("");
      setError("");
    } catch {
      setError("Kişisel liste kaydedilemedi.");
    }
  }

  function addSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!symbolDraft.trim()) { setError("Eklenecek sembolü yazın."); return; }
    void replaceWatchlist([...(watchlist?.tickers ?? []), ...symbolDraft.split(/[\s,]+/)]);
  }

  async function findSymbols(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = symbolSearch.trim();
    setSelectedSuggestion(null);
    setSuggestions([]);
    setSearchedQuery(query);
    if (!query) { setError("Aramak istediğin hisseyi veya şirketi yazın."); return; }
    try {
      const token = await getIdToken(); if (!token) return;
      setSearchingSymbols(true);
      setError("");
      const result = await izfinApiFetch<{ suggestions: SymbolSuggestion[] }>(`/api/v1/scan/symbols?q=${encodeURIComponent(query)}`, token);
      setSuggestions(result.suggestions);
    } catch {
      setError("Sembol araması şu anda alınamıyor.");
    } finally {
      setSearchingSymbols(false);
    }
  }

  function addSelectedSuggestion() { if (selectedSuggestion) void replaceWatchlist([...(watchlist?.tickers ?? []), selectedSuggestion.symbol]); }
  function removeSymbol(value: string) { void replaceWatchlist((watchlist?.tickers ?? []).filter((item) => item !== value)); }

  async function submit() {
    setError("");
    setRetryableError(false);
    setActiveFilter("Tümü");
    if (!universe?.tickers.length) { setError("Taramayı başlatmadan önce en az bir varlık seçin."); return; }
    setPollFailureCount(0);
    setRecoveryDiscoveryFailures(0);
    setScanStarting(true);
    try {
      const token = await getIdToken(); if (!token) return;
      const completed = await izfinApiStream<ScanJob>("/api/v1/scan/jobs/stream", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: universe.tickers }),
      }, setJob);
      setJob(completed);
      if (completed.status === "completed") await publishCompletedScan(completed, universe.tickers);
    } catch (caught) {
      if (caught instanceof IzfinApiError && isRetryableApiError(caught)) {
        setError(caught.message);
        setRetryableError(true);
      } else {
        setError("Canlı tarama bağlantısı kesildi. Devam eden iş sunucu durumundan geri yükleniyor…");
      }
      void loadRecoveryJobs();
    } finally {
      setScanStarting(false);
    }
  }

  function dismissGuide() {
    if (user) window.localStorage.setItem(`izfin:first-scan-guide:${user.uid}`, "done");
    setGuideDismissed(true);
  }

  function chooseProfile(profile: string) {
    setActiveUniverseProfile(profile);
    scanControlRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function focusListManager() {
    scanControlRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    symbolSearchInputRef.current?.focus();
  }

  if (!user) return null;
  const running = scanStarting || job?.status === "queued" || job?.status === "running";

  return <>
    <ScanQuickControls
      activeProfile={activeUniverseProfile}
      launchDisabled={running || !universe?.tickers.length}
      onChooseProfile={chooseProfile}
      onFocusListManager={focusListManager}
      onLaunchScan={() => void submit()}
    />
    <section className="scan-workspace" aria-label="Akıllı tarama">
      <div className="section-heading"><div><p className="eyebrow">IZFIN SCANNER</p><h2>Akıllı Tarama Merkezi</h2></div><span className="section-index">SIGNATURE SCAN</span></div>
      <p className="scan-intro">Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p>
      {!guideDismissed && !job && watchlist && <FirstScanGuide tickerCount={watchlist.tickers.length} onDismiss={dismissGuide} />}
      <div id="scan-control" ref={scanControlRef} className="scan-control-grid">
        <section className="scan-control-card">
          <p className="eyebrow">KİŞİSEL LİSTE</p><h3>Kişisel Listemi Yönet</h3><p>Kalıcı takip listen, Kendi Listem profilinin tarama evrenidir.</p>
          {watchlist ? <>
            <form className="symbol-search-form" onSubmit={findSymbols}><label>Hisse / şirket ara<input ref={symbolSearchInputRef} value={symbolSearch} onChange={(event) => setSymbolSearch(event.target.value)} placeholder="Örn. APP, Apple, NVDA, THYAO..." /></label><button type="submit" disabled={searchingSymbols}>{searchingSymbols ? "Aranıyor…" : "Ara"}</button></form>
            {searchedQuery && !searchingSymbols && <p className="symbol-search-meta">{suggestions.length ? `🔎 ${suggestions.length} eşleşme bulundu` : "Bu aramayla eşleşen piyasa sembolü bulunamadı."}</p>}
            {suggestions.length > 0 && <div className="symbol-suggestions" aria-label="Arama sonuçları">{suggestions.map((item) => <button className={selectedSuggestion?.symbol === item.symbol ? "active" : ""} key={`${item.symbol}-${item.exchange}`} type="button" onClick={() => setSelectedSuggestion(item)}><b>{item.symbol}</b><span>{item.name || "Piyasa sembolü"}</span><small>{[item.exchange, item.quote_type].filter(Boolean).join(" · ")}</small></button>)}</div>}
            {selectedSuggestion && <div className="symbol-selection-preview"><div><b>{selectedSuggestion.symbol}</b><span>{selectedSuggestion.name || "Piyasa sembolü"}</span></div><button type="button" disabled={watchlist.tickers.includes(selectedSuggestion.symbol)} onClick={addSelectedSuggestion}>{watchlist.tickers.includes(selectedSuggestion.symbol) ? "Listende" : `＋ ${selectedSuggestion.symbol} Listeme Ekle`}</button></div>}
            <div className="ticker-list">{watchlist.tickers.map((item) => <button key={item} type="button" onClick={() => removeSymbol(item)} aria-label={`${item} sembolünü listeden sil`}>{item} <span>×</span></button>)}</div>
            <form className="watchlist-form scan-watchlist-form" onSubmit={addSymbol}><label>Sembol ekle<input value={symbolDraft} onChange={(event) => setSymbolDraft(event.target.value)} placeholder="örn. THYAO.IS" /></label><button type="submit">Manuel ekle</button></form>
          </> : <p className="scan-empty">Kişisel liste yükleniyor…</p>}
        </section>
        <section className="scan-control-card">
          <p className="eyebrow">TARAMA EVRENİ</p><h3>Evreni hazırla ve taramayı başlat</h3>
          <label className="scan-profile-label">Profil<select value={activeUniverseProfile} onChange={(event) => setActiveUniverseProfile(event.target.value)}><option>Kendi Listem</option>{Object.keys(profiles).map((name) => <option key={name}>{name}</option>)}</select></label>
          <div className="active-universe"><span>AKTİF TARAMA EVRENİ</span><strong>{universe?.profil ?? activeUniverseProfile}</strong><b>{universe?.secim_ozeti.varlik_adedi ?? 0} VARLIK</b></div>
          {universe?.chipleri_goster && <div className="scan-universe-chips">{universe.tickers.map((item) => <span key={item}>{item}</span>)}</div>}
          <button className="scan-launch" disabled={running || !universe?.tickers.length} type="button" onClick={() => void submit()}>{running ? "Tarama sürüyor…" : "AKILLI TARAMAYI BAŞLAT"}</button>
          <small>Tarama; IZFIN skor, güven, giriş kalitesi, MTF, risk ve para akışı katmanlarını birlikte çalıştırır.</small>
        </section>
      </div>
      {running && <ScanOverlay job={job} total={universe?.tickers.length ?? 0} />}
      {error && <div className="scan-service-error" role="alert"><span>{error}</span>{retryableError && <button type="button" disabled={running} onClick={() => void submit()}>Tekrar dene</button>}</div>}
      {job && !running && <p className="job-progress" aria-live="polite">Durum: <strong>{job.stage}</strong> · {job.completed}/{job.total}</p>}
      {job?.status === "failed" && <p role="alert">{job.error ?? "Tarama tamamlanamadı."}</p>}
      {job?.status === "completed" && job.result && <ScanResult jobId={job.job_id} summary={job.result} activeFilter={activeFilter} onFilterChange={setActiveFilter} />}
    </section>
  </>;
}

function ScanOverlay({ job, total }: Readonly<{ job: ScanJob | null; total: number }>) {
  const completed = job?.completed ?? 0; const count = job?.total || total || 1;
  const stage = job?.stage ?? "queued";
  const bounds = stage === "complete" ? [100, 100] : stage === "finalizing" ? [94, 98] : stage === "ticker" ? [38 + Math.round((completed / count) * 52), Math.min(92, 38 + Math.round(((completed + 1) / count) * 52) - 2)] : stage === "data_ready" ? [28, 36] : stage === "preparing" || stage === "starting" ? [7, 26] : [3, 6];
  const [percent, setPercent] = useState(bounds[0]);
  useEffect(() => {
    setPercent((value) => stage === "complete" ? 100 : Math.max(value, bounds[0]));
    if (bounds[0] >= bounds[1]) return;
    const timer = window.setInterval(() => setPercent((value) => Math.min(bounds[1], value + 1)), 650);
    return () => window.clearInterval(timer);
  }, [bounds[0], bounds[1], job?.job_id, stage]);
  const title = stage === "finalizing" ? "Sonuç ekranı hazırlanıyor" : stage === "ticker" ? "Varlıklar analiz ediliyor" : stage === "data_ready" ? "Piyasa verileri hazır" : stage === "preparing" ? "Piyasa verileri alınıyor" : "Akıllı Tarama başladı";
  const description = stage === "finalizing" ? "Kararlar ve teknik paneller güvenli biçimde paketleniyor…" : stage === "ticker" ? `${job?.current_ticker ?? "Seçili varlık"} için skor · güven · MTF · risk katmanları değerlendiriliyor…` : "Piyasa geçmişi ve güncel seans verileri sağlayıcılardan hazırlanıyor…";
  return <ModalSurface className="scan-lock-overlay" label="IZFIN Akıllı Tarama sürüyor"><div className="scan-lock-card" role="status" aria-live="polite"><div className="scan-lock-brand"><i /><small>IZFIN SMART SCAN</small></div><h2 data-modal-focus tabIndex={-1}>{title}</h2><p>{description}</p><div className="scan-lock-progress"><span style={{ width: `${percent}%` }} /></div><div className="scan-lock-meta"><strong>%{percent}</strong><span>{stage === "ticker" ? `${completed}/${count} varlık tamamlandı` : completed ? `${completed}/${count} varlık · sonuçlar hazırlanıyor` : `${count} varlık sıraya alındı`}</span></div><small>Tarama tamamlanana kadar ekran geçici olarak kilitlendi. Canlı aşama içindeki yüzde yaklaşık ilerlemedir.</small></div></ModalSurface>;
}

function FirstScanGuide({ tickerCount, onDismiss }: Readonly<{ tickerCount: number; onDismiss: () => void }>) {
  return <section className="first-scan-guide" aria-label="İlk tarama rehberi"><div className="first-scan-head"><div><p className="eyebrow">İLK TARAMA REHBERİ</p><h3>Bir sonucu 30 saniyede değerlendir</h3><p>Önce merkezi kararı, sonra kararın güvenini ve risk planını okuyun.</p></div><button type="button" onClick={onDismiss}>Rehberi kapat</button></div><div className="first-scan-steps"><article><span>1 · TARAMA</span><b>Evreni seçin</b><small>{tickerCount} kayıtlı varlığın var. Kendi Listem veya hazır bir profil ile başla.</small></article><article><span>2 · KARAR</span><b>Aksiyonu okuyun</b><small>İlk referansın puan değil, Merkezi Karar olsun.</small></article><article><span>3 · TEYİT</span><b>Nedeni kontrol edin</b><small>Güven, giriş kalitesi ve MTF uyumunu birlikte değerlendir.</small></article><article><span>4 · PLAN</span><b>Riski belirleyin</b><small>Destek, stop ve hedefleri işlemden önce planla.</small></article></div><div className="first-scan-note"><b>Ana kural:</b> Skorlar karar vermez; kararı açıklar. İşlem yönünü trend, momentum, para akışı, zamanlama ve risk filtrelerini birlikte değerlendiren Merkezi Karar belirler.<a href="#scan-control">Tarama kontrolüne git →</a></div></section>;
}

function ScanResult({ jobId, summary, activeFilter, onFilterChange }: Readonly<{ jobId: string; summary: ScanSummary; activeFilter: ResultFilter; onFilterChange: (filter: ResultFilter) => void }>) {
  const { getIdToken } = useIzfinAuth();
  const {
    selectedTicker: rememberedTicker,
    setSelectedTicker: setSharedSelectedTicker,
  } = useAnalysisContext();
  const [sort, setSort] = useState<{ column: string; direction: SortDirection }>({ column: "Gelişmiş Skor", direction: "desc" });
  const [focusMode, setFocusMode] = useState(false);
  const [decisionDetail, setDecisionDetail] = useState<StockDetailResponse | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const results = useMemo(() => summary.sonuclar.filter((row) => activeFilter === "Tümü" || (activeFilter === "AL Sinyalleri" ? isBuy(row) : activeFilter === "Uzun Vadeli Adaylar" ? isLongTerm(row) : isConfirmation(row))).sort((left, right) => { const a = sortValue(left[sort.column]); const b = sortValue(right[sort.column]); const comparison = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "tr"); return sort.direction === "asc" ? comparison : -comparison; }), [activeFilter, sort, summary.sonuclar]);
  const decisionTickers = useMemo(() => normalizeTickers(summary.sonuclar.map(ticker)), [summary.sonuclar]);
  const selectedTicker = decisionTickers.includes(rememberedTicker) ? rememberedTicker : (decisionTickers[0] ?? "");

  useEffect(() => {
    if (selectedTicker !== rememberedTicker) setSharedSelectedTicker(selectedTicker);
  }, [rememberedTicker, selectedTicker, setSharedSelectedTicker]);

  useEffect(() => {
    if (!jobId || !selectedTicker) { setDecisionDetail(null); return; }
    let active = true;
    setDecisionDetail(null);
    setDecisionError("");
    void (async () => {
      try {
        const token = await getIdToken(); if (!token) return;
        const detail = await fetchMarketStockDetail(jobId, selectedTicker, token);
        if (active) setDecisionDetail(detail);
      } catch {
        if (active) setDecisionError("Hisse karar motoru bu sonuç için yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, jobId, selectedTicker]);

  function updateSort(column: string) { setSort((current) => ({ column, direction: current.column === column && current.direction === "desc" ? "asc" : "desc" })); }

  return <ModalSurface id="scan-result" className={`scan-result scan-summary${focusMode ? " is-focus" : ""}`} label="Tarama sonucu" modal={focusMode} onDismiss={() => setFocusMode(false)}>
    <div className="scan-result-header"><div><p className="eyebrow">TARAMA SONUCU</p><h3>Akıllı Tarama Sonuçları</h3></div><div className="scan-result-actions"><button data-modal-focus type="button" onClick={() => setFocusMode((value) => !value)}>{focusMode ? "↙ Geniş Görünümden Çık" : "⛶ Tabloyu Genişlet"}</button><span>{summary.sonuclar.length} sembol</span></div></div>
    {focusMode && <div className="scan-focus-meta"><b>Geniş sonuç görünümü</b><span>{results.length} sonuç · {activeFilter} filtresi · bir sütuna dokunarak sırala</span></div>}
    <div className="scan-metrics"><span><b>{summary.sonuclar.length}</b>Taranan Varlık</span><span><b>{summary.boga_sayisi}</b>Boğa Trendinde (200G)</span><span><b>{summary.alim_firsati}</b>Alım Fırsatları & Kırılımlar</span></div>
    <div className="result-filter" aria-label="Gösterilecek sonuçlar"><span>Gösterilecek sonuçlar</span>{filters.map((filter) => <button className={activeFilter === filter ? "active" : ""} key={filter} type="button" onClick={() => onFilterChange(filter)}>{filter}</button>)}</div>
    <p className="scan-filter-summary">{results.length} sonuç gösteriliyor · Filtre: {activeFilter}</p>
    {summary.basarisiz_taramalar.length > 0 && <p>Veri/hesaplama sorunu nedeniyle es geçilen varlıklar: {summary.basarisiz_taramalar.join(", ")}</p>}
    {summary.sonuclar.length === 0 ? <p className="scan-empty">Veriler çekilemedi. Farklı bir profil veya varlık grubu seçip tekrar deneyin.</p> : results.length === 0 ? <p className="scan-empty">Bu filtreye uyan sonuç yok. Diğer filtrelerden birini seçebilir veya taramayı daha sonra yenileyebilirsin.</p> : <>
      <ScanMobileResultList rows={results} selectedTicker={selectedTicker} onSelectTicker={setSharedSelectedTicker} />
      <div className="scan-result-table-wrap"><table className="scan-result-table"><thead><tr>{resultColumns.map((column) => <th key={column}><button type="button" onClick={() => updateSort(column)}>{column} <span>{sort.column === column ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span></button></th>)}</tr></thead><tbody>{results.map((row, index) => { const symbol = ticker(row); const profile = String(row["Teknik Profil"] ?? "").trim(); return <tr className={selectedTicker === symbol ? "is-selected" : ""} key={`${symbol}-${index}`}>{resultColumns.map((column) => <td key={column} className={column === "Nihai Sinyal" ? "scan-signal-cell" : ""}>{column === "Varlık" && symbol ? <button className="scan-result-symbol" type="button" onClick={() => setSharedSelectedTicker(symbol)}>{symbol}</button> : column === "Nihai Sinyal" && profile ? <><span>{String(row[column] ?? "—")}</span><small className="scan-signal-profile">Teknik Profil: {profile}</small></> : String(row[column] ?? "—")}</td>)}</tr>; })}</tbody></table></div>
    </>}
    {selectedTicker && !decisionDetail && !decisionError ? <p className="scan-decision-state" aria-live="polite">{selectedTicker} karar motoru yükleniyor…</p> : null}
    {decisionError ? <p className="scan-decision-state" role="alert">{decisionError}</p> : null}
    {decisionDetail ? <ScanDecisionCard jobId={jobId} detail={decisionDetail} tickers={decisionTickers} onTickerChange={setSharedSelectedTicker} /> : null}
  </ModalSurface>;
}
