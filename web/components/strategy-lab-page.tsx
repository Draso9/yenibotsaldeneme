"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  runBacktest,
  searchBacktestSymbols,
  type BacktestPeriod,
  type BacktestResponse,
  type BacktestSymbolSuggestion,
} from "../lib/backtest";
import { formatBacktestValue, readStrategyTicker, writeStrategyTicker } from "../lib/backtest-format.mjs";
import { useIzfinAuth } from "./auth-provider";
import { StrategyDisclosure } from "./strategy-disclosure";

const PERIODS: BacktestPeriod[] = ["3y", "5y", "10y"];
const SUMMARY_COLUMNS = ["Sinyal", "Örnek", "İşlem Başarı %", "Ort. İşlem %", "TP1 İlk %", "Stop İlk %", "20G Kârda %", "20G Ort. %", "45G Kârda %", "45G Ort. %"];
const DETAIL_COLUMNS = ["Tarih", "Sinyal", "Teknik Profil", "Ön Sinyal", "Hibrit Skor", "Güven %", "Daily MTF %", "Giriş Proxy", "Giriş", "İlk Stop", "İlk TP1", "İlk Olay", "İşlem Sonucu %", "20G %", "45G %"];

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "number") return value.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
  return String(value);
}

function valueClass(column: string, value: unknown): string {
  if (!column.includes("%")) return "";
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) return "neutral";
  return numeric > 0 ? "positive" : "negative";
}

export function StrategyLabPage() {
  const { loading: authLoading, user, getIdToken } = useIzfinAuth();
  const userId = user?.uid ?? "";
  const [ticker, setTicker] = useState("");
  const [period, setPeriod] = useState<BacktestPeriod>("5y");
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<BacktestSymbolSuggestion[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState("");

  useEffect(() => {
    const restored = userId ? readStrategyTicker(window.sessionStorage, userId) : "";
    setTicker(restored);
    setSelectedSymbol(restored);
    setResult(null);
    setError("");
  }, [userId]);

  useEffect(() => {
    const query = ticker.trim();
    if (!user || query.length < 1 || query.toUpperCase() === selectedSymbol) {
      setSuggestions([]);
      setSearching(false);
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        setSearching(true);
        try {
          const token = await getIdToken();
          if (!token) return;
          const response = await searchBacktestSymbols(token, query, 8);
          if (active) setSuggestions(response.suggestions);
        } catch {
          if (active) setSuggestions([]);
        } finally {
          if (active) setSearching(false);
        }
      })();
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [getIdToken, selectedSymbol, ticker, user]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (!normalized) {
      setError("Backtest için bir sembol girin.");
      return;
    }
    if (!user) {
      setError("Güvenli oturum hazırlanamadı.");
      return;
    }
    setRunning(true);
    setError("");
    setResult(null);
    setSuggestions([]);
    writeStrategyTicker(window.sessionStorage, userId, normalized);
    try {
      const token = await getIdToken();
      if (!token) {
        setError("Güvenli oturum hazırlanamadı.");
        return;
      }
      setResult(await runBacktest(token, normalized, period));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Backtest çalıştırılamadı.");
    } finally {
      setRunning(false);
    }
  }

  function selectSuggestion(suggestion: BacktestSymbolSuggestion) {
    const symbol = suggestion.symbol.trim().toUpperCase();
    setTicker(symbol);
    setSelectedSymbol(symbol);
    setSuggestions([]);
    setError("");
    if (userId) writeStrategyTicker(window.sessionStorage, userId, symbol);
  }

  function beginNewRun() {
    setResult(null);
    setError("");
  }

  if (authLoading) return <main className="strategy-page"><section className="strategy-panel strategy-status" aria-live="polite"><strong>Güvenli oturum hazırlanıyor</strong><span>Backtest çalışma alanın hesabınla eşleştiriliyor.</span></section></main>;
  if (!user) return <main className="strategy-page"><section className="strategy-panel strategy-auth"><p className="eyebrow">STRATEJİ LABORATUVARI</p><h1>Daily Core Backtest</h1><p>Geçmiş IZFIN kararlarını test etmek için hesabınla giriş yap.</p><a href="/">Ana sayfaya dön →</a></section></main>;

  return <main className="strategy-page" aria-label="IZFIN Strateji Laboratuvarı">
    <div className="strategy-path"><a href="/">← Piyasa Merkezi</a><span>Analiz araçları / Strateji Lab</span></div>
    <section className="strategy-hero">
      <div>
        <p className="eyebrow">STRATEJİ LABORATUVARI</p>
        <h1>Daily Core Backtest</h1>
        <p className="strategy-muted">Geçmiş her günü yalnızca o güne kadar bilinen verilerle yeniden oynat; merkezi IZFIN kararlarının sonrasını ölç.</p>
      </div>
      <span className="strategy-engine-chip"><i /> DAILY CORE</span>
    </section>

    <form className="strategy-panel strategy-runner" onSubmit={submit}>
      <div className="strategy-symbol-field">
        <label htmlFor="strategy-ticker">SEMBOL / ŞİRKET ARA</label>
        <input
          id="strategy-ticker"
          value={ticker}
          onChange={(event) => {
            setTicker(event.target.value.toUpperCase());
            setSelectedSymbol("");
          }}
          placeholder="NVDA, AVGO veya THYAO.IS"
          autoComplete="off"
          aria-describedby="strategy-symbol-note"
          aria-autocomplete="list"
          aria-expanded={suggestions.length > 0}
        />
        <small id="strategy-symbol-note">Sembol veya şirket adı yaz. Önerilerden seçim yapabilir; havuzda görünmeyen geçerli Yahoo sembolünü de doğrudan test edebilirsin.</small>
        {searching && <div className="strategy-symbol-search-state">Semboller aranıyor…</div>}
        {!searching && ticker.trim() && suggestions.length === 0 && !selectedSymbol && <div className="strategy-symbol-search-state">Eşleşme yoksa yazdığın sembol doğrudan backtest edilecek.</div>}
        {suggestions.length > 0 && <div className="strategy-symbol-results" role="listbox" aria-label="Sembol önerileri">
          {suggestions.map((suggestion) => <button type="button" role="option" aria-selected={false} key={`${suggestion.symbol}-${suggestion.exchange}`} onClick={() => selectSuggestion(suggestion)}>
            <span><b>{suggestion.symbol}</b>{suggestion.name && <small>{suggestion.name}</small>}</span>
            <em>{suggestion.exchange || suggestion.quote_type || "Piyasa"}</em>
          </button>)}
        </div>}
      </div>
      <div className="strategy-period-field">
        <span>GEÇMİŞ DÖNEM</span>
        <div>{PERIODS.map((item) => <button type="button" className={period === item ? "active" : ""} key={item} onClick={() => setPeriod(item)}>{item.toUpperCase()}</button>)}</div>
      </div>
      <button className="strategy-run-button" type="submit" disabled={running}>{running ? "HESAPLANIYOR…" : "BACKTEST'İ ÇALIŞTIR"}</button>
    </form>

    <section className="strategy-context-grid">
      <article className="strategy-panel"><span>TEST MANTIĞI</span><strong>Merkezi karar → test işlemi</strong><p>Yalnızca GÜÇLÜ AL / AL / ERKEN AL kararları geçmiş işlem olarak açılır.</p></article>
      <article className="strategy-panel"><span>VERİ DİSİPLİNİ</span><strong>Gelecek bilgisi yok</strong><p>Her gün yalnızca o tarihte bilinebilecek günlük veriler yeniden hesaplanır.</p></article>
      <article className="strategy-panel"><span>UFUKLAR</span><strong>5 / 10 / 20 / 45 gün</strong><p>Stop ve TP sonucu yanında sabit ufuk hareketleri ayrıca izlenir.</p></article>
    </section>

    {error && <section className="strategy-panel strategy-status" role="alert"><strong>Backtest çalıştırılamadı</strong><span>{error}</span></section>}
    {running && <section className="strategy-panel strategy-status" aria-live="polite"><strong>Daily Core hesaplanıyor</strong><span>{ticker.trim().toUpperCase()} · {period.toUpperCase()} geçmiş dönem verisi işleniyor.</span></section>}

    {result && <>
      <section className="strategy-result-head">
        <div><p className="eyebrow">BACKTEST SONUCU</p><h2>{result.ticker}</h2></div>
        <div><span>{result.period.toUpperCase()}</span><span>{result.detail.length} işlem</span><button type="button" onClick={beginNewRun}>Yeni test başlat</button></div>
      </section>

      {result.empty ? <section className="strategy-panel strategy-empty">Seçilen dönem için yeterli veri veya alım sinyali bulunamadı.</section> : <>
        <section className="strategy-primary-kpis">
          {result.kpis.birincil.map((metric) => <article className="strategy-panel strategy-kpi" key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><i /></article>)}
        </section>
        <section className="strategy-secondary-kpis">
          {result.kpis.ikincil.map((metric) => <article className="strategy-panel" key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></article>)}
        </section>

        {result.ambiguity_count > 0 && result.ambiguity_message && <section className="strategy-panel strategy-warning"><b>MUHAFAZAKÂR SIRALAMA</b><p>{result.ambiguity_message}</p></section>}

        <StrategyTable title="Merkezi karar türlerine göre özet" eyebrow="KARAR TİPLERİ" rows={result.summary} columns={SUMMARY_COLUMNS} formats={result.summary_formats} />
        <StrategyDisclosure label="Geçmiş IZFIN kararlarını incele" count={result.detail.length}>
          <StrategyTable title="Geçmiş test işlemleri" eyebrow="İŞLEM DETAYI" rows={result.detail} columns={DETAIL_COLUMNS} formats={result.detail_formats} wide />
          <p className="strategy-detail-explanation"><b>Sonuç kapsamı</b> · {result.detail_explanation}</p>
        </StrategyDisclosure>
        <StrategyDisclosure label="Backtest sonuçları nasıl okunur?">
          <div className="strategy-notes">{result.reading_notes.split("\n").filter(Boolean).map((line, index) => <p key={index}>{line}</p>)}</div>
        </StrategyDisclosure>
      </>}
    </>}
  </main>;
}

function StrategyTable({ title, eyebrow, rows, columns, formats, wide = false }: Readonly<{ title: string; eyebrow: string; rows: Array<Record<string, unknown>>; columns: string[]; formats: Record<string, string>; wide?: boolean }>) {
  return <section className="strategy-panel strategy-table-card">
    <div className="strategy-section-head"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div><span>{rows.length} satır</span></div>
    {rows.length === 0 ? <p className="strategy-table-empty">Gösterilecek sonuç bulunamadı.</p> : <div className="strategy-table-scroll"><table className={`strategy-table${wide ? " strategy-table-wide" : ""}`}>
      <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
      <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{columns.map((column) => <td className={valueClass(column, row[column])} key={column}>{column === "Sinyal" || column === "Varlık" ? <b>{formatBacktestValue(column, row[column], formats)}</b> : formatBacktestValue(column, row[column], formats)}</td>)}</tr>)}</tbody>
    </table></div>}
  </section>;
}
