"use client";

import {
  GoogleAuthProvider,
  browserLocalPersistence,
  browserSessionPersistence,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { acceptLegalConsent, bootstrapAccount } from "../lib/account";
import { sendIzfinVerificationEmail } from "../lib/auth-verification";
import { firebaseAuth, firebaseIsConfigured } from "../lib/firebase";
import { useIzfinAuth } from "./auth-provider";
import { IzfinBrandMark } from "./izfin-brand-mark";

type Mode = "login" | "register" | "reset";
type AuthField = "email" | "password" | "repeat" | "captcha" | "terms" | "privacy";

const STABLE_IZFIN_HOST = "izfin-web.vercel.app";

function safeNext(value: string | null): string { return value && value.startsWith("/") && !value.startsWith("//") ? value : "/scan"; }
function validEmail(value: string): boolean { const normalized = value.trim().toLowerCase(); return normalized.includes("@") && normalized.split("@")[1]?.includes("."); }
function validPassword(value: string): boolean { return value.length >= 8 && /[A-ZÇĞİÖŞÜ]/.test(value) && /[a-zçğıöşü]/.test(value) && /\d/.test(value); }
function newChallenge() { return { a: Math.floor(Math.random() * 8) + 2, b: Math.floor(Math.random() * 8) + 2 }; }
function firebaseErrorCode(reason: unknown): string {
  if (typeof reason !== "object" || reason === null || !("code" in reason)) return "";
  return String((reason as { code?: unknown }).code ?? "");
}
function googleAuthErrorMessage(reason: unknown): string {
  switch (firebaseErrorCode(reason)) {
    case "auth/unauthorized-domain":
      return `Google girişi bu alan adı için yetkilendirilmemiş. IZFIN'i https://${STABLE_IZFIN_HOST} üzerinden açın; yönetici tarafında bu alan Firebase Authorized domains listesinde olmalı.`;
    case "auth/operation-not-allowed":
      return "Google ile giriş Firebase tarafında etkin değil. Google sağlayıcısının Authentication > Sign-in method bölümünde etkinleştirilmesi gerekiyor.";
    case "auth/popup-blocked":
      return "Tarayıcı Google giriş penceresini engelledi. Bu site için pop-up izni verip tekrar deneyin.";
    case "auth/popup-closed-by-user":
      return "Google giriş penceresi tamamlanmadan kapatıldı. Tekrar deneyebilirsiniz.";
    default:
      return "Google ile giriş tamamlanamadı. Firebase Google sağlayıcısı ve yetkili alan adı ayarlarını kontrol edin.";
  }
}

export function AuthPage() {
  const router = useRouter();
  const search = useSearchParams();
  const { loading, user } = useIzfinAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [captcha, setCaptcha] = useState("");
  const [challenge, setChallenge] = useState(newChallenge);
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [remember, setRemember] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [invalidFields, setInvalidFields] = useState<AuthField[]>([]);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const [busy, setBusy] = useState(false);
  const next = useMemo(() => safeNext(search.get("next")), [search]);
  const deleted = search.get("deleted") === "1";

  useEffect(() => {
    if (!loading && user && !busy) router.replace(next);
  }, [busy, loading, next, router, user]);

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error, invalidFields]);

  function fieldAccessibility(field: AuthField) {
    const invalid = invalidFields.includes(field);
    const hint = field === "password" && mode === "register" ? "password-requirements" : "";
    return {
      "aria-invalid": invalid || undefined,
      "aria-describedby": [hint, invalid && error ? "auth-error" : ""].filter(Boolean).join(" ") || undefined,
    };
  }

  function switchMode(value: Mode) { setMode(value); setError(""); setInvalidFields([]); setMessage(""); }
  async function configurePersistence() {
    await setPersistence(firebaseAuth(), remember ? browserLocalPersistence : browserSessionPersistence);
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setInvalidFields([]); setBusy(true);
    try {
      if (!email.trim() || !password) {
        setInvalidFields([...(!email.trim() ? ["email" as const] : []), ...(!password ? ["password" as const] : [])]);
        throw new Error("E-posta ve şifre gerekli.");
      }
      await configurePersistence();
      await signInWithEmailAndPassword(firebaseAuth(), email.trim().toLowerCase(), password);
      router.push(next);
    } catch (reason) {
      if (["auth/invalid-credential", "auth/wrong-password", "auth/user-not-found", "auth/invalid-email"].includes(firebaseErrorCode(reason))) setInvalidFields(["email", "password"]);
      setError(reason instanceof Error && reason.message === "E-posta ve şifre gerekli." ? reason.message : "E-posta veya şifre doğrulanamadı.");
    } finally { setBusy(false); }
  }

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setInvalidFields([]);
    const problems: Partial<Record<AuthField, string>> = {};
    if (!validEmail(email)) problems.email = "Geçerli bir e-posta girin.";
    if (password !== repeat) problems.repeat = "Şifreler eşleşmiyor.";
    if (!validPassword(password)) problems.password = "Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.";
    if (Number(captcha) !== challenge.a + challenge.b) problems.captcha = "Doğrulama işlemi yanlış.";
    if (!terms) problems.terms = "Kullanım koşulları onaylanmalı.";
    if (!privacy) problems.privacy = "KVKK Aydınlatma Metni görüntülenip doğrulanmalı.";
    if (Object.keys(problems).length) {
      setInvalidFields(Object.keys(problems) as AuthField[]);
      setError(Object.values(problems).join(" ")); setChallenge(newChallenge()); setCaptcha(""); return;
    }
    setBusy(true);
    try {
      await configurePersistence();
      const credential = await createUserWithEmailAndPassword(firebaseAuth(), email.trim().toLowerCase(), password);
      const token = await credential.user.getIdToken();
      await bootstrapAccount(token);
      await acceptLegalConsent(token);
      await sendIzfinVerificationEmail(credential.user);
      setMessage("Hesabın oluşturuldu. Doğrulama bağlantısı e-posta adresine gönderildi.");
      router.push(next);
    } catch {
      setError("Hesap oluşturulamadı. E-posta zaten kayıtlı olabilir veya Firebase ayarlarını kontrol etmelisin.");
    } finally { setBusy(false); }
  }

  async function reset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setInvalidFields([]);
    if (!validEmail(email)) { setInvalidFields(["email"]); setError("Geçerli bir e-posta girin."); return; }
    setBusy(true);
    try { await sendPasswordResetEmail(firebaseAuth(), email.trim().toLowerCase()); setMessage("Şifre sıfırlama bağlantısı e-posta adresine gönderildi."); }
    catch { setError("Şifre sıfırlama bağlantısı gönderilemedi."); }
    finally { setBusy(false); }
  }

  async function google() {
    setError(""); setInvalidFields([]); setBusy(true);
    try {
      await configurePersistence();
      const credential = await signInWithPopup(firebaseAuth(), new GoogleAuthProvider());
      const token = await credential.user.getIdToken();
      await bootstrapAccount(token);
      router.push(next);
    } catch (reason) {
      setError(googleAuthErrorMessage(reason));
    } finally { setBusy(false); }
  }

  if (!firebaseIsConfigured()) return <main className="auth-page"><section className="auth-screen-card"><p className="eyebrow">IZFIN HESABI</p><h1>Giriş yapılandırması eksik</h1><p>Firebase web yapılandırması eklendiğinde güvenli giriş etkinleşecek.</p></section></main>;
  return <main className="auth-page"><section className="auth-screen-card"><a className="auth-logo" href="/"><IzfinBrandMark priority /><span><b>IZFIN</b><small>ANALYZE · PREDICT · INVEST</small></span></a><p className="eyebrow">SIGNATURE INTELLIGENCE</p><h1>{mode === "login" ? "Hoş Geldiniz" : mode === "register" ? "IZFIN hesabını oluştur" : "Şifreni yenile"}</h1><p className="auth-screen-intro">Piyasayı analiz et, fırsatları filtrele, kararını tek merkezden yönet.</p>
    <div className="auth-switch" aria-label="Hesap erişimi"><button className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>Giriş Yap</button><button className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>Kayıt Ol</button></div>
    {deleted && <p className="auth-screen-message" role="status">Hesabın ve kullanıcı verilerin kalıcı olarak silindi.</p>}
    {message && <p className="auth-screen-message" role="status">{message}</p>}{error && <p className="auth-screen-error" id="auth-error" ref={errorRef} role="alert" tabIndex={-1}>{error}</p>}
    {mode !== "reset" ? <label className="auth-checkbox auth-remember"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /><span>Beni hatırla</span></label> : null}
    {mode === "login" && <form className="auth-screen-form" onSubmit={login}><label>E-posta<input type="email" autoComplete="email" {...fieldAccessibility("email")} value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Şifre<input type="password" autoComplete="current-password" {...fieldAccessibility("password")} value={password} onChange={(event) => setPassword(event.target.value)} /></label><button disabled={busy} type="submit">{busy ? "Giriş yapılıyor…" : "Giriş Yap"}</button><button className="auth-text-button" type="button" onClick={() => switchMode("reset")}>Şifremi unuttum</button></form>}
    {mode === "register" && <form className="auth-screen-form" onSubmit={register}><label>E-posta<input type="email" autoComplete="email" {...fieldAccessibility("email")} value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Şifre<input type="password" autoComplete="new-password" {...fieldAccessibility("password")} value={password} onChange={(event) => setPassword(event.target.value)} /><small id="password-requirements">En az 8 karakter; büyük harf, küçük harf ve rakam içersin.</small></label><label>Şifre tekrar<input type="password" autoComplete="new-password" {...fieldAccessibility("repeat")} value={repeat} onChange={(event) => setRepeat(event.target.value)} /></label><label>İnsan doğrulaması: {challenge.a} + {challenge.b} = ?<input inputMode="numeric" {...fieldAccessibility("captcha")} value={captcha} onChange={(event) => setCaptcha(event.target.value)} /></label><label className="auth-checkbox"><input type="checkbox" {...fieldAccessibility("terms")} checked={terms} onChange={(event) => setTerms(event.target.checked)} /><span><a href="/legal/terms" target="_blank" rel="noreferrer">Kullanım Koşulları</a>&apos;nı okudum ve kabul ediyorum.</span></label><label className="auth-checkbox"><input type="checkbox" {...fieldAccessibility("privacy")} checked={privacy} onChange={(event) => setPrivacy(event.target.checked)} /><span><a href="/legal/privacy" target="_blank" rel="noreferrer">KVKK Aydınlatma Metni</a> tarafıma sunuldu.</span></label><button disabled={busy} type="submit">{busy ? "Hesap hazırlanıyor…" : "Hesabımı Oluştur"}</button></form>}
    {mode === "reset" && <form className="auth-screen-form" onSubmit={reset}><label>E-posta<input type="email" autoComplete="email" {...fieldAccessibility("email")} value={email} onChange={(event) => setEmail(event.target.value)} /></label><button disabled={busy} type="submit">{busy ? "Gönderiliyor…" : "Şifre Sıfırlama Bağlantısı Gönder"}</button><button className="auth-text-button" type="button" onClick={() => switchMode("login")}>Giriş ekranına dön</button></form>}
    {mode !== "reset" && <><div className="auth-divider">veya</div><button className="auth-google" disabled={busy} type="button" onClick={() => void google()}>Google ile devam et</button></>}
    <p className="auth-screen-foot">Firebase Auth · kişisel veri alanı · yatırım karar destek platformu</p>
  </section></main>;
}
