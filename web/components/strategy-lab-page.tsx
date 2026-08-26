"use client";

import { FormEvent, useState } from "react";
import { runBacktest, type BacktestPeriod, type BacktestResponse } from "../lib/backtest";
import { useIzfinAuth } from "./auth-provider";

const PERIODS: BacktestPeriod[] = ["3y", "5y", "10y"];
const SUGGESTED_SYMBOLS = ["THYAO.IS", "AKBNK.IS", "ASELS.IS"];
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
  const [ticker, setTicker] = useState("");
  const [period, setPeriod] = useState<BacktestPeriod>("5y");
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (!normalized) {
      setError("Backtest için bir sembol girin.");
      return;
    }
    setRunning(true);
    setError("");
    setResult(null);
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
        <label htmlFor="strategy-ticker">SEMBOL</label>
        <input id="strategy-ticker" value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="THYAO.IS" autoComplete="off" aria-describedby="strategy-symbol-note" />
        <small id="strategy-symbol-note">BIST sembolünü <b>.IS</b> uzantısıyla gir.</small>
        <div className="strategy-symbol-suggestions" aria-label="Örnek semboller">{SUGGESTED_SYMBOLS.map((symbol) => <button type="button" key={symbol} onClick={() => setTicker(symbol)}>{symbol}</button>)}</div>
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

        <StrategyTable title="Merkezi karar türlerine göre özet" eyebrow="KARAR TİPLERİ" rows={result.summary} columns={SUMMARY_COLUMNS} />
        <StrategyTable title="Geçmiş test işlemleri" eyebrow="İŞLEM DETAYI" rows={result.detail} columns={DETAIL_COLUMNS} wide />

        <section className="strategy-panel strategy-methodology">
          <div><p className="eyebrow">SONUÇ KAPSAMI</p><h2>Backtest nasıl okunmalı?</h2><p><b>Sonuç kapsamı</b> · {result.detail_explanation}</p></div>
          <div className="strategy-notes">{result.reading_notes.split("\n").filter(Boolean).map((line, index) => <p key={index}>{line}</p>)}</div>
        </section>
      </>}
    </>}
  </main>;
}

function StrategyTable({ title, eyebrow, rows, columns, wide = false }: Readonly<{ title: string; eyebrow: string; rows: Array<Record<string, unknown>>; columns: string[]; wide?: boolean }>) {
  return <section className="strategy-panel strategy-table-card">
    <div className="strategy-section-head"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div><span>{rows.length} satır</span></div>
    {rows.length === 0 ? <p className="strategy-table-empty">Gösterilecek sonuç bulunamadı.</p> : <div className="strategy-table-scroll"><table className={`strategy-table${wide ? " strategy-table-wide" : ""}`}>
      <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
      <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{columns.map((column) => <td className={valueClass(column, row[column])} key={column}>{column === "Sinyal" || column === "Varlık" ? <b>{text(row[column])}</b> : text(row[column])}</td>)}</tr>)}</tbody>
    </table></div>}
  </section>;
}
