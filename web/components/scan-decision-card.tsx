import type { StockDetailResponse } from "../lib/market-center";
import { projectionHref } from "../lib/projection";
import { stockDetailHref } from "../lib/stock-detail-route";

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

export function ScanDecisionCard({ jobId, detail }: Readonly<{ jobId: string; detail: StockDetailResponse }>) {
  const { decision, action, panel } = detail;
  const levels: Array<[string, unknown]> = [
    ["Destek", panel.destek],
    ["Direnç", panel.direnc],
    ["Stop", panel.stop],
    ["TP1", panel.tp1],
    ["TP2", panel.tp2],
    ["TP3", panel.tp3],
  ];

  return <section className="scan-decision-card" aria-label={`${detail.ticker} hisse karar motoru`}>
    <div className="scan-decision-hero">
      <div className="scan-decision-identity">
        <p className="eyebrow">HİSSEYE ÖZEL KARAR MOTORU</p>
        <h3>{detail.ticker}</h3>
        <span>Fiyat <b>{text(detail.price)}</b> · IZFIN Skor <b>{text(detail.score.nihai)}</b></span>
      </div>
      <div className="scan-decision-verdict">
        <small>MERKEZİ KARAR</small>
        <strong>{text(decision.karar, text(detail.signal))}</strong>
        <span>Skorlar kararı açıklıyor; aksiyonu merkezi motor belirliyor.</span>
      </div>
    </div>
    <div className="scan-decision-kpis">
      <span><small>Algoritma güveni</small><b>%{text(decision.guven)}</b></span>
      <span><small>Risk</small><b>{text(decision.risk)}</b></span>
      <span><small>MTF uyumu</small><b>%{text(decision.mtf_uyum)}</b></span>
      <span><small>Giriş kalitesi</small><b>{text(action.entry_quality, text(detail.entry_quality))}</b></span>
      <span><small>Teknik profil</small><b>{text(action.profile)}</b></span>
    </div>
    <div className="scan-decision-reasons">
      <article className="is-positive"><small>01 · Olumlu teyitler</small><h4>Neden alınabilir?</h4><p>{text(decision.olumlu_metin, "Olumlu teknik teyit oluşmadı.")}</p></article>
      <article className="is-risk"><small>02 · Riskler ve bekleme nedenleri</small><h4>Neden beklenmeli / alınmamalı?</h4><p>{text(decision.risk_metin, "Belirgin ek risk gerekçesi oluşmadı.")}</p></article>
    </div>
    {decision.mtf_metin ? <div className="scan-decision-note"><small>ZAMAN DİLİMLERİ</small><p>{text(decision.mtf_metin)}</p></div> : null}
    <div className="scan-decision-level-heading"><span>İşlem planı seviyeleri</span><small>Destek · direnç · zarar kes · hedefler</small></div>
    <div className="scan-decision-levels">{levels.map(([label, value]) => <span key={label}><small>{label}</small><b>{text(value)}</b></span>)}</div>
    <div className="scan-decision-actions">
      <a href={stockDetailHref(jobId, detail.ticker)}>Detaylı analizi aç →</a>
      <a href={projectionHref(jobId, detail.ticker)}>45G projeksiyonu aç →</a>
    </div>
  </section>;
}
