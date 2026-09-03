"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchPerformancePositions,
  fetchPerformanceScorecard,
  refreshPerformance,
  type PerformancePositionsResponse,
  type PerformanceScorecardResponse,
} from "../lib/performance";
import { useIzfinAuth } from "./auth-provider";
import {
  PerformancePositionTrackingView,
  PerformanceScorecardView,
} from "./performance-view";

const PERIODS = [1, 5, 10, 20, 45] as const;

export function PerformancePage() {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(20);
  const [scorecard, setScorecard] = useState<PerformanceScorecardResponse | null>(null);
  const [tracking, setTracking] = useState<PerformancePositionsResponse | null>(null);
  const [scoreError, setScoreError] = useState("");
  const [trackingError, setTrackingError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState("");

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    setTrackingError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchPerformancePositions(token);
        if (active) setTracking(result);
      } catch {
        if (active) setTrackingError("Pozisyon takibi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, refreshKey, user]);

  useEffect(() => {
    if (loading || !user) return;
    let active = true;
    setScoreError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const result = await fetchPerformanceScorecard(token, days);
        if (active) setScorecard(result);
      } catch {
        if (active) setScoreError("Performans karnesi şu anda yüklenemedi.");
      }
    })();
    return () => { active = false; };
  }, [days, getIdToken, loading, refreshKey, user]);

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshMessage("Performans verileri yenileniyor…");
    try {
      const token = await getIdToken(true);
      if (!token) {
        setRefreshMessage("Oturum doğrulanamadığı için performans verileri yenilenemedi.");
        return;
      }

      const result = await refreshPerformance(token);
      if (result.status === "updated") {
        setRefreshMessage(result.message || "Performans verileri güncellendi.");
        setRefreshKey((value) => value + 1);
      } else if (result.status === "already_current") {
        setRefreshMessage(result.message || "Performans verileri zaten güncel.");
        setRefreshKey((value) => value + 1);
      } else if (result.status === "in_progress") {
        setRefreshMessage(result.message || "Performans yenilemesi zaten devam ediyor.");
      } else if (result.status === "source_error") {
        setRefreshMessage(result.message || "Veri kaynağına ulaşılamadı; mevcut performans geçmişi korunuyor.");
      }
    } catch {
      setRefreshMessage("Performans verileri yenilenemedi; mevcut performans geçmişi korunuyor.");
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return <main className="performance-page"><section className="performance-panel performance-status" aria-live="polite"><strong>Güvenli oturum hazırlanıyor</strong><span>Performans verin hesabınla eşleştiriliyor.</span></section></main>;
  }

  if (!user) {
    return <main className="performance-page"><section className="performance-panel performance-empty"><p className="eyebrow">TAKİP & PERFORMANS</p><h1>Performans Merkezi</h1><p>Bu ekranı görmek için IZFIN hesabınla giriş yap.</p><Link href="/">Ana sayfaya dön →</Link></section></main>;
  }

  return <main className="performance-page" aria-label="IZFIN takip ve performans merkezi">
    <div className="performance-path"><Link href="/">← Piyasa Merkezi</Link><span>Hesap verileri / Performans</span></div>
    <section className="performance-hero">
      <div><p className="eyebrow">TAKİP & PERFORMANS</p><h1>Performans Merkezi</h1><p className="performance-muted">Aktif alım dönemlerini, kapanmış pozisyon geçmişini ve IZFIN sinyal karnesini tek ekranda izle.</p></div>
      <div className="performance-hero-actions"><div className="performance-period" aria-label="Ölçüm dönemi">{PERIODS.map((period) => <button className={days === period ? "active" : ""} key={period} onClick={() => setDays(period)}>{period}G</button>)}</div><button className="performance-refresh" type="button" disabled={refreshing} onClick={handleRefresh}>{refreshing ? "↻ Yenileniyor…" : "↻ Verileri yenile"}</button></div>
    </section>

    {refreshMessage && <section className="performance-panel performance-status" aria-live="polite"><strong>{refreshing ? "Performans verileri yenileniyor" : "Yenileme durumu"}</strong><span>{refreshMessage}</span></section>}

    {!tracking && !trackingError && <section className="performance-panel performance-status" aria-live="polite"><strong>Pozisyon takibi hazırlanıyor</strong><span>Aktif ve kapanmış sinyal dönemleri yükleniyor.</span></section>}
    {trackingError && <section className="performance-panel performance-status" role="alert"><strong>Pozisyon takibi kullanılamıyor</strong><span>{trackingError}</span></section>}
    {tracking && <PerformancePositionTrackingView tracking={tracking} />}

    {!scorecard && !scoreError && <section className="performance-panel performance-status" aria-live="polite"><strong>Karne hazırlanıyor</strong><span>{days} günlük sinyal ölçümü hesaplanıyor.</span></section>}
    {scoreError && <section className="performance-panel performance-status" role="alert"><strong>Performans karnesi kullanılamıyor</strong><span>{scoreError}</span></section>}
    {scorecard && <PerformanceScorecardView scorecard={scorecard} />}
  </main>;
}