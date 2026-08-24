"""Versioned FastAPI routers backed by framework-neutral IZFIN modules."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.bootstrap_service import (
    kullanici_watchlist_bootstrap_hazirla,
    kullanici_watchlist_kaydet,
)
from izfin_services.scan_page_state import tarama_sonuc_durumu_hazirla
from izfin_services.scan_page_state import (
    tarama_evreni_hazirla,
    watchlist_islem_durumu_hazirla,
)
from izfin_ui.performance_view import performans_karne_paketi_hazirla
from izfin_ui.legal_account_view import (
    gizlilik_sayfa_paketi_hazirla,
    kullanim_kosullari_paketi_hazirla,
)

from .schemas import (
    HealthResponse,
    ReadinessResponse,
    PerformanceScorecardRequest,
    PerformanceScorecardResponse,
    ScanUniverseRequest,
    ScanUniverseResponse,
    WatchlistTransitionRequest,
    WatchlistTransitionResponse,
    WatchlistResponse,
    WatchlistReplaceRequest,
    ScanRunRequest,
    ScanRunResponse,
    ScanJobCreatedResponse,
    ScanJobStatusResponse,
    PerformanceScorecardApiResponse,
    LegalDocumentResponse,
    ProfileResponse,
    LegalConsentResponse,
    LegalConsentUpdateRequest,
    AccountExportResponse,
)
from .dependencies import ApiIdentity, authenticated_user, bearer_credentials
from .scan_jobs import ScanJobCapacityError


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="izfin-api", api_version="v1")


@api_router.get("/legal/terms", response_model=LegalDocumentResponse, tags=["legal"])
def legal_terms(request: Request) -> LegalDocumentResponse:
    runtime = request.app.state.izfin_runtime
    document = kullanim_kosullari_paketi_hazirla(
        kapida=False,
        terms_version=runtime.terms_version,
    )
    return LegalDocumentResponse(
        version=runtime.terms_version,
        markdown=document["markdown"],
    )


@api_router.get("/legal/privacy", response_model=LegalDocumentResponse, tags=["legal"])
def legal_privacy(request: Request) -> LegalDocumentResponse:
    runtime = request.app.state.izfin_runtime
    document = gizlilik_sayfa_paketi_hazirla(
        kapida=False,
        privacy_version=runtime.privacy_version,
        data_controller_name=runtime.data_controller_name,
        contact_email=runtime.contact_email,
        data_controller_address=runtime.data_controller_address,
        log_retention_days=runtime.log_retention_days,
    )
    return LegalDocumentResponse(
        version=runtime.privacy_version,
        markdown=document["markdown"],
        warning=document["warning"],
        info=document["info"],
    )


@api_router.get("/profile", response_model=ProfileResponse, tags=["account"])
def get_profile(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> ProfileResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    repository = request.app.state.izfin_runtime.user_repository
    if not getattr(repository, "available", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kullanıcı profili deposu henüz yapılandırılmadı.",
        )
    return ProfileResponse(
        uid=identity.uid,
        email=identity.email,
        profile=repository.get_profile(identity.uid) or {},
    )


def _legal_consent_response(runtime, identity: ApiIdentity) -> LegalConsentResponse:
    service = runtime.legal_consent_service
    if service is None or not service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Yasal onay deposu henüz yapılandırılmadı.",
        )
    accepted, error = service.onay_guncel_mi(identity.uid)
    if error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error)
    return LegalConsentResponse(
        terms_version=runtime.terms_version,
        privacy_version=runtime.privacy_version,
        accepted=accepted,
    )


@api_router.get("/legal/consent", response_model=LegalConsentResponse, tags=["legal"])
def get_legal_consent(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> LegalConsentResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    return _legal_consent_response(request.app.state.izfin_runtime, identity)


@api_router.put("/legal/consent", response_model=LegalConsentResponse, tags=["legal"])
def update_legal_consent(
    payload: LegalConsentUpdateRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> LegalConsentResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    service = runtime.legal_consent_service
    if service is None or not service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Yasal onay deposu henüz yapılandırılmadı.",
        )
    saved, error = service.onay_kaydet(identity.uid)
    if not saved:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error)
    return _legal_consent_response(runtime, identity)


@api_router.get("/account/export", response_model=AccountExportResponse, tags=["account"])
def account_export(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> AccountExportResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    service = request.app.state.izfin_runtime.account_data_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kullanıcı verileri şu anda hazırlanamadı.",
        )
    try:
        package = service.veri_paketi_olustur(uid=identity.uid, email=identity.email)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kullanıcı verileri şu anda hazırlanamadı.",
        ) from error
    return AccountExportResponse(**package)


@api_router.get("/health/ready", response_model=ReadinessResponse, tags=["system"])
def readiness(request: Request) -> ReadinessResponse:
    runtime = request.app.state.izfin_runtime
    authentication = runtime.verify_id_token is not None
    user_repository = bool(getattr(runtime.user_repository, "available", False))
    signal_repository = bool(getattr(runtime.signal_repository, "available", False))
    scan_runner = runtime.scan_runner is not None
    return ReadinessResponse(
        ready=authentication and user_repository and signal_repository and scan_runner,
        authentication=authentication,
        user_repository=user_repository,
        signal_repository=signal_repository,
        scan_runner=scan_runner,
    )


@api_router.post("/scan/universe", response_model=ScanUniverseResponse, tags=["scan"])
def scan_universe(payload: ScanUniverseRequest) -> ScanUniverseResponse:
    return ScanUniverseResponse(
        **tarama_evreni_hazirla(
            payload.profil,
            payload.kisisel_liste,
            payload.preset_options,
        )
    )


@api_router.post(
    "/watchlist/transition",
    response_model=WatchlistTransitionResponse,
    tags=["watchlist"],
)
def watchlist_transition(payload: WatchlistTransitionRequest) -> WatchlistTransitionResponse:
    return WatchlistTransitionResponse(**watchlist_islem_durumu_hazirla(payload.islem_sonucu))


@api_router.get("/watchlist", response_model=WatchlistResponse, tags=["watchlist"])
def get_watchlist(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> WatchlistResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    if not getattr(runtime.user_repository, "available", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kullanıcı listesi deposu henüz yapılandırılmadı.",
        )
    result = kullanici_watchlist_bootstrap_hazirla(
        runtime.user_repository,
        uid=identity.uid,
        email=identity.email,
        default_tickers=runtime.default_tickers,
    )
    return WatchlistResponse(tickers=result["tickers"], recovered=result["recovered"])


@api_router.put("/watchlist", response_model=WatchlistResponse, tags=["watchlist"])
def replace_watchlist(
    payload: WatchlistReplaceRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> WatchlistResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    if not getattr(runtime.user_repository, "available", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kullanıcı listesi deposu henüz yapılandırılmadı.",
        )
    kullanici_watchlist_kaydet(
        runtime.user_repository,
        uid=identity.uid,
        email=identity.email,
        tickers=payload.tickers,
    )
    return WatchlistResponse(
        tickers=list(dict.fromkeys(str(item).strip().upper() for item in payload.tickers if str(item).strip())),
        recovered=False,
    )


@api_router.post("/scan/run", response_model=ScanRunResponse, tags=["scan"])
def run_scan(
    payload: ScanRunRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> ScanRunResponse:
    authenticated_user(request, credentials)
    runner = request.app.state.izfin_runtime.scan_runner
    if runner is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tarama sağlayıcıları henüz yapılandırılmadı.",
        )
    result = tarama_sonuc_durumu_hazirla(runner(payload.tickers))
    return ScanRunResponse(
        sonuclar=result["sonuclar"],
        basarisiz_taramalar=result["basarisiz_taramalar"],
        boga_sayisi=result["boga_sayisi"],
        alim_firsati=result["alim_firsati"],
        toplam=len(payload.tickers),
    )


@api_router.post(
    "/scan/jobs",
    response_model=ScanJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Bearer token gerekli veya geçersiz."},
        429: {"description": "İstek veya tarama kuyruğu sınırına ulaşıldı."},
        503: {"description": "Tarama sağlayıcısı kullanılamıyor."},
    },
    tags=["scan"],
)
def create_scan_job(
    payload: ScanRunRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> ScanJobCreatedResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    if runtime.scan_runner is None or runtime.scan_job_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tarama sağlayıcıları henüz yapılandırılmadı.",
        )
    try:
        snapshot = runtime.scan_job_store.submit(identity.uid, payload.tickers, runtime.scan_runner)
    except ScanJobCapacityError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
        ) from error
    return ScanJobCreatedResponse(
        job_id=snapshot.job_id,
        status=snapshot.status,
        stage=snapshot.stage,
        completed=snapshot.completed,
        total=snapshot.total,
    )


@api_router.get(
    "/scan/jobs/{job_id}",
    response_model=ScanJobStatusResponse,
    tags=["scan"],
)
def get_scan_job(
    job_id: str,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> ScanJobStatusResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    store = request.app.state.izfin_runtime.scan_job_store
    snapshot = store.get_for_owner(job_id, identity.uid) if store is not None else None
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarama işi bulunamadı.")
    return ScanJobStatusResponse(
        job_id=snapshot.job_id,
        status=snapshot.status,
        stage=snapshot.stage,
        completed=snapshot.completed,
        total=snapshot.total,
        result=snapshot.result,
        error=snapshot.error,
    )


@api_router.get(
    "/performance/scorecard",
    response_model=PerformanceScorecardApiResponse,
    tags=["performance"],
)
def get_performance_scorecard(
    request: Request,
    gun: int = 20,
    credentials=Depends(bearer_credentials),
) -> PerformanceScorecardApiResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    repository = request.app.state.izfin_runtime.signal_repository
    if not getattr(repository, "available", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Performans kaydı deposu henüz yapılandırılmadı.",
        )
    paket = performans_karne_paketi_hazirla(
        repository.list_performance_records(identity.email, limit=250),
        gun=max(1, min(int(gun), 365)),
    )
    return PerformanceScorecardApiResponse(
        metrikler=paket["metrikler"],
        kucuk_orneklem=paket["kucuk_orneklem"],
        bos_mesaj=paket["bos_mesaj"],
        kayit_adedi=len(paket["karne_df"]),
    )


@api_router.post(
    "/performance/scorecard",
    response_model=PerformanceScorecardResponse,
    tags=["performance"],
)
def performance_scorecard(
    payload: PerformanceScorecardRequest,
) -> PerformanceScorecardResponse:
    paket = performans_karne_paketi_hazirla(payload.kayitlar, gun=payload.gun)
    return PerformanceScorecardResponse(
        metrikler=paket["metrikler"],
        kucuk_orneklem=paket["kucuk_orneklem"],
        bos_mesaj=paket["bos_mesaj"],
        kayit_adedi=len(paket["karne_df"]),
    )
