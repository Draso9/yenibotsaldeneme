"""Piyasa evreni ve sembol normalleştirme kuralları.

Bu modül Streamlit, Firebase veya veri sağlayıcı istemcilerine bağlı değildir.
Web API'si ve mobil istemci aynı sembol sözleşmesini buradan kullanabilir.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


VARSAYILAN_TICKERS = [
    "AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC",
    "THYAO.IS", "FROTO.IS", "TOASO.IS",
]

# Endeks bileşen dönemi: 01.07.2026 - 30.09.2026 (2026 Q3)
# Yeni dönemsel Borsa İstanbul duyurusunda bu iki liste yeniden gözden geçirilmelidir.
BIST_ENDEKS_DONEMI = "2026-Q3"
BIST_ENDEKS_GECERLILIK = "01.07.2026-30.09.2026"

BIST_30 = [
    "AEFES.IS", "AKBNK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "CIMSA.IS",
    "DSTKF.IS", "EKGYO.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS",
    "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KRDMD.IS", "MGROS.IS", "PETKM.IS",
    "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS", "TCELL.IS",
    "THYAO.IS", "TOASO.IS", "TTKOM.IS", "TUPRS.IS", "ULKER.IS", "YKBNK.IS",
]

BIST_100 = [
    "AEFES.IS", "AKBNK.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALTNY.IS",
    "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BALSU.IS", "BERA.IS",
    "BIMAS.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "CANTE.IS",
    "CCOLA.IS", "CIMSA.IS", "CVKMD.IS", "CWENE.IS", "DAPGM.IS", "DOAS.IS",
    "DOHOL.IS", "DSTKF.IS", "ECILC.IS", "EFOR.IS", "EKGYO.IS", "ENERY.IS",
    "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "ESEN.IS", "EUPWR.IS", "EUREN.IS",
    "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLRMK.IS",
    "GRSEL.IS", "GRTHO.IS", "GSRAY.IS", "GUBRF.IS", "HALKB.IS", "HEKTS.IS",
    "IEYHO.IS", "ISCTR.IS", "ISMEN.IS", "IZENR.IS", "KCHOL.IS", "KLRHO.IS",
    "KRDMD.IS", "KTLEV.IS", "KUYAS.IS", "MAGEN.IS", "MAVI.IS", "MGROS.IS",
    "MIATK.IS", "MPARK.IS", "OBAMS.IS", "ODAS.IS", "ODINE.IS", "OTKAR.IS",
    "OYAKC.IS", "PAHOL.IS", "PASEU.IS", "PATEK.IS", "PETKM.IS", "PGSUS.IS",
    "PSGYO.IS", "QUAGR.IS", "RALYH.IS", "REEDR.IS", "SAHOL.IS", "SARKY.IS",
    "SASA.IS", "SISE.IS", "SKBNK.IS", "SOKM.IS", "TAVHL.IS", "TCELL.IS",
    "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TRALT.IS", "TRENJ.IS", "TRMET.IS",
    "TSKB.IS", "TTKOM.IS", "TUKAS.IS", "TUPRS.IS", "TURSG.IS", "ULKER.IS",
    "VAKBN.IS", "VESTL.IS", "YKBNK.IS", "ZOREN.IS",
]

ABD_HİSSELERİ = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "AMD", "INTC", "NFLX",
]

BIST_TICKER_ALIAS = {
    "KOZAA.IS": "TRMET.IS",
    "KOZAL.IS": "TRALT.IS",
    "IPEKE.IS": "TRENJ.IS",
}


def bist_ticker_guncelle(ticker: object) -> str:
    """Eski BIST işlem kodlarını güncel Yahoo/BIST kodlarına normalize eder."""
    normalized = str(ticker or "").strip().upper()
    return BIST_TICKER_ALIAS.get(normalized, normalized)


def bist_ticker_listesi_guncelle(tickers: Iterable[object] | None) -> list[str]:
    """Sırayı korur; eski kodları günceller ve mükerrerleri siler."""
    sonuc: list[str] = []
    gorulen: set[str] = set()
    for ticker in tickers or []:
        guncel = bist_ticker_guncelle(ticker)
        if guncel and guncel not in gorulen:
            sonuc.append(guncel)
            gorulen.add(guncel)
    return sonuc


def finnhub_symbol(ticker: object) -> str:
    """Yahoo biçimindeki BIST son ekini Finnhub sembol biçimine çevirir."""
    normalized = str(ticker or "").strip()
    return normalized.replace(".IS", "") if normalized.endswith(".IS") else normalized


def ticker_girdisini_dogrula(raw: object) -> tuple[str | None, str | None]:
    """Kullanıcı ticker girişini normalize eder; bozuk karakterleri engeller."""
    symbol = str(raw or "").strip().upper()
    if not symbol:
        return None, "Lütfen önce bir hisse sembolü yazın."
    if len(symbol) > 20:
        return None, "Sembol beklenenden uzun görünüyor."
    if not re.fullmatch(r"[A-Z0-9.\^=_-]+", symbol):
        return None, "Sembol yalnızca harf, rakam ve . - _ ^ = karakterlerini içerebilir."
    return symbol, None


# Geçiş döneminde app2.py ve mevcut testlerin özel isimleri bozulmasın.
_finnhub_symbol = finnhub_symbol
_ticker_girdisini_dogrula = ticker_girdisini_dogrula
