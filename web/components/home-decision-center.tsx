"use client";

import { useEffect, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";
import { IzfinBrandMark } from "./izfin-brand-mark";
import { MarketCenterPanel } from "./market-center";

type ScanHistoryItem = { job_id: string; status: "queued" | "running" | "completed" | "failed"; created_at?: string | null };

export function HomeDecisionCenter() {
  const { user, getIdToken } = useIzfinAuth();
  const [jobId, setJobId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) { setJobId(""); return; }
    let active = true;
    setLoading(true); setError("");
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const history = await izfinApiFetch<{ jobs: ScanHistoryItem[] }>("/api/v1/scan/jobs?limit=12", token);
        const completed = history.jobs.find((item) => item.status === "completed");
        if (active) setJobId(completed?.job_id ?? "");
      } catch {
        if (active) setError("Son tarama özeti şu anda alınamıyor.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [getIdToken, user]);

  return <section className="home-decision" aria-label="IZFIN karar merkezi">
    <div className="home-decision-hero">
      <div><p className="eyebrow">IZFIN SIGNATURE COMMAND CENTER</p><h1>IZFIN Piyasa Merkezi</h1><p>Son taramanın karar dağılımını, piyasa modunu ve en güçlü setup’ı tek bakışta gör.</p></div>
      <IzfinBrandMark className="home-decision-brand-mark" decorative imageSize={72} priority />
    </div>
    {!user && <div className="home-decision-empty"><p className="eyebrow">IZFIN KARAR MERKEZİ</p><h2>Giriş yaptıktan sonra ilk taramanı başlat</h2><p>Karar dağılımı, piyasa modu ve öne çıkan setup bu alanda oluşacak.</p><a className="primary" href="/auth?next=/scan">Giriş yap →</a></div>}
    {user && loading && <p className="home-decision-state" aria-live="polite">Son tarama özeti hazırlanıyor…</p>}
    {user && error && <p className="home-decision-state" role="alert">{error}</p>}
    {user && !loading && !error && !jobId && <div className="home-decision-empty"><p className="eyebrow">IZFIN KARAR MERKEZİ</p><h2>İlk tarama bekleniyor</h2><p>Karar dağılımı, piyasa modu ve öne çıkan setup Akıllı Tarama tamamlandığında burada oluşacak.</p><a className="primary" href="/scan">Akıllı Taramayı Başlat →</a></div>}
    {user && jobId && <MarketCenterPanel jobId={jobId} />}
  </section>;
}
