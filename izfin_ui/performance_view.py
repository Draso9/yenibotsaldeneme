from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from izfin_core.performance_engine import _guvenli_dict, performans_karnesi_ozeti


def _naive_tarih_serisi(seri: pd.Series) -> pd.Series:
    if seri.empty:
        return seri
    return seri.dt.tz_localize(None) if getattr(seri.dt, "tz", None) is not None else seri


def performans_pozisyon_paketi_hazirla(
    kayitlar: Sequence[Mapping[str, Any]] | None,
    *,
    simdi_ts: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Takip ekranı için açık/kapalı pozisyonları ve üst KPI'ları hazırlar."""
    df_perf = pd.DataFrame(list(kayitlar or [])).reset_index(drop=True)
    if df_perf.empty:
        return {
            "df_perf": df_perf,
            "acik_df": pd.DataFrame(),
            "kapali_df": pd.DataFrame(),
            "acik_gecen": pd.Series(dtype=float),
            "pozitif": 0,
            "negatif": 0,
            "ort_getiri": 0.0,
        }

    for col in ["giris_fiyati", "son_fiyat", "kapanis_fiyati", "getiri_yuzde"]:
        if col in df_perf.columns:
            df_perf[col] = pd.to_numeric(df_perf[col], errors="coerce")

    if "durum" not in df_perf.columns:
        df_perf["durum"] = "ACIK"
    df_perf["durum"] = (
        df_perf["durum"]
        .fillna("ACIK")
        .replace({"None": "ACIK", "": "ACIK"})
        .astype(str)
        .str.upper()
    )
    df_perf["_tarih"] = pd.to_datetime(df_perf.get("olusturma_zamani"), errors="coerce")
    df_perf["_kapanis_tarih"] = pd.to_datetime(df_perf.get("kapanis_zamani"), errors="coerce")

    acik_df = df_perf[df_perf["durum"].eq("ACIK")].copy()
    if not acik_df.empty:
        acik_df["ticker"] = acik_df["ticker"].fillna("").astype(str).str.strip().str.upper()
    acik_df = (
        acik_df.sort_values(["ticker", "_tarih"], ascending=[True, True])
        .drop_duplicates(subset=["ticker"], keep="first")
        .sort_values("_tarih", ascending=False)
        .reset_index(drop=True)
    )

    kapali_df = df_perf[df_perf["durum"].eq("KAPALI")].copy()
    if not kapali_df.empty:
        kapali_df["_giris_gun"] = kapali_df["_tarih"].dt.floor("D")
        kapali_df["_kapanis_gun"] = kapali_df["_kapanis_tarih"].dt.floor("D")
        kapali_df["_giris_fiyat_key"] = pd.to_numeric(
            kapali_df.get("giris_fiyati"), errors="coerce"
        ).round(4)
        kapali_df["_doluluk"] = kapali_df.notna().sum(axis=1)
        kapali_df = (
            kapali_df.sort_values(
                ["_doluluk", "_kapanis_tarih", "_tarih"],
                ascending=[False, False, True],
                na_position="last",
            )
            .drop_duplicates(
                subset=["ticker", "_giris_gun", "_giris_fiyat_key", "_kapanis_gun"],
                keep="first",
            )
            .sort_values(["_kapanis_tarih", "_tarih"], ascending=False)
            .drop(
                columns=["_giris_gun", "_kapanis_gun", "_giris_fiyat_key", "_doluluk"],
                errors="ignore",
            )
            .reset_index(drop=True)
        )

    simdi_ts = pd.Timestamp.now(tz=None) if simdi_ts is None else pd.Timestamp(simdi_ts)
    if simdi_ts.tzinfo is not None:
        simdi_ts = simdi_ts.tz_localize(None)
    acik_tarih = (
        _naive_tarih_serisi(acik_df["_tarih"])
        if not acik_df.empty
        else pd.Series(dtype="datetime64[ns]")
    )
    acik_gecen = (
        (simdi_ts.normalize() - acik_tarih.dt.normalize()).dt.days.clip(lower=0)
        if not acik_df.empty
        else pd.Series(dtype=float)
    )

    getiriler = pd.to_numeric(
        acik_df.get("getiri_yuzde", pd.Series(dtype=float)), errors="coerce"
    )
    pozitif = int((getiriler > 0).sum())
    negatif = int((getiriler < 0).sum())
    ort_getiri = float(getiriler.mean()) if not acik_df.empty else 0.0

    return {
        "df_perf": df_perf,
        "acik_df": acik_df,
        "kapali_df": kapali_df,
        "acik_gecen": acik_gecen,
        "pozitif": pozitif,
        "negatif": negatif,
        "ort_getiri": ort_getiri,
    }


def aktif_pozisyon_gorunumu_hazirla(
    acik_df: pd.DataFrame,
    acik_gecen: pd.Series,
) -> pd.DataFrame:
    """Aktif pozisyon HTML renderer'ının beklediği kolonları üretir."""
    if acik_df is None or acik_df.empty:
        return pd.DataFrame()
    ilk_sinyal = (
        acik_df.get("ilk_sinyal").fillna("— Eski kayıt")
        if "ilk_sinyal" in acik_df.columns
        else pd.Series(["— Eski kayıt"] * len(acik_df))
    )
    return pd.DataFrame(
        {
            "İlk Alım Tarihi": acik_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
            "Varlık": acik_df.get("ticker"),
            "İlk Sinyal": ilk_sinyal,
            "Güncel Sinyal": acik_df.get("sinyal"),
            "İlk Alım Fiyatı": acik_df.get("giris_fiyati"),
            "Güncel Fiyat": acik_df.get("son_fiyat"),
            "Kâr / Zarar %": acik_df.get("getiri_yuzde"),
            "Geçen Gün": acik_gecen.reset_index(drop=True),
            "Durum": "🟢 Açık",
        }
    )


def _ufuk_extreme(row: pd.Series, tip: str = "max") -> float:
    ufuklar = _guvenli_dict(row.get("performans_ufuklari"))
    vals: list[float] = []
    if isinstance(ufuklar, dict):
        for item in ufuklar.values():
            try:
                g = float((item or {}).get("getiri"))
                if np.isfinite(g):
                    vals.append(g)
            except Exception:
                pass

    direkt_alan = "max_yukselis_45g" if tip == "max" else "max_dusus_45g"
    try:
        direkt = float(row.get(direkt_alan))
        if np.isfinite(direkt):
            return direkt
    except Exception:
        pass
    if not vals:
        return np.nan
    return max(vals) if tip == "max" else min(vals)


def _hedef_gordu(row: pd.Series, hedef_no: int) -> str:
    kayitli = row.get(f"ilk_tp{hedef_no}_gordu")
    if isinstance(kayitli, (bool, np.bool_)):
        return "✅" if bool(kayitli) else "❌"
    try:
        giris = float(row.get("giris_fiyati"))
        hedef = float(row.get(f"ilk_tp{hedef_no}"))
    except Exception:
        return "—"
    if not np.isfinite(giris) or giris <= 0 or not np.isfinite(hedef) or hedef <= 0:
        return "—"
    gorulen = _ufuk_extreme(row, "max")
    if not np.isfinite(gorulen):
        return "—"
    return "✅" if gorulen >= ((hedef / giris) - 1) * 100 else "❌"


def kapanmis_pozisyon_gorunumu_hazirla(kapali_df: pd.DataFrame) -> pd.DataFrame:
    """Kapanmış pozisyon tablosunun hesaplanan/fallback alanlarını tek yerde üretir."""
    if kapali_df is None or kapali_df.empty:
        return pd.DataFrame()

    giris_fiyat_seri = pd.to_numeric(kapali_df.get("giris_fiyati"), errors="coerce")
    kapanis_fiyat_seri = pd.to_numeric(
        kapali_df.get("kapanis_fiyati", kapali_df.get("son_fiyat")), errors="coerce"
    )
    hesaplanan_getiri = ((kapanis_fiyat_seri / giris_fiyat_seri) - 1.0) * 100.0
    mevcut_getiri = pd.to_numeric(kapali_df.get("getiri_yuzde"), errors="coerce")
    kapanis_getiri = mevcut_getiri.where(mevcut_getiri.notna(), hesaplanan_getiri)

    pozisyonda_gun = (
        (kapali_df["_kapanis_tarih"] - kapali_df["_tarih"]).dt.total_seconds()
        / 86400.0
    ).clip(lower=0)

    max_kar = pd.to_numeric(
        kapali_df.get("donem_max_kar", pd.Series(np.nan, index=kapali_df.index)),
        errors="coerce",
    )
    max_dusus = pd.to_numeric(
        kapali_df.get("donem_max_dusus", pd.Series(np.nan, index=kapali_df.index)),
        errors="coerce",
    )
    eski_max = kapali_df.apply(lambda r: _ufuk_extreme(r, "max"), axis=1)
    eski_min = kapali_df.apply(lambda r: _ufuk_extreme(r, "min"), axis=1)
    max_kar = max_kar.where(max_kar.notna(), eski_max)
    max_dusus = max_dusus.where(max_dusus.notna(), eski_min)

    return pd.DataFrame(
        {
            "İlk Alım Tarihi": kapali_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
            "Kapanış Tarihi": kapali_df["_kapanis_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
            "Varlık": kapali_df.get("ticker"),
            "Son Alım Sinyali": kapali_df.get("sinyal"),
            "Kapanış Nedeni": kapali_df.get("kapanis_sinyali"),
            "İlk Alım Fiyatı": giris_fiyat_seri,
            "Kapanış Fiyatı": kapanis_fiyat_seri,
            "Kâr / Zarar %": kapanis_getiri,
            "Pozisyonda Gün": pozisyonda_gun.round(1),
            "Maks. Kâr %": max_kar,
            "Maks. Düşüş %": max_dusus,
            "İlk Stop": pd.to_numeric(
                kapali_df.get("ilk_stop", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
            ),
            "İlk TP1": pd.to_numeric(
                kapali_df.get("ilk_tp1", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
            ),
            "İlk TP2": pd.to_numeric(
                kapali_df.get("ilk_tp2", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
            ),
            "İlk TP3": pd.to_numeric(
                kapali_df.get("ilk_tp3", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
            ),
            "TP1": kapali_df.apply(lambda r: _hedef_gordu(r, 1), axis=1),
            "TP2": kapali_df.apply(lambda r: _hedef_gordu(r, 2), axis=1),
            "TP3": kapali_df.apply(lambda r: _hedef_gordu(r, 3), axis=1),
            "Stop": kapali_df.apply(
                lambda r: (
                    "✅" if bool(r.get("ilk_stop_gordu")) else "❌"
                )
                if isinstance(r.get("ilk_stop_gordu"), (bool, np.bool_))
                else "—",
                axis=1,
            ),
            "Durum": "⚪ Kapalı",
        }
    )


def kapanmis_performans_ozeti_hazirla(kapanmis_gorunum: pd.DataFrame) -> dict[str, Any]:
    """Kapanmış dönem KPI ve açıklama view-modelini üretir."""
    kg = pd.DataFrame() if kapanmis_gorunum is None else kapanmis_gorunum.copy()
    if kg.empty:
        return {
            "adet": 0,
            "unique_tickers": 0,
            "win_rate": np.nan,
            "avg_ret": np.nan,
            "median_ret": np.nan,
            "median_days": np.nan,
            "tp1_rate": np.nan,
            "stop_rate": np.nan,
            "best_txt": "—",
            "worst_txt": "—",
            "yorumlar": [],
            "reason_counts": [],
        }

    ret = pd.to_numeric(kg["Kâr / Zarar %"], errors="coerce")
    days = pd.to_numeric(kg["Pozisyonda Gün"], errors="coerce")
    valid_ret = ret.dropna()
    win_rate = float((valid_ret > 0).mean() * 100) if not valid_ret.empty else np.nan
    avg_ret = float(valid_ret.mean()) if not valid_ret.empty else np.nan
    median_ret = float(valid_ret.median()) if not valid_ret.empty else np.nan
    median_days = float(days.dropna().median()) if not days.dropna().empty else np.nan
    unique_tickers = int(kg["Varlık"].nunique()) if "Varlık" in kg.columns else 0

    tp1_rate = np.nan
    if "TP1" in kg.columns:
        tp1_vals = kg["TP1"].astype(str).str.upper()
        tp1_rate = float(tp1_vals.isin(["EVET", "TRUE", "1", "✓", "✅"]).mean() * 100)

    stop_rate = np.nan
    if "Stop" in kg.columns:
        stop_vals = kg["Stop"].astype(str).str.upper()
        stop_rate = float(stop_vals.isin(["EVET", "TRUE", "1", "✓", "✅"]).mean() * 100)

    best_txt = "—"
    worst_txt = "—"
    if not valid_ret.empty:
        try:
            best_i = ret.idxmax()
            worst_i = ret.idxmin()
            best_txt = f"{kg.loc[best_i, 'Varlık']} %{float(ret.loc[best_i]):+.1f}"
            worst_txt = f"{kg.loc[worst_i, 'Varlık']} %{float(ret.loc[worst_i]):+.1f}"
        except Exception:
            pass

    yorumlar: list[str] = []
    if np.isfinite(win_rate):
        if win_rate >= 65:
            yorumlar.append(
                f"Kapanmış alım dönemlerinin %{win_rate:.0f}'i pozitif sonuçlanmış; geçmiş sinyal seçimi güçlü görünüyor."
            )
        elif win_rate >= 50:
            yorumlar.append(
                f"Kapanmış alım dönemlerinin %{win_rate:.0f}'i pozitif; sistem geçmişte hafif pozitif bir seçicilik göstermiş."
            )
        else:
            yorumlar.append(
                f"Pozitif kapanış oranı %{win_rate:.0f}; geçmiş sinyal seçimi daha seçici filtrelere ihtiyaç duyabilir."
            )

    if np.isfinite(avg_ret) and np.isfinite(median_ret):
        if avg_ret > median_ret + 2:
            yorumlar.append(
                "Ortalama getiri medyanın belirgin üzerinde; birkaç güçlü kazanan toplam performansı yukarı taşıyor."
            )
        elif median_ret > avg_ret + 2:
            yorumlar.append(
                "Medyan getiri ortalamanın üzerinde; birkaç zayıf dönem genel ortalamayı aşağı çekiyor."
            )
        elif avg_ret > 0:
            yorumlar.append(
                "Ortalama ve medyan getiri birbirine yakın; sonuç dağılımı görece dengeli."
            )
        else:
            yorumlar.append(
                "Ortalama ve medyan getirinin birlikte zayıf olması, kapanış disiplininin ayrıca incelenmesini gerektiriyor."
            )

    if np.isfinite(tp1_rate) and np.isfinite(stop_rate):
        if tp1_rate > stop_rate + 10:
            yorumlar.append(
                "TP1 görülme oranı stop görülme oranından belirgin yüksek; giriş sonrası olumlu hareket üretme kapasitesi iyi."
            )
        elif stop_rate > tp1_rate + 10:
            yorumlar.append(
                "Stop görülme oranı TP1 oranından yüksek; giriş zamanlaması veya risk filtresi geliştirilebilir."
            )
        else:
            yorumlar.append(
                "TP1 ve stop görülme oranları birbirine yakın; sinyal sonrası yön ayrışması sınırlı."
            )

    if unique_tickers <= 3 and len(kg) >= 5:
        yorumlar.append(
            "Sonuçların önemli bölümü az sayıda hissede yoğunlaşmış; genelleme yaparken örneklem çeşitliliğine dikkat edilmeli."
        )

    reason_counts: list[tuple[str, int]] = []
    if "Kapanış Nedeni" in kg.columns:
        counts = kg["Kapanış Nedeni"].fillna("Belirsiz").astype(str).value_counts().head(5)
        reason_counts = [(str(k), int(v)) for k, v in counts.items()]

    return {
        "adet": int(len(kg)),
        "unique_tickers": unique_tickers,
        "win_rate": win_rate,
        "avg_ret": avg_ret,
        "median_ret": median_ret,
        "median_days": median_days,
        "tp1_rate": tp1_rate,
        "stop_rate": stop_rate,
        "best_txt": best_txt,
        "worst_txt": worst_txt,
        "yorumlar": yorumlar[:4],
        "reason_counts": reason_counts,
    }


def performans_karne_paketi_hazirla(
    kayitlar: Sequence[Mapping[str, Any]] | None,
    *,
    gun: int,
) -> dict[str, Any]:
    """Karne motoru çıktısını kullanıcıya gösterilecek özet ve tablolara dönüştürür."""
    karne_df = performans_karnesi_ozeti(kayitlar, gun=int(gun))
    if karne_df.empty:
        return {
            "karne_df": karne_df,
            "pozitif_oran": np.nan,
            "medyan_getiri": np.nan,
            "benchmark_ustu": np.nan,
            "medyan_alfa": np.nan,
            "gorunum": pd.DataFrame(),
            "detay": pd.DataFrame(),
            "detay_kolonlari": [],
            "kucuk_orneklem": True,
        }

    pozitif_oran = float((karne_df["getiri"] > 0).mean() * 100)
    medyan_getiri = float(karne_df["getiri"].median())
    alfa_seri = pd.to_numeric(karne_df["alfa"], errors="coerce").dropna()
    benchmark_ustu = float((alfa_seri > 0).mean() * 100) if not alfa_seri.empty else np.nan
    medyan_alfa = float(alfa_seri.median()) if not alfa_seri.empty else np.nan

    detay_karne = karne_df.copy()
    detay_karne["getiri"] = pd.to_numeric(detay_karne["getiri"], errors="coerce")
    detay_karne["alfa"] = pd.to_numeric(detay_karne["alfa"], errors="coerce")

    gorunum = (
        detay_karne.groupby("ticker", dropna=False)
        .agg(
            **{
                "Sinyal Sayısı": ("getiri", "size"),
                "Başarı Oranı %": ("getiri", lambda x: float((x > 0).mean() * 100)),
                f"+{int(gun)}G Medyan Getiri %": ("getiri", "median"),
                "Medyan Benchmark Farkı %": ("alfa", "median"),
            }
        )
        .reset_index()
        .rename(columns={"ticker": "Varlık"})
        .sort_values(f"+{int(gun)}G Medyan Getiri %", ascending=False)
    )

    detay = detay_karne.copy()
    detay["sinyal_tarihi"] = pd.to_datetime(
        detay["sinyal_tarihi"], errors="coerce"
    ).dt.strftime("%d.%m.%Y")
    detay = detay.rename(
        columns={
            "ticker": "Varlık",
            "sinyal_tarihi": "Sinyal Tarihi",
            "sinyal": "Sinyal",
            "getiri": f"+{int(gun)}G Getiri %",
            "alfa": "Benchmark Farkı %",
        }
    )
    detay_kolonlari = [
        "Varlık",
        "Sinyal Tarihi",
        "Sinyal",
        f"+{int(gun)}G Getiri %",
        "Benchmark Farkı %",
    ]
    detay_kolonlari = [
        c for c in detay_kolonlari if c in detay.columns and not detay[c].isna().all()
    ]

    return {
        "karne_df": karne_df,
        "pozitif_oran": pozitif_oran,
        "medyan_getiri": medyan_getiri,
        "benchmark_ustu": benchmark_ustu,
        "medyan_alfa": medyan_alfa,
        "gorunum": gorunum,
        "detay": detay,
        "detay_kolonlari": detay_kolonlari,
        "kucuk_orneklem": len(karne_df) < 30,
    }
