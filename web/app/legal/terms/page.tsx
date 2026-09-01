"use client";

import { useEffect, useState } from "react";
import { fetchLegalDocument, legalTermsPath, type LegalDocumentResponse } from "../../../lib/account";
import { IzfinBrandMark } from "../../../components/izfin-brand-mark";
import { LegalMarkdown } from "../../../components/legal-markdown";

export default function LegalTermsPage() {
  const [document, setDocument] = useState<LegalDocumentResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchLegalDocument(legalTermsPath())
      .then((value) => { if (active) setDocument(value); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);

  return <main className="legal-public-page">
    <article className="legal-public-card">
      <a className="legal-public-brand" href="/auth"><IzfinBrandMark priority /><span><b>IZFIN</b><small>KULLANIM KOŞULLARI</small></span></a>
      {error ? <><h1>Kullanım Koşulları yüklenemedi</h1><p>Metin şu anda alınamadı. Sayfayı yenileyip tekrar deneyebilirsin.</p></> : !document ? <><h1>Kullanım Koşulları</h1><p>Güncel metin yükleniyor…</p></> : <>
        <div className="legal-public-head"><p className="eyebrow">GÜNCEL SÜRÜM</p><span>{document.version}</span></div>
        <LegalMarkdown markdown={document.markdown} />
      </>}
      <a className="legal-public-back" href="/auth">Giriş / kayıt ekranına dön</a>
    </article>
  </main>;
}
