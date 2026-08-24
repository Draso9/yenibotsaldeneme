"""Pure presentation helpers for the smart-scan page shell."""

from __future__ import annotations

import html
from collections.abc import Sequence
from typing import Any

from izfin_ui.watchlist_view import aktif_evren_chipleri_html


def tarama_sayfa_html_paketi_hazirla(kisisel_liste_adedi: int) -> dict[str, str]:
    """Return the static scan-page chrome without depending on Streamlit state."""
    adet = max(int(kisisel_liste_adedi), 0)
    return {
        "hero_html": (
            '<div class="iz-scanner-hero"><div>'
            '<div class="iz-section-label">IZFIN SCANNER</div>'
            '<h2 id="akilli-tarama-merkezi">Akıllı Tarama Merkezi</h2>'
            '<p>Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları '
            'skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p>'
            '</div><span class="iz-badge wait">SIGNATURE SCAN</span></div>'
        ),
        "control_header_html": f"""
            <div class="iz-scan-control-head">
              <div>
                <div class="iz-section-label">TARAMA KONTROL PANELİ</div>
                <h3 id="tarama-kontrol-paneli">Evreni hazırla ve taramayı başlat</h3>
                <p>Hisse ekleme, kişisel liste, profil ve tarama seçimi artık tek çalışma alanında.</p>
              </div>
              <div class="iz-scan-count">KİŞİSEL LİSTE · {adet} VARLIK</div>
            </div>
        """,
        "watchlist_panel_html": (
            '<div class="iz-panel-title"><span class="iz-panel-icon">⌕</span>'
            '<div><b>Hisse Ara & Listem</b>'
            '<small>Piyasalarda ara, kişisel evrenini oluştur</small></div></div>'
        ),
        "universe_panel_html": (
            '<div class="iz-panel-title"><span class="iz-panel-icon">◎</span>'
            '<div><b>Tarama Evreni</b>'
            '<small>Profilini ve taranacak varlıkları belirle</small></div></div>'
        ),
    }


def aktif_tarama_evreni_html(
    profil: Any,
    tickers: Sequence[Any] | None,
    *,
    chipleri_goster: bool,
) -> str:
    """Render the selected profile and optional personal-watchlist chips."""
    varliklar = list(tickers or [])
    chipler = ""
    if chipleri_goster:
        chipler = (
            '<div class="iz-static-chip-wrap">'
            + aktif_evren_chipleri_html(varliklar)
            + "</div>"
        )
    return f"""
        <div class="iz-active-universe">
            <div class="iz-active-universe-top">
                <div>
                    <small>AKTİF TARAMA EVRENİ</small>
                    <strong>{html.escape(str(profil))}</strong>
                </div>
                <span>{len(varliklar)} VARLIK</span>
            </div>
            {chipler}
        </div>
    """


def tarama_secim_ozeti_html(varlik_adedi: int) -> str:
    adet = max(int(varlik_adedi), 0)
    return (
        f'<div class="iz-scan-selection-summary"><b>{adet}</b>'
        "<span> varlık taramaya hazır</span></div>"
    )


def tarama_sonuc_kpi_html_paketi_hazirla(
    sonuc_adedi: int,
    boga_sayisi: int,
    alim_firsati: int,
) -> tuple[str, str, str]:
    """Return the three result KPI cards in their existing display order."""
    return (
        '<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div>'
        f'<div class="kpi-value">{int(sonuc_adedi)}</div></div>',
        '<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div>'
        f'<div class="kpi-value kpi-highlight-green">{int(boga_sayisi)}</div></div>',
        '<div class="kpi-card"><div class="kpi-title">Alım Fırsatları & Kırılımlar</div>'
        f'<div class="kpi-value kpi-highlight-fire">🔥 {int(alim_firsati)}</div></div>',
    )


def tarama_odak_stili_html() -> str:
    return """
        <style>
[data-testid="stSidebar"]{display:none!important;}
        [data-testid="stHeader"]{display:none!important;}
        [data-testid="stToolbar"]{display:none!important;}
        footer{display:none!important;}

        .stAppViewContainer .main .block-container{
            max-width:100%!important;
            width:100%!important;
            padding:12px 18px 28px!important;
        }

        .iz-scan-table-wrap{
            width:100%!important;
            max-width:none!important;
            overflow-x:hidden!important;
        }

        .iz-focus-title h2{font-size:21px!important;}
        .iz-focus-title p{font-size:10px!important;}
        </style>
    """


def tarama_odak_basligi_html() -> str:
    return """
        <div class="iz-focus-title">
            <div>
                <small>IZFIN SIGNATURE SCAN</small>
                <h2>Akıllı Tarama Sonuçları</h2>
                <p>Geniş tablo görünümü · tüm karar alanları tek ekranda</p>
            </div>
        </div>
    """


def tarama_odak_meta_html(varlik_adedi: int, filtre: Any) -> str:
    return (
        f'<div class="iz-focus-meta"><span>{max(int(varlik_adedi), 0)} varlık</span>'
        f"<span>{html.escape(str(filtre))}</span></div>"
    )


def tarama_tablosu_sarmala(tablo_html: str) -> str:
    return '<div class="iz-scan-table-wrap">' + str(tablo_html) + "</div>"
