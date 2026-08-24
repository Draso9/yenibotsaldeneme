"""Pydantic contracts shared by IZFIN HTTP endpoints."""

from __future__ import annotations

from typing import Any

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


class ScanRunRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=100)


class ScanRunResponse(BaseModel):
    sonuclar: list[dict[str, Any]]
    basarisiz_taramalar: list[str]
    boga_sayisi: int
    alim_firsati: int
    toplam: int


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


class PerformanceMetric(BaseModel):
    label: str
    value: str


class PerformanceScorecardResponse(BaseModel):
    metrikler: list[PerformanceMetric]
    kucuk_orneklem: bool
    bos_mesaj: str | None
    kayit_adedi: int
