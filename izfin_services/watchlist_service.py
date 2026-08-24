"""Framework-neutral personal watchlist and symbol-search workflows."""

from __future__ import annotations

from typing import Any, Callable

from izfin_services.bootstrap_service import kullanici_watchlist_kaydet


def _ticker_listesi(values) -> list[str]:
    return list(
        dict.fromkeys(
            str(value).strip().upper()
            for value in (values or [])
            if str(value).strip()
        )
    )


def _sonuc(
    *,
    status: str,
    message: str,
    tickers,
    symbol: str = "",
    clear_input: bool = False,
) -> dict[str, Any]:
    return {
        "ok": status == "success",
        "status": status,
        "message": message,
        "tickers": _ticker_listesi(tickers),
        "symbol": symbol,
        "clear_input": bool(clear_input),
    }


def watchlist_sembol_ekle(
    user_repository,
    *,
    uid: str | None,
    email: str | None,
    tickers,
    raw_symbol: str | None,
    validator: Callable[[str], tuple[str | None, str | None]] | None = None,
    now_factory=None,
    error_handler: Callable[[str, Exception, str | None], Any] | None = None,
) -> dict[str, Any]:
    """Validate, add and persist one symbol with rollback-safe result data."""
    mevcut = _ticker_listesi(tickers)
    try:
        if validator is None:
            symbol = str(raw_symbol or "").strip().upper()
            hata = None if symbol else "Lütfen bir sembol yazın."
        else:
            symbol, hata = validator(str(raw_symbol or ""))
            symbol = str(symbol or "").strip().upper()
        if hata:
            return _sonuc(
                status="error",
                message=f"Hisse eklenemedi: {hata}",
                tickers=mevcut,
            )
        if symbol in mevcut:
            return _sonuc(
                status="warning",
                message=f"{symbol} zaten kişisel listenizde bulunuyor.",
                tickers=mevcut,
                symbol=symbol,
            )

        yeni_liste = mevcut + [symbol]
        kullanici_watchlist_kaydet(
            user_repository,
            uid=uid,
            email=email,
            tickers=yeni_liste,
            now_factory=now_factory,
        )
        return _sonuc(
            status="success",
            message=f"{symbol} kişisel listenize başarıyla eklendi.",
            tickers=yeni_liste,
            symbol=symbol,
            clear_input=True,
        )
    except Exception as error:
        symbol = locals().get("symbol", "")
        if error_handler:
            try:
                error_handler("watchlist_sembol_ekle", error, symbol or None)
            except Exception:
                pass
        if not symbol:
            return _sonuc(
                status="error",
                message="Hisse listeye eklenemedi: beklenmeyen bir işlem hatası oluştu.",
                tickers=mevcut,
            )
        return _sonuc(
            status="error",
            message=f"{symbol} listeye eklenemedi: kayıt işlemi tamamlanamadı.",
            tickers=mevcut,
            symbol=symbol,
        )


def watchlist_sembolleri_sil(
    user_repository,
    *,
    uid: str | None,
    email: str | None,
    tickers,
    raw_symbols: str | None,
    now_factory=None,
    error_handler: Callable[[str, Exception, str | None], Any] | None = None,
) -> dict[str, Any]:
    """Remove one or more symbols and persist only after a meaningful change."""
    mevcut = _ticker_listesi(tickers)
    semboller = _ticker_listesi(str(raw_symbols or "").replace(",", " ").split())
    if not semboller:
        return _sonuc(
            status="error",
            message="Silinecek bir sembol yazın.",
            tickers=mevcut,
        )

    bulunan = [symbol for symbol in semboller if symbol in mevcut]
    bulunamayan = [symbol for symbol in semboller if symbol not in mevcut]
    if not bulunan:
        return _sonuc(
            status="warning",
            message=f"Listede bulunamadı: {', '.join(bulunamayan)}",
            tickers=mevcut,
        )

    yeni_liste = [symbol for symbol in mevcut if symbol not in bulunan]
    try:
        kullanici_watchlist_kaydet(
            user_repository,
            uid=uid,
            email=email,
            tickers=yeni_liste,
            now_factory=now_factory,
        )
    except Exception as error:
        if error_handler:
            try:
                error_handler("watchlist_sembolleri_sil", error, ",".join(bulunan))
            except Exception:
                pass
        return _sonuc(
            status="error",
            message=f"Silme işlemi kaydedilemedi: {error}",
            tickers=mevcut,
        )

    ek = f" Listede bulunamayan: {', '.join(bulunamayan)}." if bulunamayan else ""
    return _sonuc(
        status="success",
        message=f"{', '.join(bulunan)} kişisel listenizden silindi.{ek}",
        tickers=yeni_liste,
        clear_input=True,
    )


def sembol_onerileri_getir(
    arama: str | None,
    *,
    yahoo_search: Callable[[str], list[dict[str, Any]]],
    finnhub_search: Callable[[str], dict[str, Any]] | None = None,
    local_universe=(),
    error_handler: Callable[[str, Exception], Any] | None = None,
    limit: int = 15,
) -> list[dict[str, str]]:
    """Aggregate Yahoo, Finnhub and local-universe matches without session state."""
    query = str(arama or "").strip()
    if not query:
        return []

    query_upper = query.upper()
    sonuc: list[dict[str, str]] = []
    seen: set[str] = set()

    def ekle(symbol, name="", exchange="", quote_type="") -> None:
        symbol_norm = str(symbol or "").strip().upper()
        if not symbol_norm or symbol_norm in seen:
            return
        seen.add(symbol_norm)
        sonuc.append(
            {
                "symbol": symbol_norm,
                "name": str(name or "").strip(),
                "exchange": str(exchange or "").strip(),
                "quote_type": str(quote_type or "").strip(),
            }
        )

    try:
        for item in yahoo_search(query) or []:
            ekle(
                item.get("symbol"),
                item.get("name"),
                item.get("exchange"),
                item.get("quote_type"),
            )
    except Exception as error:
        if error_handler:
            error_handler("sembol_arama_yahoo", error)

    if len(sonuc) < 8 and finnhub_search is not None:
        try:
            for item in (finnhub_search(query) or {}).get("result", []) or []:
                quote_type = str(item.get("type") or "").upper()
                if quote_type and quote_type not in {
                    "COMMON STOCK",
                    "ADR",
                    "ETP",
                    "REIT",
                    "PREFERRED STOCK",
                    "UNIT",
                    "CLOSED-END FUND",
                }:
                    continue
                ekle(
                    item.get("symbol"),
                    item.get("description"),
                    item.get("displaySymbol"),
                    quote_type,
                )
        except Exception as error:
            if error_handler:
                error_handler("sembol_arama_finnhub", error)

    for symbol in sorted(set(_ticker_listesi(local_universe))):
        if query_upper in symbol:
            ekle(
                symbol,
                "IZFIN evreni",
                "BIST" if symbol.endswith(".IS") else "US",
                "EQUITY",
            )

    if query.replace(".", "").replace("-", "").isalnum() and len(query) <= 15:
        if query_upper not in seen:
            ekle(query_upper, "Sembol olarak ekle", "", "SYMBOL")

    return sonuc[: max(0, int(limit))]
