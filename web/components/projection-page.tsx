"use client";

import { useEffect, useState } from "react";
import { fetchProjection, type ProjectionResponse } from "../lib/projection";
import { fetchScanJobContext, resolveTicker, resultTickers } from "../lib/scan-context";
import { stockDetailHref } from "../lib/stock-detail-route";
import { useAnalysisContext } from "./analysis-context-provider";
import { useIzfinAuth } from "./auth-provider";
import { ProjectionModelView } from "./projection-model-view";

// Presentation contract: ProjectionModelView renders "Model kapsamı" and the explicit "yatırım tavsiyesi değildir" disclaimer.
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
          try {
            await refreshLatestCompletedScan();
          } catch {
            /* guided state below after one authoritative history attempt */
          }
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

  const backHref = resolvedJobId && resolvedTicker ? stockDetailHref(resolvedJobId, resolvedTicker) : "/";

  function chooseTicker(nextTicker: string) {
    const normalized = nextTicker.trim().toUpperCase();
    setResolvedTicker(normalized);
    setSelectedTicker(normalized);
  }

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
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-ticker-selector"><p className="eyebrow">SON TAMAMLANAN TARAMA</p><h1>Projeksiyon için hisse seç</h1><p>Son tamamlanan taramandaki varlıklardan birini seç.</p><select value={resolvedTicker} onChange={(event) => chooseTicker(event.target.value)}><option value="">Hisse seç…</option>{availableTickers.map((value) => <option value={value} key={value}>{value}</option>)}</select></section></main>;
  }

  if (!resolvedJobId || !resolvedTicker) {
    return <main className="projection-page"><a className="projection-back" href="/">← Piyasa Merkezi</a><section className="projection-panel projection-status" role="alert"><strong>Projeksiyon bağlamı kullanılamıyor</strong><span>{error || "Tamamlanmış taramadan bir varlık seçilemedi."}</span><a href="/scan">Akıllı Tarama'yı aç →</a></section></main>;
  }

  if (!projection && !error) {
    return <main className="projection-page"><div className="projection-path"><a className="projection-back" href={backHref}>← Detaylı Analiz</a><span>Tarama sonucu / {resolvedTicker} / Projeksiyon</span></div><section className="projection-panel projection-status" aria-live="polite"><strong>Model hazırlanıyor</strong><span>Tarama verisindeki teknik panel, ATR ve volatilite bantları işleniyor.</span></section></main>;
  }

  if (error || !projection) {
    return <main className="projection-page"><div className="projection-path"><a className="projection-back" href={backHref}>← Detaylı Analiz</a><span>Tarama sonucu / {resolvedTicker} / Projeksiyon</span></div><section className="projection-panel projection-status" role="alert"><strong>Projeksiyon kullanılamıyor</strong><span>{error || "Model verisi alınamadı."}</span></section></main>;
  }

  return <ProjectionModelView
    projection={projection}
    ticker={resolvedTicker}
    availableTickers={availableTickers}
    onTickerChange={chooseTicker}
    backHref={backHref}
  />;
}
