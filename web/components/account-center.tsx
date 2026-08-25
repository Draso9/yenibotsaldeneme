"use client";

import { useEffect, useState } from "react";
import { izfinApiFetch } from "../lib/api";
import { useIzfinAuth } from "./auth-provider";

type Profile = { uid: string; email: string; profile: Record<string, unknown> };
type Consent = { terms_version: string; privacy_version: string; accepted: boolean };
type ExportPackage = { export_schema: string; exported_at: string; collections: Record<string, unknown[]> };

export function AccountCenter() {
  const { user, getIdToken } = useIzfinAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [consent, setConsent] = useState<Consent | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!user) { setProfile(null); setConsent(null); return; }
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken(); if (!token) return;
        const [nextProfile, nextConsent] = await Promise.all([
          izfinApiFetch<Profile>("/api/v1/profile", token),
          izfinApiFetch<Consent>("/api/v1/legal/consent", token),
        ]);
        if (active) { setProfile(nextProfile); setConsent(nextConsent); }
      } catch { if (active) setMessage("Hesap bilgileri şu anda yüklenemedi."); }
    })();
    return () => { active = false; };
  }, [getIdToken, user]);

  async function acceptTerms() {
    try {
      const token = await getIdToken(); if (!token) return;
      const updated = await izfinApiFetch<Consent>("/api/v1/legal/consent", token, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ terms_accepted: true, privacy_notice_seen: true }),
      });
      setConsent(updated); setMessage("Yasal onay kaydedildi.");
    } catch { setMessage("Yasal onay kaydedilemedi."); }
  }

  async function downloadExport() {
    try {
      const token = await getIdToken(); if (!token) return;
      const data = await izfinApiFetch<ExportPackage>("/api/v1/account/export", token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob); const link = document.createElement("a");
      link.href = url; link.download = "izfin-hesap-verisi.json"; link.click(); URL.revokeObjectURL(url);
    } catch { setMessage("Veri paketi indirilemedi."); }
  }

  if (!user) return null;
  return <section className="account-center" aria-label="Hesap merkezi">
    <div className="section-heading"><div><p className="eyebrow">HESAP</p><h2>Hesap merkezim</h2></div><span className="section-index">04</span></div>
    <div className="account-status-row">
      {profile && <p className="account-email">{profile.email}</p>}
      {consent && <span className={`consent-pill${consent.accepted ? " is-current" : ""}`}>Yasal onay · {consent.accepted ? "güncel" : "bekliyor"}</span>}
    </div>
    <div className="account-actions"><button onClick={() => void acceptTerms()}>Yasal onayı güncelle</button><button onClick={() => void downloadExport()}>Verilerimi indir</button></div>
    {message && <p className="account-message">{message}</p>}
  </section>;
}
