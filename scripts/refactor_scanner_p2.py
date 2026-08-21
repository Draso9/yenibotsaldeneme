"""One-shot scanner P2 refactor for app2.py.

Temporary helper for branch refactor/scanner-p2. It wires the remaining indicator,
risk/volatility and breakout calculations through izfin_core.scanner_engine while
leaving Streamlit orchestration and session-state behavior unchanged.
"""
from __future__ import annotations

import ast
from pathlib import Path

APP = Path("app2.py")
OLD_IMPORT = 'from izfin_core.scanner_engine import (\n    goreceli_guc_ve_hacim_hesapla,\n    hibrit_skor_hesapla,\n    on_sinyal_belirle,\n)\n'
NEW_IMPORT = 'from izfin_core.scanner_engine import (\n    breakout_kosulu_hesapla,\n    goreceli_guc_ve_hacim_hesapla,\n    hibrit_skor_hesapla,\n    on_sinyal_belirle,\n    risk_volatilite_hazirla,\n    temel_teknik_gostergeleri_hesapla,\n)\n'
INDICATOR_START = "                        delta = df_long['Close'].diff()\n"
INDICATOR_END = '                        # Gelişmiş teyitler: ADX, CMF, A/D, SuperTrend, VWAP ve çoklu zaman dilimi.\n'
NEW_INDICATORS = '                        # RSI, MACD, SMA200, Bollinger, MFI, OBV ve EMA\'lar saf scanner motorunda.\n                        temel = temel_teknik_gostergeleri_hesapla(df_long)\n                        rsi = temel["rsi"]\n                        macd_serisi = temel["macd_serisi"]\n                        macd_sinyal = temel["macd_sinyal"]\n                        sma_200 = temel["sma200"]\n                        uzun_vade_trend = temel["uzun_vade_trend"]\n                        bb_mid = temel["bb_mid"]\n                        bb_ust = temel["bb_ust"]\n                        bb_alt = temel["bb_alt"]\n                        mfi_val = temel["mfi"]\n                        obv = temel["obv"]\n                        obv_ema = temel["obv_ema"]\n                        ema_9_val = temel["ema9"]\n                        ema_21_val = temel["ema21"]\n                        ema_50_val = temel["ema50"]\n\n'
RISK_START = '                        # Destek/direnç referanslarında mevcut mumu hariç tutmak,\n'
RISK_END = '                        # Ön sinyal öncelik sırası artık saf scanner motorunda tutulur.\n'
NEW_RISK = '                        # ATR, volatilite, stop, destek/direnç ve hedefler saf scanner motorunda.\n                        risk_paket = risk_volatilite_hazirla(\n                            df_long,\n                            fiyat=bugun_kapanis,\n                            ema50=ema_50_val,\n                            bb_alt=bb_alt,\n                            bb_mid=bb_mid,\n                            bb_ust=bb_ust,\n                            adx=adx,\n                        )\n                        swing_high = risk_paket["swing_high"]\n                        swing_low = risk_paket["swing_low"]\n                        atr = risk_paket["atr"]\n                        hv20 = risk_paket["hv20"]\n                        hv60 = risk_paket["hv60"]\n                        karma_destek = risk_paket["destek"]\n                        karma_direnc = risk_paket["direnc"]\n                        trailing_stop = risk_paket["stop"]\n                        risk_yuzde = risk_paket["risk_yuzde"]\n                        risk_seviyesi = risk_paket["risk_seviyesi"]\n                        vol_rejimi = risk_paket["volatilite_rejimi"]\n                        seviyeler = risk_paket["seviyeler"]\n                        tp1 = risk_paket["tp1"]\n                        tp2 = risk_paket["tp2"]\n                        tp3 = risk_paket["tp3"]\n                        risk_odul = risk_paket["risk_odul"]\n                        hibrit_tp = risk_paket["hibrit_tp"]\n\n                        # Kırılım referansı ve koşulu da tek saf hesapta değerlendirilir.\n                        breakout_paket = breakout_kosulu_hesapla(\n                            fiyat=bugun_kapanis,\n                            swing_high=swing_high,\n                            onceki_bb_ust=temel["onceki_bb_ust"],\n                            atr=atr,\n                            hacim_oran=hacim_oran,\n                            ema9=ema_9_val,\n                            ema21=ema_21_val,\n                            uzun_vade_trend=uzun_vade_trend,\n                        )\n                        kirilim_referansi = breakout_paket["referans"]\n                        breakout_kosulu = breakout_paket["kosul"]\n\n'
TARGET_MARKERS = (
    "breakout_kosulu_hesapla(",
    "risk_volatilite_hazirla(",
    "temel_teknik_gostergeleri_hesapla(",
)


def replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start_count = text.count(start_marker)
    end_count = text.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise RuntimeError(f"{label}: marker mismatch (start={start_count}, end={end_count})")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + replacement + text[end:]


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    if all(marker in text for marker in TARGET_MARKERS) and NEW_IMPORT in text:
        print("scanner P2 already applied; nothing to do")
        ast.parse(text, filename=str(APP))
        return
    partial = [marker for marker in TARGET_MARKERS if marker in text]
    if partial:
        raise RuntimeError(f"scanner P2 appears partially applied: {partial}")
    text = replace_exact_once(text, OLD_IMPORT, NEW_IMPORT, "scanner import block")
    text = replace_between(text, INDICATOR_START, INDICATOR_END, NEW_INDICATORS, "technical indicator block")
    text = replace_between(text, RISK_START, RISK_END, NEW_RISK, "risk/breakout block")
    ast.parse(text, filename=str(APP))
    for marker in TARGET_MARKERS:
        if marker not in text:
            raise RuntimeError(f"missing target marker after refactor: {marker}")
    APP.write_text(text, encoding="utf-8")
    print("scanner P2 refactor applied successfully")


if __name__ == "__main__":
    main()
