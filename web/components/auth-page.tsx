"use client";

import { GoogleAuthProvider, createUserWithEmailAndPassword, sendEmailVerification, sendPasswordResetEmail, signInWithEmailAndPassword, signInWithPopup } from "firebase/auth";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { acceptLegalConsent, bootstrapAccount } from "../lib/account";
import { firebaseAuth, firebaseIsConfigured } from "../lib/firebase";
import { useIzfinAuth } from "./auth-provider";

type Mode = "login" | "register" | "reset";

function safeNext(value: string | null): string { return value && value.startsWith("/") && !value.startsWith("//") ? value : "/scan"; }
function validEmail(value: string): boolean { const normalized = value.trim().toLowerCase(); return normalized.includes("@") && normalized.split("@")[1]?.includes("."); }
function validPassword(value: string): boolean { return value.length >= 8 && /[A-ZÇĞİÖŞÜ]/.test(value) && /[a-zçğıöşü]/.test(value) && /\d/.test(value); }
function newChallenge() { return { a: Math.floor(Math.random() * 8) + 2, b: Math.floor(Math.random() * 8) + 2 }; }

export function AuthPage() {
  const router = useRouter(); const search = useSearchParams(); const { loading, user } = useIzfinAuth();
  const [mode, setMode] = useState<Mode>("login"); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [repeat, setRepeat] = useState("");
  const [captcha, setCaptcha] = useState(""); const [challenge, setChallenge] = useState(newChallenge); const [terms, setTerms] = useState(false); const [privacy, setPrivacy] = useState(false);
  const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const next = useMemo(() => safeNext(search.get("next")), [search]);
  useEffect(() => { if (!loading && user) router.replace(next); }, [loading, next, router, user]);

  function switchMode(value: Mode) { setMode(value); setError(""); setMessage(""); }
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    try { if (!email.trim() || !password) throw new Error("E-posta ve şifre gerekli."); await signInWithEmailAndPassword(firebaseAuth(), email.trim().toLowerCase(), password); router.push(next); }
    catch (reason) { setError(reason instanceof Error && reason.message === "E-posta ve şifre gerekli." ? reason.message : "E-posta veya şifre doğrulanamadı."); }
    finally { setBusy(false); }
  }
  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const problems = [!validEmail(email) && "Geçerli bir e-posta girin.", password !== repeat && "Şifreler eşleşmiyor.", !validPassword(password) && "Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.", Number(captcha) !== challenge.a + challenge.b && "Doğrulama işlemi yanlış.", !terms && "Kullanım koşulları onaylanmalı.", !privacy && "KVKK Aydınlatma Metni görüntülenip doğrulanmalı."].filter(Boolean);
    if (problems.length) { setError(problems.join(" ")); setChallenge(newChallenge()); setCaptcha(""); return; }
    setBusy(true);
    try {
      const credential = await createUserWithEmailAndPassword(firebaseAuth(), email.trim().toLowerCase(), password);
      const token = await credential.user.getIdToken();
      await bootstrapAccount(token); await acceptLegalConsent(token); await sendEmailVerification(credential.user);
      setMessage("Hesabın oluşturuldu. Doğrulama bağlantısı e-posta adresine gönderildi."); router.push(next);
    } catch { setError("Hesap oluşturulamadı. E-posta zaten kayıtlı olabilir veya Firebase ayarlarını kontrol etmelisin."); }
    finally { setBusy(false); }
  }
  async function reset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); if (!validEmail(email)) { setError("Geçerli bir e-posta girin."); return; }
    setBusy(true); try { await sendPasswordResetEmail(firebaseAuth(), email.trim().toLowerCase()); setMessage("Şifre sıfırlama bağlantısı e-posta adresine gönderildi."); } catch { setError("Şifre sıfırlama bağlantısı gönderilemedi."); } finally { setBusy(false); }
  }
  async function google() { setError(""); setBusy(true); try { await signInWithPopup(firebaseAuth(), new GoogleAuthProvider()); router.push(next); } catch { setError("Google ile giriş tamamlanamadı."); } finally { setBusy(false); } }

  if (!firebaseIsConfigured()) return <main className="auth-page"><section className="auth-screen-card"><p className="eyebrow">IZFIN HESABI</p><h1>Giriş yapılandırması eksik</h1><p>Firebase web yapılandırması eklendiğinde güvenli giriş etkinleşecek.</p></section></main>;
  return <main className="auth-page"><section className="auth-screen-card"><a className="auth-logo" href="/"><span>I</span><span>Z</span><b>IZFIN</b></a><p className="eyebrow">SIGNATURE INTELLIGENCE</p><h1>{mode === "login" ? "Hoş Geldiniz" : mode === "register" ? "IZFIN hesabını oluştur" : "Şifreni yenile"}</h1><p className="auth-screen-intro">Piyasayı analiz et, fırsatları filtrele, kararını tek merkezden yönet.</p>
    <div className="auth-switch" aria-label="Hesap erişimi"><button className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>Giriş Yap</button><button className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>Kayıt Ol</button></div>
    {message && <p className="auth-screen-message" role="status">{message}</p>}{error && <p className="auth-screen-error" role="alert">{error}</p>}
    {mode === "login" && <form className="auth-screen-form" onSubmit={login}><label>E-posta<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Şifre<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><button disabled={busy} type="submit">{busy ? "Giriş yapılıyor…" : "Giriş Yap"}</button><button className="auth-text-button" type="button" onClick={() => switchMode("reset")}>Şifremi unuttum</button></form>}
    {mode === "register" && <form className="auth-screen-form" onSubmit={register}><label>E-posta<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Şifre<input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} /><small>En az 8 karakter; büyük harf, küçük harf ve rakam içersin.</small></label><label>Şifre tekrar<input type="password" autoComplete="new-password" value={repeat} onChange={(event) => setRepeat(event.target.value)} /></label><label>İnsan doğrulaması: {challenge.a} + {challenge.b} = ?<input inputMode="numeric" value={captcha} onChange={(event) => setCaptcha(event.target.value)} /></label><label className="auth-checkbox"><input type="checkbox" checked={terms} onChange={(event) => setTerms(event.target.checked)} /><span>Kullanım Koşulları&apos;nı kabul ediyorum.</span></label><label className="auth-checkbox"><input type="checkbox" checked={privacy} onChange={(event) => setPrivacy(event.target.checked)} /><span>KVKK Aydınlatma Metni tarafıma sunuldu.</span></label><button disabled={busy} type="submit">{busy ? "Hesap hazırlanıyor…" : "Hesabımı Oluştur"}</button></form>}
    {mode === "reset" && <form className="auth-screen-form" onSubmit={reset}><label>E-posta<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><button disabled={busy} type="submit">{busy ? "Gönderiliyor…" : "Şifre Sıfırlama Bağlantısı Gönder"}</button><button className="auth-text-button" type="button" onClick={() => switchMode("login")}>Giriş ekranına dön</button></form>}
    {mode !== "reset" && <><div className="auth-divider">veya</div><button className="auth-google" disabled={busy} type="button" onClick={() => void google()}>Google ile devam et</button></>}
    <p className="auth-screen-foot">Firebase Auth · kişisel veri alanı · yatırım karar destek platformu</p>
  </section></main>;
}

