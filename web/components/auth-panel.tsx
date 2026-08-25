"use client";

import { signInWithEmailAndPassword } from "firebase/auth";
import { FormEvent, useState } from "react";
import { firebaseAuth } from "../lib/firebase";
import { useIzfinAuth } from "./auth-provider";

export function AuthPanel() {
  const { configured, loading, user, logout } = useIzfinAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { await signInWithEmailAndPassword(firebaseAuth(), email.trim(), password); }
    catch { setError("E-posta veya şifre doğrulanamadı."); }
    finally { setSubmitting(false); }
  }
  if (!configured) return <p className="auth-note">Giriş ekranı Firebase web yapılandırması eklendiğinde etkinleşecek.</p>;
  if (loading) return <p className="auth-note">Oturum kontrol ediliyor…</p>;
  if (user) return <div className="auth-user"><span>{user.email}</span><button onClick={() => void logout()}>Çıkış yap</button></div>;
  return <form className="auth-form" onSubmit={submit}>
    <label>E-posta<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
    <label>Şifre<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={submitting}>{submitting ? "Giriş yapılıyor…" : "Giriş yap"}</button>
  </form>;
}
