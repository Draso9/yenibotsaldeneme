type PerformanceRow = Record<string, unknown>;

type PerformanceMobileCardsProps = {
  rows: PerformanceRow[];
  variant: "active" | "closed";
  onInspectClosed?: (index: number) => void;
};

function display(value: unknown) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function percent(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return `${numeric > 0 ? "+" : ""}${numeric.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}%`;
}

export function PerformanceMobileCards({ rows, variant, onInspectClosed }: PerformanceMobileCardsProps) {
  return <div className="performance-mobile-cards" aria-label={variant === "active" ? "Aktif pozisyon kartları" : "Kapanmış pozisyon kartları"}>
    {rows.map((row, index) => <article className="performance-panel performance-mobile-card" key={`${display(row["Varlık"])}-${index}`}>
      <div className="performance-mobile-card-head">
        <span><small>VARLIK</small><strong>{display(row["Varlık"])}</strong></span>
        <span><small>K/Z</small><strong>{percent(row["Kâr / Zarar %"])}</strong></span>
      </div>
      {variant === "active" ? <dl>
        <div><dt>İlk alım</dt><dd>{display(row["İlk Alım Tarihi"])}</dd></div>
        <div><dt>Güncel sinyal</dt><dd>{display(row["Güncel Sinyal"])}</dd></div>
        <div><dt>Geçen gün</dt><dd>{display(row["Geçen Gün"])}</dd></div>
        <div><dt>Durum</dt><dd>{display(row.Durum)}</dd></div>
      </dl> : <>
        <dl>
          <div><dt>Kapanış</dt><dd>{display(row["Kapanış Tarihi"])}</dd></div>
          <div><dt>Neden</dt><dd>{display(row["Kapanış Nedeni"])}</dd></div>
          <div><dt>Pozisyonda gün</dt><dd>{display(row["Pozisyonda Gün"])}</dd></div>
          <div><dt>Son sinyal</dt><dd>{display(row["Son Alım Sinyali"])}</dd></div>
        </dl>
        {onInspectClosed ? <button type="button" onClick={() => onInspectClosed(index)}>Dönemi incele</button> : null}
      </>}
    </article>)}
  </div>;
}
