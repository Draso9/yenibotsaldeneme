"""Framework-neutral scan result table presenters for IZFIN."""

from __future__ import annotations

import html
import re


DEFAULT_COLUMNS = (
    "Varlık",
    "Fiyat",
    "Nihai Sinyal",
    "Gelişmiş Skor",
    "Güven",
    "🎯 Giriş Kalitesi",
    "MTF Uyum",
    "Risk",
    "Para Akışı",
    "PEG / Değerleme",
    "Seans Dışı",
)

SORT_TYPES = {
    "Varlık": "text",
    "Fiyat": "number",
    "Nihai Sinyal": "number",
    "Gelişmiş Skor": "number",
    "Güven": "number",
    "🎯 Giriş Kalitesi": "number",
    "MTF Uyum": "number",
    "Risk": "number",
    "Para Akışı": "number",
    "PEG / Değerleme": "number",
    "Seans Dışı": "number",
}


def badge_class(value) -> str:
    upper = str(value or "").upper()
    if "GÜÇLÜ AL" in upper or ("AL" in upper and "ERKEN" not in upper):
        return "buy"
    if "ERKEN" in upper:
        return "early"
    if "TEYİT" in upper or "İZLE" in upper:
        return "wait"
    return "risk"


def sort_num(value, default: float = -999999.0, last_percent: bool = False) -> float:
    try:
        text = str(value or "").replace(",", ".")
        if last_percent:
            values = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
            if values:
                return float(values[-1])
        match = re.search(r"([+-]?\d+(?:\.\d+)?)", text)
        return float(match.group(1)) if match else float(default)
    except Exception:
        return float(default)


def sort_risk(value) -> int:
    upper = str(value or "").upper()
    if "ÇOK YÜKSEK" in upper:
        return 4
    if "YÜKSEK" in upper:
        return 3
    if "ORTA" in upper:
        return 2
    if "DÜŞÜK" in upper:
        return 1
    return 0


def sort_signal(value) -> int:
    upper = str(value or "").upper()
    if "GÜÇLÜ AL" in upper or "KUSURSUZ" in upper:
        return 6
    if "ERKEN AL" in upper or "KADEMELİ ALIM" in upper:
        return 5
    if "AL" in upper and "KÂR AL" not in upper and "KAR AL" not in upper:
        return 4
    if "TEYİT" in upper or "İZLE" in upper or "BEKLE" in upper:
        return 3
    if "NÖTR" in upper:
        return 2
    if "KÂR AL" in upper or "KAR AL" in upper:
        return 1
    if "SAT" in upper or "KAÇIN" in upper or "UZAK DUR" in upper:
        return 0
    return 2


def sort_flow(value) -> int:
    upper = str(value or "").upper()
    if "GÜÇLÜ" in upper and ("GİRİŞ" in upper or "POZİTİF" in upper):
        return 5
    if "GİRİŞ" in upper or "POZİTİF" in upper:
        return 4
    if "DENGELİ" in upper or "NÖTR" in upper:
        return 3
    if "ZAYIF" in upper:
        return 2
    if "ÇIKIŞ" in upper or "NEGATİF" in upper:
        return 1
    return 0


def tarama_tablosu_html(df, paneller=None) -> str:
    if df is None or df.empty:
        return '<div class="iz-table-wrap"><div style="padding:22px;color:#7895a9">Gösterilecek tarama sonucu yok.</div></div>'

    paneller = paneller or {}
    columns = [column for column in DEFAULT_COLUMNS if column in df.columns]
    esc = lambda value: html.escape(str(value if value is not None else "—"))
    heads = "".join(
        f'<th class="iz-sortable-th" data-col="{index}" data-type="{SORT_TYPES[column]}" title="Sıralamak için tıklayın">{esc(column)}<span class="iz-sort-icon">↕</span></th>'
        for index, column in enumerate(columns)
    )

    body = []
    for _, row in df.iterrows():
        profile = str(row.get("Teknik Profil", "") or "").strip()
        ticker = str(row.get("Varlık", "") or "")
        panel = paneller.get(ticker, {})
        cells = []
        for column in columns:
            value = str(row.get(column, "—"))
            css_class = ""
            rendered = esc(value)
            sort_value = value.lower()
            if column == "Varlık":
                css_class = "ticker"
                sort_value = ticker.lower()
            elif column == "Fiyat":
                sort_value = sort_num(value)
            elif column == "Gelişmiş Skor":
                css_class = "score"
                sort_value = float(panel.get("cezali_skor", sort_num(value)) or 0)
            elif column == "Güven":
                sort_value = float(panel.get("guven_skoru", sort_num(value)) or 0)
            elif column == "🎯 Giriş Kalitesi":
                sort_value = float(
                    panel.get("giris_puani", panel.get("tetik_puani", sort_num(value))) or 0
                )
            elif column == "MTF Uyum":
                sort_value = float(panel.get("mtf_uyum", sort_num(value)) or 0)
            elif column == "Nihai Sinyal":
                sort_value = sort_signal(value)
                profile_html = ""
                if profile:
                    profile_class = "long-term" if "UZUN VADELİ ADAY" in profile.upper() else "profile"
                    profile_html = (
                        f'<span class="iz-signal-profile {profile_class}">Profil: {esc(profile)}</span>'
                    )
                rendered = (
                    f'<div class="iz-signal-stack"><span class="iz-badge {badge_class(value)}">'
                    f'{esc(value)}</span>{profile_html}</div>'
                )
            elif column == "Risk":
                sort_value = sort_risk(value)
                upper = value.upper()
                css_class = (
                    "risk-high"
                    if "YÜKSEK" in upper or "PANİK" in upper
                    else "risk-low"
                    if "DÜŞÜK" in upper or "SAKİN" in upper
                    else "risk-mid"
                )
            elif column == "Para Akışı":
                css_class = "muted"
                sort_value = sort_flow(value)
            elif column == "PEG / Değerleme":
                css_class = "muted"
                sort_value = sort_num(value)
            elif column == "Seans Dışı":
                css_class = "muted"
                sort_value = sort_num(value, last_percent=True)

            cells.append(
                f'<td class="{css_class}" data-sort="{html.escape(str(sort_value), quote=True)}">{rendered}</td>'
            )
        body.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div class="iz-table-wrap"><table class="iz-table iz-client-sortable"><thead><tr>'
        + heads
        + '</tr></thead><tbody>'
        + "".join(body)
        + "</tbody></table></div>"
    )


def tarama_genis_ozet_html(df) -> str:
    """Geniş görünüm: hizalı, profesyonel ve okunabilir IZFIN sonuç tablosu."""
    if df is None or df.empty:
        return '<div class="iz-wide-table-empty">Gösterilecek tarama sonucu yok.</div>'

    def esc(value):
        return html.escape(str(value if value not in (None, "") else "—"))

    def percent_class(value):
        text = str(value or "")
        if "+" in text:
            return "up"
        if "-" in text:
            return "down"
        return "flat"

    rows = []
    for _, row in df.iterrows():
        raw_ticker = str(row.get("Varlık", "—"))
        ticker = esc(raw_ticker)
        price = esc(row.get("Fiyat", "—"))
        raw_signal = str(row.get("Nihai Sinyal", "—"))
        signal = esc(raw_signal)

        score = esc(row.get("Gelişmiş Skor", "—"))
        confidence = esc(row.get("Güven", "—"))
        mtf = esc(row.get("MTF Uyum", "—"))
        raw_entry = str(row.get("🎯 Giriş Kalitesi", "—"))
        entry = esc(raw_entry)

        raw_risk = str(row.get("Risk", "—"))
        risk = esc(raw_risk)
        raw_flow = str(row.get("Para Akışı", "—"))
        flow = esc(raw_flow)
        raw_value = str(row.get("PEG / Değerleme", "—"))
        valuation = esc(raw_value)
        raw_session = str(row.get("Seans Dışı", "—"))
        session = esc(raw_session)

        risk_upper = raw_risk.upper()
        risk_class = "high" if "YÜKSEK" in risk_upper else "low" if "DÜŞÜK" in risk_upper else "mid"

        flow_upper = raw_flow.upper()
        flow_class = (
            "good"
            if any(item in flow_upper for item in ("GİRİŞ", "GÜÇLÜ", "POZİTİF"))
            else "bad"
            if any(item in flow_upper for item in ("ÇIKIŞ", "ZAYIF", "NEGATİF"))
            else "mid"
        )

        value_upper = raw_value.upper()
        value_class = (
            "good"
            if any(item in value_upper for item in ("UCUZ", "CAZİP"))
            else "bad"
            if any(item in value_upper for item in ("YÜKSEK", "PAHALI", "PRİM"))
            else "mid"
        )

        session_class = percent_class(raw_session)
        sort_ticker = raw_ticker.lower()
        sort_signal_value = sort_signal(raw_signal)
        sort_score = sort_num(score)
        sort_risk_value = sort_risk(raw_risk)
        sort_value = sort_num(raw_value)
        sort_session = sort_num(raw_session, last_percent=True)

        rows.append(
            "<tr>"
            f"<td class='izw-asset' data-sort='{sort_ticker}'>"
            f"<div class='izw-asset-top'><div><strong>{ticker}</strong><small>Varlık</small></div></div>"
            f"<div class='izw-price'>{price}</div>"
            "</td>"
            f"<td class='izw-decision' data-sort='{sort_signal_value}'>"
            f"<span class='iz-badge {badge_class(raw_signal)}'>{signal}</span>"
            "<small>Merkezi karar</small>"
            f"<div class='izw-profile {'long-term' if 'UZUN VADELİ ADAY' in str(row.get('Teknik Profil', '')).upper() else ''}'>{esc(row.get('Teknik Profil', '—'))}</div>"
            "</td>"
            f"<td class='izw-quality' data-sort='{sort_score}'>"
            "<div class='izw-quality-top'>"
            f"<div><span>SKOR</span><b>{score}</b></div>"
            f"<div><span>GÜVEN</span><b>{confidence}</b></div>"
            f"<div><span>MTF</span><b>{mtf}</b></div>"
            "</div>"
            "<div class='izw-entry'>"
            "<span>GİRİŞ KALİTESİ</span>"
            f"<b title='{entry}'>{entry}</b>"
            "</div>"
            "</td>"
            f"<td class='izw-riskflow' data-sort='{sort_risk_value}'>"
            "<div class='izw-rf-grid'>"
            f"<div class='{risk_class}'><span>RİSK</span><b>{risk}</b></div>"
            f"<div class='{flow_class}'><span>PARA AKIŞI</span><b title='{flow}'>{flow}</b></div>"
            "</div>"
            "</td>"
            f"<td class='izw-value' data-sort='{sort_value}'>"
            "<span>DEĞERLEME</span>"
            f"<b class='{value_class}' title='{valuation}'>{valuation}</b>"
            "</td>"
            f"<td class='izw-session' data-sort='{sort_session}'>"
            "<span class='izw-moon'>◐</span>"
            f"<b class='{session_class}' title='{session}'>{session}</b>"
            "</td>"
            "</tr>"
        )

    return (
        "<div class='izw-shell'>"
        "<table class='izw-table iz-client-sortable'>"
        "<thead><tr>"
        "<th class='iz-sortable-th' data-col='0' data-type='text'>VARLIK / FİYAT<span class='iz-sort-icon'>↕</span></th>"
        "<th class='iz-sortable-th' data-col='1' data-type='number'>IZFIN KARARI<span class='iz-sort-icon'>↕</span></th>"
        "<th class='iz-sortable-th' data-col='2' data-type='number'>KALİTE<span class='iz-sort-icon'>↕</span></th>"
        "<th class='iz-sortable-th' data-col='3' data-type='number'>RİSK / AKIŞ<span class='iz-sort-icon'>↕</span></th>"
        "<th class='iz-sortable-th' data-col='4' data-type='number'>DEĞERLEME<span class='iz-sort-icon'>↕</span></th>"
        "<th class='iz-sortable-th' data-col='5' data-type='number'>SEANS DIŞI<span class='iz-sort-icon'>↕</span></th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
        "</div>"
    )


def sortable_table_script() -> str:
    return """
<script>
(() => {
  const doc = window.parent.document;
  function bind(table){
    if(!table) return false;
    if(table.dataset.izSortBound==="1") return true;
    const tbody=table.querySelector("tbody");
    const heads=[...table.querySelectorAll("thead th.iz-sortable-th")];
    if(!tbody || !heads.length) return false;
    table.dataset.izSortBound="1";
    heads.forEach(th=>{
      const run=()=>{
        const col=Number(th.dataset.col||0);
        const type=th.dataset.type||"text";
        const same=Number(table.dataset.sortCol??-1)===col;
        const prev=table.dataset.sortDir||"";
        const dir=same?(prev==="desc"?"asc":"desc"):(type==="text"?"asc":"desc");
        const rows=[...tbody.querySelectorAll("tr")];
        rows.sort((a,b)=>{
          let av=a.children[col]?.dataset.sort ?? a.children[col]?.innerText ?? "";
          let bv=b.children[col]?.dataset.sort ?? b.children[col]?.innerText ?? "";
          if(type==="number"){
            av=Number(av); bv=Number(bv);
            if(!Number.isFinite(av)) av=-999999999;
            if(!Number.isFinite(bv)) bv=-999999999;
            return dir==="asc"?av-bv:bv-av;
          }
          const c=String(av).localeCompare(String(bv),"tr",{numeric:true,sensitivity:"base"});
          return dir==="asc"?c:-c;
        });
        rows.forEach(r=>tbody.appendChild(r));
        table.dataset.sortCol=String(col); table.dataset.sortDir=dir;
        heads.forEach(h=>{h.classList.remove("iz-sort-active"); const ic=h.querySelector(".iz-sort-icon"); if(ic) ic.textContent="↕";});
        th.classList.add("iz-sort-active");
        const icon=th.querySelector(".iz-sort-icon"); if(icon) icon.textContent=dir==="desc"?"↓":"↑";
      };
      th.addEventListener("click",run);
      th.tabIndex=0;
    });
    return true;
  }
  const bindAll=()=>{
    const tables=[...doc.querySelectorAll("table.iz-client-sortable")];
    return tables.length>0 && tables.map(bind).every(Boolean);
  };
  let bindAttempts=0;
  const bindWithRetry=()=>{
    bindAttempts+=1;
    if(!bindAll() && bindAttempts<480) setTimeout(bindWithRetry,250);
  };
  bindWithRetry();
})();
</script>
"""
