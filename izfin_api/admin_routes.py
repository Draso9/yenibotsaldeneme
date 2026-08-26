"""Admin-only operational quality endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.quality_service import qa_release_status, qa_static_metrics

from .dependencies import ApiIdentity, authenticated_user, bearer_credentials

admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _admin_emails() -> set[str]:
    raw = os.getenv("IZFIN_ADMIN_EMAILS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def admin_user(request: Request, credentials=Depends(bearer_credentials)) -> ApiIdentity:
    identity = authenticated_user(request, credentials)
    if identity.email not in _admin_emails():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli.")
    return identity


def _read_first(paths: tuple[Path, ...]) -> str:
    for path in paths:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


@admin_router.get("/quality")
def admin_quality(request: Request, _identity: ApiIdentity = Depends(admin_user)) -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    app_source = _read_first((root / "app2.py", root / "app.py"))
    css_source = _read_first((root / "styles" / "izfin.css", root / "izfin_styles.css", root / "style.css", root / "styles.css"))
    metrics = qa_static_metrics(app_source, css_source)
    return {"app_release": request.app.state.izfin_runtime.app_release, "metrics": metrics, "status": qa_release_status(metrics)}
