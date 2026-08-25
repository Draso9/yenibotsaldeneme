"""Authenticated account lifecycle routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.account_data_service import hesap_silme_onayi_dogrula

from .dependencies import ApiIdentity, authenticated_user, bearer_credentials
from .schemas import AccountDeleteRequest, AccountDeleteResponse


account_router = APIRouter(prefix="/api/v1")


@account_router.delete("/account", response_model=AccountDeleteResponse, tags=["account"])
def delete_account(
    payload: AccountDeleteRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> AccountDeleteResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    if not runtime.account_delete_enabled or runtime.account_data_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kalıcı hesap silme production kimlik sağlayıcısında henüz etkin değil.",
        )

    confirmed, error = hesap_silme_onayi_dogrula(
        hesap_email=identity.email,
        girilen_email=payload.email,
        girilen_ifade=payload.confirmation_phrase,
        geri_alinamaz=payload.irreversible,
    )
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error,
        )

    try:
        deleted_documents = runtime.account_data_service.hesabi_kalici_sil(
            uid=identity.uid,
            email=identity.email,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hesap silme işlemi şu anda tamamlanamadı.",
        ) from exc

    return AccountDeleteResponse(deleted=True, deleted_documents=int(deleted_documents))
