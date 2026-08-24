"""Pydantic contracts shared by IZFIN HTTP endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    api_version: str


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
