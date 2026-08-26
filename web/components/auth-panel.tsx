"use client";

import { useIzfinAuth } from "./auth-provider";

export function AuthPanel() {
  const { configured, loading, user, logout } = useIzfinAuth();
  if (!configured) return <p className="auth-note">Giriş ekranı Firebase web yapılandırması eklendiğinde etkinleşecek.</p>;
  if (loading) return <p className="auth-note">Oturum kontrol ediliyor…</p>;
  if (user) return <div className="auth-user"><span>{user.email}</span><button onClick={() => void logout()}>Çıkış yap</button></div>;
  return <div className="auth-home-link"><p>Giriş, kayıt, e-posta doğrulama ve şifre sıfırlama ayrı güvenli ekranda yönetilir.</p><a href="/auth">Giriş veya kayıt ol →</a></div>;
}

