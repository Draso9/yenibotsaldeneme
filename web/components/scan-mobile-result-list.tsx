type ScanResultRow = Record<string, unknown>;

type ScanMobileResultListProps = {
  rows: ScanResultRow[];
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
};

const secondaryFields = [
  "Fiyat",
  "Güven",
  "🎯 Giriş Kalitesi",
  "MTF Uyum",
  "Para Akışı",
  "PEG / Değerleme",
  "Seans Dışı",
] as const;

function display(value: unknown) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

export function ScanMobileResultList({ rows, selectedTicker, onSelectTicker }: ScanMobileResultListProps) {
  return <div className="scan-mobile-result-list" aria-label="Mobil tarama sonuçları">
    {rows.map((row, index) => {
      const symbol = display(row["Varlık"]).trim().toUpperCase();
      const profile = display(row["Teknik Profil"]);
      return <article className={`scan-mobile-result-card${selectedTicker === symbol ? " is-selected" : ""}`} key={`${symbol}-${index}`}>
        <button className="scan-mobile-primary" type="button" onClick={() => onSelectTicker(symbol)}>
          <span><small>HİSSE</small><strong>{symbol}</strong></span>
          <span><small>KARAR</small><strong>{display(row["Nihai Sinyal"])}</strong></span>
          <span><small>SKOR</small><strong>{display(row["Gelişmiş Skor"])}</strong></span>
          <span><small>RİSK</small><strong>{display(row["Risk"])}</strong></span>
        </button>
        <details className="scan-mobile-secondary">
          <summary>Diğer göstergeler</summary>
          <dl>
            {profile !== "—" ? <><dt>Teknik Profil</dt><dd>{profile}</dd></> : null}
            {secondaryFields.map((field) => <div key={field}><dt>{field}</dt><dd>{display(row[field])}</dd></div>)}
          </dl>
        </details>
      </article>;
    })}
  </div>;
}
