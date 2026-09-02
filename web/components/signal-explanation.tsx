type Check = { kod: string; saglandi: boolean; metin: string };
type Audit = { available?: boolean; oncelikli_karar?: boolean; mesaj?: string; ozet?: string; seviyeler?: Record<string, unknown> };

function checks(value: unknown): Check[] {
  return Array.isArray(value) ? value.filter((item): item is Check => item !== null && typeof item === "object" && typeof item.kod === "string" && typeof item.saglandi === "boolean" && typeof item.metin === "string") : [];
}

/** Render the Python gate audit; never infer a decision from client-side scores. */
export function SignalExplanation({ value }: Readonly<{ value: unknown }>) {
  const audit: Audit = value !== null && typeof value === "object" ? value : {};
  if (audit.available !== true) return <p className="scan-decision-note">{typeof audit.mesaj === "string" ? audit.mesaj : "Bu kayıtta ayrıntılı teyit kontrolü bulunmuyor. Kayıtlı merkezi karar geçerlidir."}</p>;
  return <details className="signal-explanation">
    <summary>Neden bu karar? Hangi teyit eksik?</summary>
    <p>{audit.ozet}</p>
    {audit.oncelikli_karar && <p className="signal-priority">Öncelikli risk/kâr koruma kararı uygulanıyor; alım eşikleri tek başına kararı değiştirmez.</p>}
    <p>Bu kontrol tarama anındaki verilere aittir. Erken AL daha az teyit ister; AL ve Güçlü AL için ek koşullar aranır. Güçlü AL, getiri garantisi anlamına gelmez.</p>
    {([ ["ERKEN_AL", "Erken AL"], ["AL", "AL"], ["GUCLU_AL", "Güçlü AL"] ] as const).map(([key, label]) => {
      const items = checks(audit.seviyeler?.[key]);
      if (!items.length) return <p key={key}>{label} için ayrıntılı koşul bilgisi yok.</p>;
      const missing = items.filter((item) => !item.saglandi);
      return <details key={key} className="signal-level">
        <summary>{label} · {missing.length ? `${missing.length} eksik koşul` : "Alım koşulları sağlandı"}</summary>
        <ul>{items.map((item) => <li key={item.kod} className={item.saglandi ? "is-met" : "is-missing"}><b>{item.saglandi ? "Sağlandı" : "Eksik"}:</b> {item.metin}</li>)}</ul>
      </details>;
    })}
  </details>;
}
