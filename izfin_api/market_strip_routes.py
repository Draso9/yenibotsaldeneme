"""Public market-strip reads backed by the framework-neutral market overview service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

market_strip_router = APIRouter(prefix="/api/v1", tags=["market"])


@market_strip_router.get("/market/strip")
def market_strip(request: Request) -> dict[str, Any]:
    loader = request.app.state.izfin_runtime.market_overview_loader
    if loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Piyasa bandı sağlayıcısı yapılandırılmadı.",
        )
    package = loader() or {}
    items = []
    for raw in package.get("items", []) if isinstance(package, Mapping) else []:
        if not isinstance(raw, Mapping):
            continue
        items.append(
            {
                "ad": str(raw.get("ad") or ""),
                "fiyat": raw.get("fiyat"),
                "deg": raw.get("deg"),
                "kaynak": str(raw.get("kaynak") or ""),
            }
        )
    return {
        "items": items,
        "durum": str(package.get("durum") or "VERİ KONTROL"),
        "gecikme_sn": package.get("gecikme_sn"),
        "yerel_saat": str(package.get("yerel_saat") or "—"),
    }
