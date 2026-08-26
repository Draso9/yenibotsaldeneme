"""Pydantic contracts shared by IZFIN HTTP endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    api_version: str


class ReadinessResponse(BaseModel):
    ready: bool
    authentication: bool
    user_repository: bool
    signal_repository: bool
    scan_runner: bool


class ScanUniverseRequest(BaseModel):
    profil: str = "Kendi Listem"
    kisisel_liste: list[Any] = Field(default_factory=list)
    preset_options: dict[str, list[Any]] = Field(default_factory=dict)


class ScanUniverseResponse(BaseModel):
    profil: str
    tickers: list[str]
    chipleri_goster: bool
    secim_ozeti: dict[str, int]


class ScanProfilesResponse(BaseModel):
    """Server-owned scan profiles shared by Streamlit, web, and future mobile clients."""

    profiles: dict[str, list[str]] = Field(default_factory=dict)


class SymbolSuggestion(BaseModel):
    """One normalized symbol match from the existing search service."""

    symbol: str
    name: str = ""
    exchange: str = ""
    quote_type: str = ""


class SymbolSearchResponse(BaseModel):
    query: str
    suggestions: list[SymbolSuggestion] = Field(default_factory=list)


class WatchlistTransitionRequest(BaseModel):
    islem_sonucu: dict[str, Any] = Field(default_factory=dict)


class WatchlistTransitionResponse(BaseModel):
    custom_tickers: list[str]
    aktif_profil: str | None
    secilen_varliklar: list[str] | None
    clear_input: bool
    mesaj: tuple[str, str]


class WatchlistResponse(BaseModel):
    tickers: list[str]
    recovered: bool


class WatchlistReplaceRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=250)


class LegalDocumentResponse(BaseModel):
    version: str
    markdown: str
    warning: str | None = None
    info: str | None = None


class ProfileResponse(BaseModel):
    uid: str
    email: str
    profile: dict[str, Any]


class LegalConsentUpdateRequest(BaseModel):
    terms_accepted: Literal[True]
    privacy_notice_seen: Literal[True]


class LegalConsentResponse(BaseModel):
    terms_version: str
    privacy_version: str
    accepted: bool


class AccountExportResponse(BaseModel):
    export_schema: str
    exported_at: str
    app_release: str
    user_uid: str
    user_email: str
    collections: dict[str, list[dict[str, Any]]]


class AccountDeleteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    confirmation_phrase: str = Field(min_length=1, max_length=64)
    irreversible: bool


class AccountDeleteResponse(BaseModel):
    deleted: bool
    deleted_documents: int


class ScanRunRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=100)


class ScanRunResponse(BaseModel):
    sonuclar: list[dict[str, Any]]
    basarisiz_taramalar: list[str]
    boga_sayisi: int
    alim_firsati: int
    toplam: int


class ScanJobCreatedResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    completed: int
    total: int


class ScanJobStatusResponse(ScanJobCreatedResponse):
    result: dict[str, Any] | None = None
    error: str | None = None


class ScanJobHistoryItem(BaseModel):
    job_id: str
    status: str
    stage: str
    completed: int
    total: int
    tickers: list[str] = Field(default_factory=list)
    created_at: str | None = None


class ScanJobHistoryResponse(BaseModel):
    jobs: list[ScanJobHistoryItem] = Field(default_factory=list)


class MarketCenterRequest(BaseModel):
    sonuclar: list[dict[str, Any]] = Field(default_factory=list)
    teknik_paneller: dict[str, dict[str, Any]] = Field(default_factory=dict)
    piyasa_degisimleri: list[float] = Field(default_factory=list)
    max_signals: int = Field(default=7, ge=1, le=20)
    max_movers: int = Field(default=6, ge=1, le=20)


class MarketCenterResponse(BaseModel):
    empty: bool
    metrics: dict[str, Any]
    decision: dict[str, Any]
    best_ticker: str | None = None
    top_signals: list[dict[str, Any]]
    movers: list[dict[str, Any]]


class StockDetailRequest(BaseModel):
    sonuclar: list[dict[str, Any]] = Field(default_factory=list)
    teknik_paneller: dict[str, dict[str, Any]] = Field(default_factory=dict)


class StockDetailResponse(BaseModel):
    ticker: str
    price: Any = None
    signal: Any = None
    entry_quality: Any = None
    score: dict[str, Any]
    decision: dict[str, Any]
    action: dict[str, Any] = Field(default_factory=dict)
    panel: dict[str, Any]


class ProjectionBandResponse(BaseModel):
    kind: Literal["downside", "base", "upside"]
    label: str
    target: float
    extreme: float
    change_pct: float


class ProjectionResponse(BaseModel):
    ticker: str
    horizon_days: int
    model: dict[str, Any]
    scenario: dict[str, Any]
    metrics: dict[str, Any]
    bands: list[ProjectionBandResponse]


class BacktestRunRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    period: str = Field(default="5y", min_length=1, max_length=4)


class BacktestResponse(BaseModel):
    ticker: str
    period: str
    empty: bool
    stats: dict[str, Any]
    kpis: dict[str, Any]
    summary: list[dict[str, Any]]
    detail: list[dict[str, Any]]
    ambiguity_count: int
    ambiguity_message: str | None = None
    detail_explanation: str
    reading_notes: str


class PerformanceMetric(BaseModel):
    label: str
    value: str


class PerformancePositionsResponse(BaseModel):
    kpis: list[PerformanceMetric]
    active: list[dict[str, Any]]
    closed: list[dict[str, Any]]
    closed_summary: dict[str, Any]


class PerformanceScorecardQuery(BaseModel):
    gun: int = Field(default=20, ge=1, le=365)


class PerformanceScorecardApiResponse(BaseModel):
    metrikler: list[PerformanceMetric]
    kucuk_orneklem: bool
    bos_mesaj: str | None
    kayit_adedi: int


class PerformanceScorecardRequest(BaseModel):
    kayitlar: list[dict[str, Any]] = Field(default_factory=list)
    gun: int = Field(ge=1, le=365)


class PerformanceScorecardResponse(BaseModel):
    metrikler: list[PerformanceMetric]
    kucuk_orneklem: bool
    bos_mesaj: str | None
    kayit_adedi: int



