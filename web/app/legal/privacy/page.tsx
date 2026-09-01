"use client";

import { useEffect, useState } from "react";
import { fetchLegalDocument, legalPrivacyPath, type LegalDocumentResponse } from "../../../lib/account";
import { IzfinBrandMark } from "../../../components/izfin-brand-mark";
import { LegalMarkdown } from "../../../components/legal-markdown";

export default function LegalPrivacyPage() {
  const [document, setDocument] = useState<LegalDocumentResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchLegalDocument(legalPrivacyPath())
      .then((value) => { if (active) setDocument(value); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);

  return <main className="legal-public-page">
    <article className="legal-public-card">
      <a className="legal-public-brand" href="/auth"><IzfinBrandMark priority /><span><b>IZFIN</b><small>KVKK AYDINLATMA METNİ</small></span></a>
      {error ? <><h1>KVKK Aydınlatma Metni yüklenemedi</h1><p>Metin şu anda alınamadı. Sayfayı yenileyip tekrar deneyebilirsin.</p></> : !document ? <><h1>KVKK Aydınlatma Metni</h1><p>Güncel metin yükleniyor…</p></> : <>
        <div className="legal-public-head"><p className="eyebrow">GÜNCEL SÜRÜM</p><span>{document.version}</span></div>
        {document.warning ? <p className="legal-public-warning">{document.warning}</p> : null}
        {document.info ? <p className="legal-public-info">{document.info}</p> : null}
        <LegalMarkdown markdown={document.markdown} />
      </>}
      <a className="legal-public-back" href="/auth">Giriş / kayıt ekranına dön</a>
    </article>
  </main>;
}
