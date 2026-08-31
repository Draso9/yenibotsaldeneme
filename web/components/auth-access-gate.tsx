"use client";

import { sendEmailVerification } from "firebase/auth";
import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { acceptLegalConsent, bootstrapAccount, fetchLegalConsent } from "../lib/account";
import { IzfinBrandMark } from "./izfin-brand-mark";
import { useIzfinAuth } from "./auth-provider";

type GateState = "checking" | "verification" | "consent" | "error" | "ready";

export function AuthAccessGate({ children }: Readonly<{ children: React.ReactNode }>) {
  const { loading, user, getIdToken, logout } = useIzfinAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<GateState>("checking");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacySeen, setPrivacySeen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const checkAccess = useCallback(async () => {
    if (loading) return;
    if (!user) {
      const next = pathname.startsWith("/") ? pathname : "/scan";
      router.replace(`/auth?next=${encodeURIComponent(next)}`);
      setState("checking");
      return;
    }
    if (!user.emailVerified) {
      setState("verification");
      return;
    }

    setState("checking");
    setMessage("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Oturum anahtarı alınamadı.");
      await bootstrapAccount(token);
      const consent = await fetchLegalConsent(token);
      setState(consent.accepted ? "ready" : "consent");
    } catch {
      setState("error");
    }
  }, [getIdToken, loading, pathname, router, user]);

  useEffect(() => {
    void checkAccess();
  }, [checkAccess]);

  async function handleLogout() {
    if (busy) return;
    setBusy(true);
    try {
      await logout();
      router.replace("/auth");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    if (!user || busy) return;
    setBusy(true);
    setMessage("");
    try {
      await sendEmailVerification(user);
      setMessage("Doğrulama bağlantısı yeniden gönderildi. E-postanı kontrol et.");
    } catch {
      setMessage("Doğrulama bağlantısı gönderilemedi. Biraz sonra tekrar deneyebilirsin.");
    } finally {
      setBusy(false);
    }
  }

  async function recheckVerification() {
    if (!user || busy) return;
    setBusy(true);
    setMessage("");
    try {
      await user.reload();
      if (user.emailVerified) {
        await checkAccess();
      } else {
        setState("verification");
        setMessage("E-posta henüz doğrulanmış görünmüyor.");
      }
    } catch {
      setMessage("Doğrulama durumu kontrol edilemedi. Tekrar deneyebilirsin.");
    } finally {
      setBusy(false);
    }
  }

  async function recordConsent() {
    if (!termsAccepted || !privacySeen || busy) return;
    setBusy(true);
    setMessage("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Oturum anahtarı alınamadı.");
      const consent = await acceptLegalConsent(token);
      setState(consent.accepted ? "ready" : "consent");
    } catch {
      setState("error");
    } finally {
      setBusy(false);
    }
  }

  if (loading || state === "checking" || !user) {
    return <GateFrame title="Hesabın kontrol ediliyor" text="Kimlik, hesap başlangıcı ve güncel yasal onay güvenli biçimde doğrulanıyor." />;
  }

  if (state === "verification") {
    return <GateFrame title="E-posta doğrulaması gerekli" text="Şifreyle oluşturulan hesabınla devam etmeden önce e-posta adresini doğrulamalısın.">
      {message ? <p className="auth-gate-message" role="status">{message}</p> : null}
      <div className="auth-gate-actions">
        <button disabled={busy} onClick={() => void recheckVerification()} type="button">Doğrulamayı Kontrol Et</button>
        <button className="secondary" disabled={busy} onClick={() => void resendVerification()} type="button">E-postayı Yeniden Gönder</button>
        <button className="text" disabled={busy} onClick={() => void handleLogout()} type="button">Çıkış Yap</button>
      </div>
    </GateFrame>;
  }

  if (state === "error") {
    return <GateFrame title="Yasal onay durumu kontrol edilemedi" text="Güvenliğiniz için onay durumu doğrulanmadan IZFIN çalışma alanı açılmaz.">
      <div className="auth-gate-actions">
        <button disabled={busy} onClick={() => void checkAccess()} type="button">Tekrar Dene</button>
        <button className="text" disabled={busy} onClick={() => void handleLogout()} type="button">Çıkış Yap</button>
      </div>
    </GateFrame>;
  }

  if (state === "consent") {
    return <GateFrame title="Güncel yasal onay gerekli" text="Devam etmeden önce güncel Kullanım Koşulları ve KVKK Aydınlatma Metni'ni açıkça inceleyip onaylamalısın.">
      <div className="auth-gate-legal-links">
        <a href="/legal/terms" target="_blank" rel="noreferrer">Kullanım Koşullarını Aç</a>
        <a href="/legal/privacy" target="_blank" rel="noreferrer">KVKK Metnini Aç</a>
      </div>
      <label className="auth-gate-check"><input checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} type="checkbox" /><span>Güncel Kullanım Koşulları'nı okudum ve kabul ediyorum.</span></label>
      <label className="auth-gate-check"><input checked={privacySeen} onChange={(event) => setPrivacySeen(event.target.checked)} type="checkbox" /><span>Güncel KVKK Aydınlatma Metni tarafıma sunuldu.</span></label>
      <div className="auth-gate-actions">
        <button disabled={busy || !termsAccepted || !privacySeen} onClick={() => void recordConsent()} type="button">Onayla ve IZFIN'e Devam Et</button>
        <button className="text" disabled={busy} onClick={() => void handleLogout()} type="button">Çıkış Yap</button>
      </div>
    </GateFrame>;
  }

  return <>{children}</>;
}

function GateFrame({ title, text, children }: Readonly<{ title: string; text: string; children?: React.ReactNode }>) {
  return <main className="auth-gate-page">
    <section className="auth-gate-card" aria-live="polite">
      <IzfinBrandMark priority />
      <p className="eyebrow">IZFIN GÜVENLİ ERİŞİM</p>
      <h1>{title}</h1>
      <p>{text}</p>
      {children}
    </section>
  </main>;
}
