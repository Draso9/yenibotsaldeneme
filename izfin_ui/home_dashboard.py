from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import html
from math import isfinite
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if isfinite(result) else float(default)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def home_scan_bos_mu(sonuclar: Sequence[Mapping[str, Any]] | None) -> bool:
    """Ana sayfada son tarama verisi olup olmadığını framework bağımsız belirler."""
    return not bool(sonuclar)


def home_panel_metrics_hazirla(
    paneller: Sequence[Mapping[str, Any]] | None,
    piyasa_degisimleri: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Piyasa merkezi için pulse/trend/momentum/akış/risk view-modelini üretir."""
    panel_listesi = list(paneller or [])
    if not panel_listesi:
        degisimler = [
            _safe_float(value, default=float("nan"))
            for value in (piyasa_degisimleri or [])
        ]
        degisimler = [value for value in degisimler if isfinite(value)]
        ortalama = sum(degisimler) / len(degisimler) if degisimler else 0.0
        pulse = int(_clamp(round(50 + ortalama * 8), 15, 85))
        return {
            "pulse": pulse,
            "trend": pulse,
            "momentum": int(_clamp(pulse - 4)),
            "flow": int(_clamp(pulse - 2)),
            "risk": 50,
            "kaynak": "PİYASA VERİSİ",
        }

    trend = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("fiyat"), 0.0) > _safe_float(panel.get("sma200"), float("inf"))
    ) / len(panel_listesi) * 100
    momentum = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("macd"), 0.0) > _safe_float(panel.get("macd_signal"), 0.0)
    ) / len(panel_listesi) * 100
    flow = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("cmf"), 0.0) > 0
    ) / len(panel_listesi) * 100

    risk_map = {"DÜŞÜK": 25, "ORTA": 50, "YÜKSEK": 75, "ÇOK YÜKSEK": 90}
    risk_values = [
        risk_map.get(str(panel.get("risk_seviyesi", "ORTA")).upper(), 50)
        for panel in panel_listesi
    ]
    risk = sum(risk_values) / len(risk_values) if risk_values else 50.0
    pulse = int(round(_clamp(.34 * trend + .27 * momentum + .24 * flow + .15 * (100 - risk))))

    return {
        "pulse": pulse,
        "trend": int(round(trend)),
        "momentum": int(round(momentum)),
        "flow": int(round(flow)),
        "risk": int(round(risk)),
        "kaynak": "IZFIN TARAMASI",
    }


def home_karar_ozeti_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    *,
    pulse: int,
    trend: int,
    momentum: int,
    flow: int,
    risk: int,
    kaynak: str,
    sinyal_yonu_belirle: Callable[[str], str],
) -> dict[str, Any]:
    """Ana sayfa karar merkezinin hesaplama kısmını render katmanından ayırır."""
    sonuc_listesi = list(sonuclar or [])
    panel_map = dict(paneller or {})

    guclu_al = 0
    alim_tarafi = 0
    teyit = 0
    yuksek_risk = 0
    adaylar: list[tuple[float, str, float, float, float, str, str]] = []

    for sonuc in sonuc_listesi:
        ticker = str(sonuc.get("Varlık", ""))
        panel = panel_map.get(ticker, {})
        sinyal = str(sonuc.get("Nihai Sinyal", "") or "").upper()
        skor = _safe_float(panel.get("cezali_skor"), 0.0)
        guven = _safe_float(panel.get("guven_skoru"), 50.0)
        mtf = _safe_float(panel.get("mtf_uyum"), 50.0)
        risk_txt = str(panel.get("risk_seviyesi", sonuc.get("Risk", "")) or "").upper()

        yon = sinyal_yonu_belirle(sinyal)
        if yon == "ALIM":
            alim_tarafi += 1
            if "GÜÇLÜ AL" in sinyal or "KUSURSUZ" in sinyal:
                guclu_al += 1
        elif yon == "NÖTR" and any(
            etiket in sinyal for etiket in ("BEKLE", "TEYİT", "ERKEN", "NÖTR", "İZLE")
        ):
            teyit += 1

        if "YÜKSEK" in risk_txt:
            yuksek_risk += 1

        risk_ceza = 10 if "ÇOK YÜKSEK" in risk_txt else 6 if "YÜKSEK" in risk_txt else 0
        yon_bonus = 18 if yon == "ALIM" else (0 if yon == "NÖTR" else -100)
        setup_rank = skor * .52 + guven * .30 + mtf * .18 - risk_ceza + yon_bonus
        if yon != "SATIŞ":
            adaylar.append((setup_rank, ticker, skor, guven, mtf, risk_txt, sinyal))

    adaylar.sort(reverse=True)
    best = adaylar[0] if adaylar else None

    if pulse >= 72:
        mod, mod_cls = "GÜÇLÜ POZİTİF", "positive"
    elif pulse >= 60:
        mod, mod_cls = "SEÇİCİ POZİTİF", "positive"
    elif pulse >= 45:
        mod, mod_cls = "DENGELİ / SEÇİCİ", "neutral"
    elif pulse >= 32:
        mod, mod_cls = "TEMKİNLİ", "caution"
    else:
        mod, mod_cls = "RİSKTEN KAÇIN", "danger"

    yorum_parcalari: list[str] = []
    if trend >= 70:
        yorum_parcalari.append("trend güçlü")
    elif trend < 45:
        yorum_parcalari.append("trend zayıf")
    if momentum >= 65:
        yorum_parcalari.append("momentum destekliyor")
    elif momentum < 45:
        yorum_parcalari.append("momentum zayıf")
    if flow < 45:
        yorum_parcalari.append("para akışı teyidi zayıf")
    elif flow >= 60:
        yorum_parcalari.append("para akışı pozitif")
    if risk >= 65:
        yorum_parcalari.append("risk seviyesi yüksek")
    elif risk < 40:
        yorum_parcalari.append("risk görece düşük")

    yorum = ", ".join(yorum_parcalari[:4])
    if yorum:
        yorum = yorum[0].upper() + yorum[1:] + "."
    else:
        yorum = "Teknik bileşenler dengeli; güçlü setup'larda seçici ilerlemek uygun."

    return {
        "sonuclar": sonuc_listesi,
        "paneller": panel_map,
        "guclu_al": guclu_al,
        "alim_tarafi": alim_tarafi,
        "teyit": teyit,
        "yuksek_risk": yuksek_risk,
        "best": best,
        "mod": mod,
        "mod_cls": mod_cls,
        "yorum": yorum,
        "pulse": int(pulse),
        "trend": int(trend),
        "momentum": int(momentum),
        "flow": int(flow),
        "risk": int(risk),
        "kaynak": str(kaynak),
    }


def home_top_signals_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    max_n: int = 7,
) -> list[dict[str, Any]]:
    """En yüksek cezalı skora sahip ana sayfa sinyal satırlarını hazırlar."""
    panel_map = dict(paneller or {})
    sirali = sorted(
        list(sonuclar or []),
        key=lambda sonuc: _safe_float(
            panel_map.get(str(sonuc.get("Varlık", "")), {}).get("cezali_skor"),
            0.0,
        ),
        reverse=True,
    )[: max(0, int(max_n))]

    cikti: list[dict[str, Any]] = []
    for sonuc in sirali:
        ticker = str(sonuc.get("Varlık", ""))
        panel = panel_map.get(ticker, {})
        cikti.append(
            {
                "ticker": ticker,
                "fiyat": sonuc.get("Fiyat", "—"),
                "sinyal": str(sonuc.get("Nihai Sinyal", "—")),
                "skor": int(_safe_float(panel.get("cezali_skor"), 0.0)),
                "guven": int(_safe_float(panel.get("guven_skoru"), 50.0)),
                "mtf": int(_safe_float(panel.get("mtf_uyum"), 50.0)),
                "risk": panel.get("risk_seviyesi", sonuc.get("Risk", "—")),
            }
        )
    return cikti


def home_movers_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    max_n: int = 6,
) -> list[dict[str, Any]]:
    """Mutlak günlük değişime göre ana sayfa hareket listesini sıralar."""
    panel_map = dict(paneller or {})
    rows: list[tuple[float, float, str, Any]] = []
    for sonuc in list(sonuclar or []):
        ticker = str(sonuc.get("Varlık", ""))
        degisim = _safe_float(panel_map.get(ticker, {}).get("gunluk_degisim"), 0.0)
        rows.append((abs(degisim), degisim, ticker, sonuc.get("Fiyat", "—")))
    rows.sort(reverse=True)

    return [
        {"ticker": ticker, "fiyat": fiyat, "degisim": degisim}
        for _, degisim, ticker, fiyat in rows[: max(0, int(max_n))]
    ]


def home_dashboard_html_hazirla(
    sonuclar,
    paneller,
    *,
    piyasa_degisimleri=None,
    sinyal_yonu_belirle,
):
    """Karar merkezi view-modeli ve HTML'ini tek framework-neutral pakette üretir."""
    sonuc_listesi = list(sonuclar or [])
    panel_map = dict(paneller or {})
    metrics = home_panel_metrics_hazirla(list(panel_map.values()), piyasa_degisimleri)
    ozet = home_karar_ozeti_hazirla(
        sonuc_listesi,
        panel_map,
        sinyal_yonu_belirle=sinyal_yonu_belirle,
        **metrics,
    )
    hero = (
        '<div class="iz-hero iz-market-hero">'
        '<div class="iz-market-hero-kicker"><span class="iz-market-hero-dot"></span>IZFIN SIGNATURE COMMAND CENTER</div>'
        '<div class="iz-market-hero-main"><div><h1>IZFIN Piyasa Merkezi</h1>'
        '<p>Son taramanın karar dağılımını, piyasa modunu ve en güçlü setup’ı tek bakışta gör.</p>'
        '</div><div class="iz-market-hero-mark">IZ</div></div></div>'
    )
    if not sonuc_listesi:
        empty = (
            '<div class="iz-decision-center iz-decision-center-premium">'
            '<div class="iz-decision-head"><div><small>IZFIN KARAR MERKEZİ</small>'
            '<h2>İlk tarama bekleniyor</h2><p>Karar dağılımı, piyasa modu ve öne çıkan setup bu alanda oluşacak.</p>'
            '</div><span class="iz-decision-mode neutral">HAZIR</span></div>'
            '<div class="iz-decision-empty iz-decision-empty-premium">'
            '<div class="iz-decision-empty-icon">◫</div><b>Henüz piyasa özeti oluşmadı</b>'
            '<span>Akıllı Tarama çalıştırıldığında trend, momentum, para akışı ve risk bileşenleri burada birleşir.</span>'
            '</div></div>'
        )
        return {"hero_html": hero, "center_html": empty, "best_ticker": None, "metrics": metrics, "summary": ozet}

    best = ozet["best"]
    best_ticker = None
    if best:
        _, best_ticker, skor, guven, mtf, risk, sinyal = best
        best_html = (
            '<div class="iz-best-setup-copy iz-best-setup-feature iz-featured-stock-v2">'
            '<div class="iz-featured-left"><div class="iz-best-feature-label"><span>✦</span> BUGÜNÜN ÖNE ÇIKAN HİSSESİ</div>'
            '<div class="iz-featured-identity">'
            f'<div class="iz-featured-ticker">{html.escape(best_ticker)}</div>'
            f'<div class="iz-featured-signal">{html.escape(sinyal or "—")}</div></div>'
            '<div class="iz-featured-caption">Son taramada listenin teknik bileşiminde en fazla öne çıkan aday</div></div>'
            '<div class="iz-featured-metrics">'
            f'<div><span>IZFIN SKOR</span><strong>{int(skor)}</strong></div>'
            f'<div><span>GÜVEN</span><strong>%{int(guven)}</strong></div>'
            f'<div><span>MTF</span><strong>%{int(mtf)}</strong></div>'
            f'<div><span>RİSK</span><strong>{html.escape(risk or "—")}</strong></div>'
            '</div></div>'
        )
    else:
        best_html = '<div class="iz-best-setup-copy"><small>BUGÜNÜN ÖNE ÇIKAN SETUP’I</small><strong>—</strong></div>'

    center = (
        '<div class="iz-decision-center iz-decision-center-premium"><div class="iz-decision-head">'
        '<div><small>IZFIN KARAR MERKEZİ</small><h2>Son Tarama Özeti</h2>'
        f'<p>{html.escape(str(metrics["kaynak"]))} · Son taranan evrene göre</p></div>'
        f'<span class="iz-decision-mode {ozet["mod_cls"]}">{ozet["mod"]} · {metrics["pulse"]}/100</span></div>'
        '<div class="iz-decision-kpis">'
        f'<div><span>ALIM TARAFI</span><b>{ozet["alim_tarafi"]}</b><small>AL / Güçlü AL</small></div>'
        f'<div><span>GÜÇLÜ SETUP</span><b>{ozet["guclu_al"]}</b><small>yüksek öncelik</small></div>'
        f'<div><span>TEYİT BEKLEYEN</span><b>{ozet["teyit"]}</b><small>henüz tamamlanmadı</small></div>'
        f'<div><span>YÜKSEK RİSK</span><b>{ozet["yuksek_risk"]}</b><small>dikkat gerektiriyor</small></div>'
        '</div><div class="iz-decision-lower iz-decision-lower-summary"><div class="iz-market-factors">'
        f'<div><span>TREND</span><b>{metrics["trend"]}</b></div>'
        f'<div><span>MOMENTUM</span><b>{metrics["momentum"]}</b></div>'
        f'<div><span>PARA AKIŞI</span><b>{metrics["flow"]}</b></div>'
        f'<div><span>RİSK</span><b>{metrics["risk"]}</b></div></div></div>'
        f'<div class="iz-system-comment"><span>SİSTEM YORUMU</span><p>{html.escape(ozet["yorum"])}</p></div>'
        f'<div class="iz-best-setup-bottom">{best_html}</div>'
        '<div class="iz-decision-foot">Piyasa modu tüm piyasanın resmi breadth göstergesi değildir; IZFIN’in son taramada analiz ettiği listenin teknik bileşiminden üretilir.</div></div>'
    )
    return {"hero_html": hero, "center_html": center, "best_ticker": best_ticker, "metrics": metrics, "summary": ozet}


def home_top_signals_html(sonuclar, paneller, *, max_n=7):
    rows = []
    for item in home_top_signals_hazirla(sonuclar, paneller, max_n=max_n):
        sinyal = str(item["sinyal"])
        sinyal_upper = sinyal.upper()
        if "GÜÇLÜ AL" in sinyal_upper or ("AL" in sinyal_upper and "ERKEN" not in sinyal_upper):
            badge = "buy"
        elif "ERKEN" in sinyal_upper:
            badge = "early"
        elif "TEYİT" in sinyal_upper or "İZLE" in sinyal_upper:
            badge = "wait"
        else:
            badge = "risk"
        rows.append(
            f'<tr><td><b>{html.escape(str(item["ticker"]))}</b></td>'
            f'<td>{html.escape(str(item["fiyat"]))}</td>'
            f'<td><span class="iz-badge {badge}">{html.escape(sinyal)}</span></td>'
            f'<td><b style="color:#20e69a">{int(item["skor"])}</b></td>'
            f'<td><div class="iz-ring" style="--g:{int(item["guven"])}"><span>{int(item["guven"])}%</span></div></td>'
            f'<td>{int(item["mtf"])}%</td><td>{html.escape(str(item["risk"]))}</td></tr>'
        )
    if not rows:
        return (
            '<div class="iz-signals iz-home-feature-card iz-home-feature-cyan"><div class="iz-feature-head">'
            '<div class="iz-feature-icon iz-feature-icon-cyan">◎</div><div class="iz-feature-head-copy">'
            '<div class="iz-card-title">LİSTENİN DİKKAT ÇEKENLERİ</div><div class="iz-feature-accent"></div>'
            '<div class="iz-feature-desc">Derin Tarama çalıştırıldığında en yüksek skorlu sinyaller burada özetlenecek.</div>'
            '</div></div><div class="iz-feature-divider"></div><div class="iz-feature-empty">'
            '<div class="iz-empty-graphic iz-empty-chart"><span class="iz-empty-screen"></span>'
            '<span class="iz-empty-line"></span><span class="iz-empty-spark s1">✦</span><span class="iz-empty-spark s2">✦</span></div>'
            '<b>Henüz veri yok</b><span>Akıllı Tarama ile listenizdeki fırsatları keşfedin.</span>'
            '<div class="iz-feature-cta-slot"></div></div></div>'
        )
    return '<div class="iz-signals"><div class="iz-card-title">LİSTENİN DİKKAT ÇEKENLERİ</div><table><thead><tr><th>VARLIK</th><th>FİYAT</th><th>IZFIN KARARI</th><th>SKOR</th><th>GÜVEN</th><th>MTF</th><th>RİSK</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def home_movers_html(sonuclar, paneller, *, max_n=6, compact=False):
    rows = home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    if compact and rows:
        body = ''.join(
            '<div class="iz-mv1827-row">'
            f'<div class="iz-mv1827-ticker">{html.escape(str(item["ticker"]))}</div>'
            f'<div class="iz-mv1827-price">{html.escape(str(item["fiyat"]))}</div>'
            f'<div class="iz-mv1827-change {"pos" if item["degisim"] >= 0 else "neg"}">{item["degisim"]:+.2f}%</div></div>'
            for item in rows
        )
        style = """
        <style>
        .iz-mv1827-card{width:100%;min-height:406px;box-sizing:border-box;overflow:hidden;padding:20px 18px 16px;border:1px solid #153f55;border-radius:16px;background:#071724;color:#effaff;font-family:inherit}
        .iz-mv1827-title{min-height:28px;display:flex;align-items:center;margin:0 0 10px;color:#f4fbff;font-size:14px;line-height:1;font-weight:850;letter-spacing:.02em;text-transform:uppercase}
        .iz-mv1827-head,.iz-mv1827-row{display:grid;grid-template-columns:minmax(70px,1fr) minmax(0,1.65fr) minmax(64px,.72fr);column-gap:14px;align-items:center;width:100%;box-sizing:border-box}
        .iz-mv1827-head{min-height:38px;padding:0 12px;border-bottom:1px solid #17445a;color:#60b9dc;font-size:8px;font-weight:820;letter-spacing:.06em}
        .iz-mv1827-head>div:nth-child(2),.iz-mv1827-head>div:nth-child(3){text-align:right}
        .iz-mv1827-row{min-height:55px;padding:0 12px;border-bottom:1px solid rgba(23,68,90,.72);transition:background-color .15s ease}
        .iz-mv1827-row:last-child{border-bottom:0}.iz-mv1827-row:hover{background:rgba(18,58,78,.22)}
        .iz-mv1827-ticker,.iz-mv1827-price,.iz-mv1827-change{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .iz-mv1827-ticker{color:#f2fbff;font-size:11px;font-weight:850}.iz-mv1827-price{color:#9bc7d8;font-size:10px;font-weight:700;text-align:right}
        .iz-mv1827-change{font-size:11px;font-weight:850;text-align:right}.iz-mv1827-change.pos{color:#00d77e}.iz-mv1827-change.neg{color:#ff4256}
        @media(max-width:768px){.iz-mv1827-card{min-height:0;padding:16px 12px 12px}.iz-mv1827-head,.iz-mv1827-row{grid-template-columns:minmax(54px,.8fr) minmax(0,1.55fr) minmax(58px,.72fr);column-gap:8px;padding-left:8px;padding-right:8px}.iz-mv1827-price{font-size:9px}.iz-mv1827-change{font-size:10px}}
        </style>
        """
        return (
            style + '<div class="iz-mv1827-card"><div class="iz-mv1827-title">BÜYÜK HAREKETLER</div>'
            '<div class="iz-mv1827-head"><div>VARLIK</div><div>FİYAT</div><div>DEĞİŞİM</div></div>'
            + body + '</div>'
        )
    if rows:
        body = ''.join(
            '<div class="iz-mover-row" style="display:grid!important;grid-template-columns:minmax(72px,.72fr) minmax(0,1.65fr) auto!important;align-items:center!important;width:100%!important">'
            f'<div class="iz-mover-name">{html.escape(str(item["ticker"]))}</div>'
            f'<div class="iz-mover-price">{html.escape(str(item["fiyat"]))}</div>'
            f'<div class="iz-mover-chg {"pos" if item["degisim"] >= 0 else "neg"}">{item["degisim"]:+.2f}%</div></div>'
            for item in rows
        )
        return f'<div class="iz-movers"><div class="iz-card-title">BÜYÜK HAREKETLER</div>{body}<span hidden aria-hidden="true"></span></div>'
    return (
        '<div class="iz-movers iz-home-feature-card iz-home-feature-purple"><div class="iz-feature-head">'
        '<div class="iz-feature-icon iz-feature-icon-purple">▥</div><div class="iz-feature-head-copy">'
        '<div class="iz-card-title">BÜYÜK HAREKETLER</div><div class="iz-feature-accent"></div>'
        '<div class="iz-feature-desc">Akıllı Tarama sonrası listedeki dikkat çekici fiyat hareketleri burada görünecek.</div>'
        '</div></div><div class="iz-feature-divider"></div><div class="iz-feature-empty">'
        '<div class="iz-empty-graphic iz-empty-bars"><span class="b1"></span><span class="b2"></span><span class="b3"></span>'
        '<span class="iz-empty-spark s1">✦</span><span class="iz-empty-spark s2">✦</span></div>'
        '<b>Henüz veri yok</b><span>Akıllı Tarama ile gün içindeki büyük hareketleri görün.</span>'
        '<div class="iz-feature-cta-slot"></div></div></div>'
    )
