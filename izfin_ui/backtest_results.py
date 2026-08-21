"""Framework-neutral result presenters for the IZFIN Strategy Laboratory."""

from __future__ import annotations

from typing import Any

import pandas as pd


BACKTEST_DETAY_ACIKLAMA = (
    "Bu tablo, geçmişte hangi tarihte hangi merkezi IZFIN kararının işlem açtığını "
    "ve karar anındaki günlük çekirdek puanlarını gösterir."
)

BACKTEST_OKUMA_NOTLARI = """
- **Bu test artık eski basit dört koşulu değil, IZFIN'in günlük çekirdek analiz zincirini geçmişte yeniden çalıştırır.** Hibrit skor, ADX/DI, CMF, SuperTrend, risk, teknik profil, güven ve merkezi karar birlikte değerlendirilir.
- **Yalnızca merkezi motorun GÜÇLÜ AL / AL / ERKEN AL aksiyonları işlem açar.** TEYİT BEKLE ve İZLE geçmiş işlem sayılmaz.
- **Daily MTF % ve Giriş Proxy**, 5–10 yıllık intraday geçmiş bulunmadığı için günlük veriden türetilen doğrulama alanlarıdır; canlı 5dk/15dk/1s Giriş Motoruymuş gibi sunulmaz.
- **20G / 45G sonuçları**, çıkıştan bağımsız sabit ufuk ölçümüdür; hissenin karar sonrası yön seçme kalitesini gösterir.
- İlk Stop ve TP1 yalnızca sinyal gününe kadar bilinen verilerle hesaplanıp dondurulur. Aynı gün ikisi de görülürse test muhafazakâr biçimde Stop'u önce kabul eder.
- Komisyon, vergi, spread ve gerçek emir kayması modellenmez; sonuçlar gerçek işlem getirisi garantisi değildir.
"""

BACKTEST_OZET_FORMAT = {
    "Örnek": "{:.0f}",
    "İşlem Başarı %": "{:.1f}%",
    "Ort. İşlem %": "{:+.2f}%",
    "TP1 İlk %": "{:.1f}%",
    "Stop İlk %": "{:.1f}%",
    "20G Kârda %": "{:.1f}%",
    "20G Ort. %": "{:+.2f}%",
    "45G Kârda %": "{:.1f}%",
    "45G Ort. %": "{:+.2f}%",
}

BACKTEST_DETAY_KOLONLARI = [
    "Tarih",
    "Sinyal",
    "Teknik Profil",
    "Ön Sinyal",
    "Hibrit Skor",
    "Güven %",
    "Daily MTF %",
    "Giriş Proxy",
    "Giriş",
    "İlk Stop",
    "İlk TP1",
    "İlk Olay",
    "İşlem Sonucu %",
    "20G %",
    "45G %",
]

BACKTEST_DETAY_FORMAT = {
    "Hibrit Skor": "{:.0f}",
    "Güven %": "{:.0f}",
    "Daily MTF %": "{:.0f}",
    "Giriş Proxy": "{:.0f}",
    "Giriş": "{:.2f}",
    "İlk Stop": "{:.2f}",
    "İlk TP1": "{:.2f}",
    "İşlem Sonucu %": "{:+.2f}%",
    "20G %": "{:+.2f}%",
    "45G %": "{:+.2f}%",
}


def backtest_karar_ozeti_hazirla(bt: pd.DataFrame) -> pd.DataFrame:
    """Aggregate historical trades by the central IZFIN decision label."""
    if bt is None or bt.empty:
        return pd.DataFrame(
            columns=["Sinyal", *BACKTEST_OZET_FORMAT.keys()]
        )

    gerekli = {
        "Sinyal",
        "İşlem Sonucu %",
        "İlk Olay",
        "20G %",
        "45G %",
    }
    eksik = gerekli.difference(bt.columns)
    if eksik:
        raise KeyError(f"Backtest özet alanları eksik: {', '.join(sorted(eksik))}")

    return (
        bt.groupby("Sinyal")
        .agg(
            Örnek=("Sinyal", "size"),
            **{
                "İşlem Başarı %": (
                    "İşlem Sonucu %",
                    lambda x: (x > 0).mean() * 100,
                ),
                "Ort. İşlem %": ("İşlem Sonucu %", "mean"),
                "TP1 İlk %": (
                    "İlk Olay",
                    lambda x: (x == "TP1").mean() * 100,
                ),
                "Stop İlk %": (
                    "İlk Olay",
                    lambda x: x.astype(str).str.startswith("STOP").mean() * 100,
                ),
                "20G Kârda %": ("20G %", lambda x: (x > 0).mean() * 100),
                "20G Ort. %": ("20G %", "mean"),
                "45G Kârda %": ("45G %", lambda x: (x > 0).mean() * 100),
                "45G Ort. %": ("45G %", "mean"),
            },
        )
        .reset_index()
        .sort_values(["İşlem Başarı %", "Örnek"], ascending=False)
        .reset_index(drop=True)
    )


def backtest_detay_gorunumu_hazirla(bt: pd.DataFrame) -> pd.DataFrame:
    """Prepare the historical decision table without Streamlit formatting."""
    if bt is None or bt.empty:
        return pd.DataFrame(columns=BACKTEST_DETAY_KOLONLARI)

    kolonlar = [k for k in BACKTEST_DETAY_KOLONLARI if k in bt.columns]
    detay = bt[kolonlar].copy()
    if "Tarih" in detay.columns:
        detay["Tarih"] = pd.to_datetime(
            detay["Tarih"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
    return detay


def backtest_sonuc_paketi_hazirla(bt: pd.DataFrame) -> dict[str, Any]:
    """Return all renderer-ready Strategy Laboratory result view-models."""
    ozet = backtest_karar_ozeti_hazirla(bt)
    detay = backtest_detay_gorunumu_hazirla(bt)
    return {
        "ozet": ozet,
        "ozet_format": dict(BACKTEST_OZET_FORMAT),
        "detay": detay,
        "detay_format": {
            key: value
            for key, value in BACKTEST_DETAY_FORMAT.items()
            if key in detay.columns
        },
        "detay_height": min(520, 82 + 35 * len(detay)),
        "detay_aciklama": BACKTEST_DETAY_ACIKLAMA,
        "okuma_notlari": BACKTEST_OKUMA_NOTLARI,
    }
