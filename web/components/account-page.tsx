"use client";

import { useEffect, useState } from "react";
import {
  acceptLegalConsent,
  deleteAccount,
  fetchAccountExport,
  fetchLegalConsent,
  fetchLegalDocument,
  fetchProfile,
  legalPrivacyPath,
  legalTermsPath,
  type LegalConsentResponse,
  type LegalDocumentResponse,
  type ProfileResponse,
} from "../lib/account";
import { useIzfinAuth } from "./auth-provider";

type Tab = "privacy" | "terms" | "export" | "delete";
const DELETE_PHRASE = "HESABIMI KALICI OLARAK SİL";

function LegalText({ document }: Readonly<{ document: LegalDocumentResponse | null }>) {
  if (!document) return <p className="account-muted">Belge yükleniyor…</p>;
  const blocks = document.markdown.split("\n").map((line) => line.trim()).filter(Boolean);
  return <div className="account-legal-copy">
    {document.warning && <div className="account-warning">{document.warning}</div>}
    {blocks.map((line, index) => {
      if (line.startsWith("### ")) return <h3 key={`${line}-${index}`}>{line.slice(4)}</h3>;
      if (line.startsWith("- ")) return <p className="account-list-line" key={`${line}-${index}`}>• {line.slice(2).replaceAll("**", "")}</p>;
      return <p key={`${line}-${index}`}>{line.replaceAll("**", "")}</p>;
    })}
    {document.info && <div className="account-info">{document.info}</div>}
  </div>;
}

export function AccountPage() {
  const { loading, user, getIdToken, logout } = useIzfinAuth();
  const [tab, setTab] = useState<Tab>("privacy");
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [consent, setConsent] = useState<LegalConsentResponse | null>(null);
  const [privacy, setPrivacy] = useState<LegalDocumentResponse | null>(null);
  const [terms, setTerms] = useState<LegalDocumentResponse | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [deleteEmail, setDeleteEmail] = useState("");
  const [deletePhrase, setDeletePhrase] = useState("");
  const [irreversible, setIrreversible] = useState(false);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetchLegalDocument(legalPrivacyPath()),
      fetchLegalDocument(legalTermsPath()),
    ]).then(([privacyDoc, termsDoc]) => {
      if (active) { setPrivacy(privacyDoc); setTerms(termsDoc); }
    }).catch(() => { if (active) setMessage("Yasal belgeler şu anda yüklenemedi."); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (loading || !user) { setProfile(null); setConsent(null); return; }
    let active = true;
    void (async () => {
      try {
        const token = await getIdToken();
        if (!token) return;
        const [nextProfile, nextConsent] = await Promise.all([
          fetchProfile(token),
          fetchLegalConsent(token),
        ]);
        if (active) { setProfile(nextProfile); setConsent(nextConsent); setDeleteEmail(nextProfile.email); }
      } catch { if (active) setMessage("Hesap bilgileri şu anda yüklenemedi."); }
    })();
    return () => { active = false; };
  }, [getIdToken, loading, user]);

  async function handleConsent() {
    setBusy(true); setMessage("");
    try {
      const token = await getIdToken(); if (!token) return;
      setConsent(await acceptLegalConsent(token));
      setMessage("Kullanım koşulları ve KVKK bilgilendirme kaydı güncellendi.");
    } catch { setMessage("Yasal onay kaydedilemedi."); }
    finally { setBusy(false); }
  }

  async function handleExport() {
    setBusy(true); setMessage("");
    try {
      const token = await getIdToken(); if (!token) return;
      const data = await fetchAccountExport(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `izfin-verilerim-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Kişisel veri paketin hazırlandı.");
    } catch { setMessage("Veri paketi indirilemedi."); }
    finally { setBusy(false); }
  }

  async function handleDelete() {
    if (!user) return;
    setBusy(true); setMessage("");
    try {
      const token = await getIdToken(); if (!token) return;
      const result = await deleteAccount(token, {
        email: deleteEmail,
        confirmation_phrase: deletePhrase,
        irreversible,
      });
      await logout();
      setMessage(`Hesap ve ${result.deleted_documents} kullanıcı veri belgesi kalıcı olarak silindi.`);
    } catch { setMessage("Silme işlemi tamamlanamadı. Onay alanlarını kontrol edip yeniden deneyin."); }
    finally { setBusy(false); }
  }

  const signedIn = Boolean(user);

  return <main className="account-page" aria-label="Gizlilik ve hesap merkezi">
    <section className="account-page-hero">
      <div><p className="eyebrow">GÜVEN & ŞEFFAFLIK</p><h1>Gizlilik & Hesap</h1><p className="account-muted">Yasal metinleri incele, sürümlü onayını yönet, verilerini indir veya hesabını kalıcı olarak sil.</p></div>
      <div className="account-identity-card">
        <span>OTURUM</span><strong>{profile?.email ?? (loading ? "Hazırlanıyor…" : "Giriş yapılmadı")}</strong>
        <small>{consent ? `Yasal onay · ${consent.accepted ? "güncel" : "bekliyor"}` : "Hesap işlemleri güvenli oturum gerektirir"}</small>
      </div>
    </section>

    <nav className="account-tabs" aria-label="Hesap bölümleri">
      {([
        ["privacy", "KVKK & Gizlilik"], ["terms", "Kullanım Koşulları"], ["export", "Verilerimi İndir"], ["delete", "Hesabı Sil"],
      ] as Array<[Tab, string]>).map(([key, label]) => <button className={tab === key ? "active" : ""} key={key} onClick={() => { setTab(key); setMessage(""); }}>{label}</button>)}
    </nav>

    {message && <div className="account-message" role="status">{message}</div>}

    <section className="account-layout">
      <article className="account-panel account-main-panel">
        {tab === "privacy" && <><div className="account-section-head"><div><p className="eyebrow">VERİ ŞEFFAFLIĞI</p><h2>KVKK Aydınlatma Metni</h2></div><span>{privacy?.version ?? "—"}</span></div><LegalText document={privacy} /></>}
        {tab === "terms" && <><div className="account-section-head"><div><p className="eyebrow">HİZMET ÇERÇEVESİ</p><h2>Kullanım Koşulları</h2></div><span>{terms?.version ?? "—"}</span></div><LegalText document={terms} /></>}
        {tab === "export" && <div className="account-action-copy"><p className="eyebrow">VERİ TAŞINABİLİRLİĞİ</p><h2>Kişisel verilerinin bir kopyasını al</h2><p>Profil, kişisel listeler ve hesabına bağlı kullanıcı belgeleri JSON paketi olarak hazırlanır.</p>{signedIn ? <button className="account-primary" disabled={busy} onClick={() => void handleExport()}>{busy ? "Hazırlanıyor…" : "Verilerimi indir"}</button> : <p className="account-warning">Veri paketi için önce giriş yapmalısın.</p>}</div>}
        {tab === "delete" && <div className="account-delete-zone"><p className="eyebrow">GERİ ALINAMAZ İŞLEM</p><h2>Hesabı ve kullanıcı verilerini kalıcı sil</h2><p>Firebase hesabın, kişisel listen, aktif sinyallerin ve performans geçmişin kaldırılır. Önce veri paketini indirmen önerilir.</p>{signedIn ? <div className="account-delete-form"><label>E-posta adresin<input value={deleteEmail} onChange={(event) => setDeleteEmail(event.target.value)} /></label><label>Onay ifadesi<input placeholder={DELETE_PHRASE} value={deletePhrase} onChange={(event) => setDeletePhrase(event.target.value)} /></label><label className="account-check"><input type="checkbox" checked={irreversible} onChange={(event) => setIrreversible(event.target.checked)} /><span>Bu işlemin geri alınamaz olduğunu anlıyorum.</span></label><button className="account-danger" disabled={busy || deletePhrase !== DELETE_PHRASE || !irreversible} onClick={() => void handleDelete()}>{busy ? "Siliniyor…" : "Hesabımı kalıcı olarak sil"}</button></div> : <p className="account-warning">Hesap silme için önce giriş yapmalısın.</p>}</div>}
      </article>

      <aside className="account-side">
        <section className="account-panel"><p className="eyebrow">ONAY DURUMU</p><h3>{consent?.accepted ? "Belgeler güncel" : "Onay bekleniyor"}</h3><p>{consent ? `Koşul ${consent.terms_version} · KVKK ${consent.privacy_version}` : "Giriş yaptıktan sonra mevcut onay kaydın burada görünür."}</p>{signedIn && !consent?.accepted && <button className="account-secondary" disabled={busy} onClick={() => void handleConsent()}>Belgeleri okudum, onayı kaydet</button>}</section>
        <section className="account-panel"><p className="eyebrow">HESAP GÜVENLİĞİ</p><h3>Kimlik sınırı</h3><p>Hesap işlemleri Firebase ID token ile doğrulanır; silme çağrısı yalnızca doğrulanmış kullanıcının kendi UID ve e-postasıyla çalışır.</p></section>
      </aside>
    </section>
  </main>;
}
