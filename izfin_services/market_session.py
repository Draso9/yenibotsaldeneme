"""Canlı seans ve ticker bazlı piyasa hazırlığını Streamlit kabuğundan ayırır."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from izfin_core.market_data import abd_quote_regular_seans_mi, normalize_yf_columns


def _hata_bildir(error_handler, context, error, ticker=None):
    if error_handler is None:
        return
    try:
        if ticker is None:
            error_handler(context, error)
        else:
            error_handler(context, error, ticker)
    except Exception:
        pass


def intraday_local_index(ticker, df, *, error_handler=None):
    """Intraday indexini varlığın yerel piyasa saatine normalize eder."""
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    try:
        idx = pd.to_datetime(x.index)
        tz = "Europe/Istanbul" if str(ticker).endswith(".IS") else "America/New_York"
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize(tz)
        else:
            idx = idx.tz_convert(tz)
        x.index = idx
    except Exception as error:
        _hata_bildir(error_handler, "intraday_local_index", error, ticker)
    return x


def regular_seans_intraday(ticker, df, *, error_handler=None):
    """Teknik hesaplar için yalnızca normal seans mumlarını döndürür."""
    x = intraday_local_index(ticker, df, error_handler=error_handler)
    if x.empty:
        return x
    try:
        if str(ticker).endswith(".IS"):
            return x.between_time("10:00", "18:10", inclusive="both")
        return x.between_time("09:30", "16:00", inclusive="both")
    except Exception as error:
        _hata_bildir(error_handler, "regular_seans_intraday", error, ticker)
        return x


def seans_disi_ozet(ticker, ham_intraday, quote=None, *, error_handler=None):
    """ABD premarket/after-hours fiyatını yalnızca ek bilgi olarak özetler."""
    if str(ticker).endswith(".IS"):
        return "—", None

    x = intraday_local_index(ticker, ham_intraday, error_handler=error_handler)
    if x.empty or "Close" not in x.columns:
        if quote and quote.get("close", 0) > 0 and not abd_quote_regular_seans_mi(quote):
            try:
                px = float(quote["close"])
                return f"🌙 Seans dışı {px:.2f}", px
            except Exception as error:
                _hata_bildir(error_handler, "seans_disi_quote", error, ticker)
        return "—", None

    try:
        x = x.dropna(subset=["Close"]).sort_index()
        if x.empty:
            return "—", None
        son_ts = x.index[-1]
        son_dakika = son_ts.hour * 60 + son_ts.minute
        if (9 * 60 + 30) <= son_dakika <= (16 * 60):
            return "—", None
        son_fiyat = float(x["Close"].iloc[-1])
        tur = "PM" if son_dakika < (9 * 60 + 30) else "AH"
        regular = regular_seans_intraday(ticker, x, error_handler=error_handler)
        onceki_regular = regular[regular.index < son_ts] if not regular.empty else regular
        if not onceki_regular.empty:
            ref = float(onceki_regular["Close"].dropna().iloc[-1])
            if ref > 0:
                deg = ((son_fiyat / ref) - 1.0) * 100.0
                return f"🌙 {tur} {son_fiyat:.2f} ({deg:+.2f}%)", son_fiyat
        return f"🌙 {tur} {son_fiyat:.2f}", son_fiyat
    except Exception as error:
        _hata_bildir(error_handler, "seans_disi_ozet", error, ticker)
        return "—", None


def canli_ohlcv_ile_guncelle(
    ticker,
    df_long,
    *,
    intraday_hazir=None,
    quote_hazir=None,
    intraday_fetcher: Callable[..., Any] | None = None,
    quote_fetcher: Callable[[str], Any] | None = None,
    error_handler=None,
):
    """Günlük seriyi yalnızca normal seans OHLCV verisiyle günceller.

    Fetcher'lar dışarıdan enjekte edilir; böylece servis Streamlit cache veya ağ
    sağlayıcısına doğrudan bağımlı kalmaz.
    """
    df = df_long.copy().sort_index()
    kaynak = "Yahoo günlük (fallback)"

    quote = quote_hazir
    if quote is None and quote_fetcher is not None:
        try:
            quote = quote_fetcher(ticker)
        except Exception as error:
            _hata_bildir(error_handler, "finnhub_quote_fallback", error, ticker)
            quote = None

    ham_intraday = (
        intraday_hazir.copy()
        if isinstance(intraday_hazir, pd.DataFrame)
        else pd.DataFrame()
    )
    if ham_intraday.empty and intraday_fetcher is not None:
        try:
            ham_intraday = intraday_fetcher(ticker, interval="5m", period="5d")
        except Exception as error:
            _hata_bildir(error_handler, "yahoo_intraday_fallback", error, ticker)
            ham_intraday = pd.DataFrame()

    ham_intraday = normalize_yf_columns(ham_intraday)
    intraday = regular_seans_intraday(ticker, ham_intraday, error_handler=error_handler)
    if not intraday.empty and "Close" in intraday.columns:
        intraday = intraday.dropna(subset=["Close"]).sort_index()

    if not intraday.empty:
        seans_tarihi = intraday.index[-1].date()
        seans_rows = intraday[intraday.index.date == seans_tarihi]
        if not seans_rows.empty:
            o = float(seans_rows["Open"].dropna().iloc[0])
            h = float(seans_rows["High"].max())
            l = float(seans_rows["Low"].min())
            c = float(seans_rows["Close"].dropna().iloc[-1])
            v = (
                float(seans_rows["Volume"].fillna(0).sum())
                if "Volume" in seans_rows
                else 0.0
            )
            kaynak = (
                "Yahoo 5 dk (BIST normal seans)"
                if str(ticker).endswith(".IS")
                else "Yahoo 5 dk (ABD normal seans)"
            )

            if (
                not str(ticker).endswith(".IS")
                and quote
                and quote.get("close", 0) > 0
                and abd_quote_regular_seans_mi(quote)
            ):
                c = float(quote["close"])
                if quote.get("open", 0) > 0:
                    o = float(quote["open"])
                if quote.get("high", 0) > 0:
                    h = max(h, float(quote["high"]))
                if quote.get("low", 0) > 0:
                    l = min(l, float(quote["low"]))
                kaynak = "Finnhub fiyat + Yahoo 5 dk (normal seans)"

            last_daily_date = pd.Timestamp(df.index[-1]).date()
            if last_daily_date == seans_tarihi:
                target_idx = df.index[-1]
            else:
                target_idx = pd.Timestamp(seans_tarihi)
                if getattr(df.index, "tz", None) is not None:
                    target_idx = target_idx.tz_localize(df.index.tz)

            row = {"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            for col, val in row.items():
                if col in df.columns and pd.notna(val):
                    df.loc[target_idx, col] = val
            df = df.sort_index()
    elif quote and quote.get("close", 0) > 0:
        # Quote-only fallback geçmiş günlük mumu bozmaz.
        kaynak = "Yahoo günlük · Finnhub quote yalnızca ek fiyat"

    return df, intraday, kaynak, ham_intraday


def tekil_normal_seans_veri_cek(
    ticker,
    intraday_fetcher: Callable[..., Any] | None,
    *,
    error_handler=None,
):
    """Toplu intraday başarısızlığında normal-seans fallback verisi döndürür."""
    if intraday_fetcher is None:
        return pd.DataFrame()
    try:
        data = intraday_fetcher(ticker, interval="5m", period="5d")
    except Exception as error:
        _hata_bildir(error_handler, "yahoo_intraday_tekil_fallback", error, ticker)
        return pd.DataFrame()
    return regular_seans_intraday(ticker, data, error_handler=error_handler)


def ticker_piyasa_paketi_hazirla(
    ticker,
    df_long,
    *,
    intraday_hazir=None,
    quote_hazir=None,
    intraday_fetcher=None,
    quote_fetcher=None,
    error_handler=None,
):
    """Ticker analizinden önce canlı seans ve temel piyasa metriklerini paketler."""
    df_long, df_intraday, veri_kaynagi, ham_intraday = canli_ohlcv_ile_guncelle(
        ticker,
        df_long,
        intraday_hazir=intraday_hazir,
        quote_hazir=quote_hazir,
        intraday_fetcher=intraday_fetcher,
        quote_fetcher=quote_fetcher,
        error_handler=error_handler,
    )
    seans_disi_metin, seans_disi_fiyat = seans_disi_ozet(
        ticker,
        ham_intraday,
        quote_hazir if quote_hazir is not None else None,
        error_handler=error_handler,
    )

    bugun_kapanis = float(df_long["Close"].iloc[-1])
    onceki_kapanis = (
        float(df_long["Close"].iloc[-2])
        if len(df_long) >= 2
        else bugun_kapanis
    )
    gunluk_degisim = (
        ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100.0
        if onceki_kapanis > 0
        else 0.0
    )

    is_bist = str(ticker).endswith(".IS")
    para_birimi = "TL" if is_bist else "$"
    fiyat_str = (
        f"{bugun_kapanis:.2f} {para_birimi} "
        f"({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"
    )

    volume = pd.to_numeric(df_long["Volume"], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    ortalama_hacim_20 = volume.rolling(20).mean().iloc[-1]
    ortalama_ciro_tutar = (
        float(ortalama_hacim_20) * bugun_kapanis
        if pd.notna(ortalama_hacim_20)
        else 0.0
    )
    is_sig_tahta = ortalama_ciro_tutar < (
        50_000_000 if is_bist else 5_000_000
    )
    bugun_hacim = volume.iloc[-1] if len(volume) else np.nan
    hacim_sma20 = (
        volume.rolling(20, min_periods=5).mean().iloc[-1]
        if len(volume)
        else np.nan
    )

    return {
        "df_long": df_long,
        "df_intraday": df_intraday,
        "ham_intraday": ham_intraday,
        "veri_kaynagi": veri_kaynagi,
        "seans_disi_metin": seans_disi_metin,
        "seans_disi_fiyat": seans_disi_fiyat,
        "bugun_kapanis": bugun_kapanis,
        "onceki_kapanis": onceki_kapanis,
        "gunluk_degisim": gunluk_degisim,
        "is_bist": is_bist,
        "para_birimi": para_birimi,
        "fiyat_str": fiyat_str,
        "ortalama_hacim_20": ortalama_hacim_20,
        "ortalama_ciro_tutar": ortalama_ciro_tutar,
        "is_sig_tahta": bool(is_sig_tahta),
        "bugun_hacim": bugun_hacim,
        "hacim_sma20": hacim_sma20,
    }
