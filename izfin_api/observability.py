"""Privacy-safe request observability helpers for the HTTP API."""

from __future__ import annotations

import json
import logging
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Match

from .rate_limit import FixedWindowRateLimiter


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def request_id_for(value: str | None) -> str:
    candidate = str(value or "").strip()
    return candidate if _REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex


def log_request_event(logger: logging.Logger, **fields: Any) -> None:
    event = {
        "event": "api_request",
        "request_id": str(fields["request_id"]),
        "method": str(fields["method"]),
        "route": str(fields["route"]),
        "status_code": int(fields["status_code"]),
        "elapsed_ms": int(fields["elapsed_ms"]),
    }
    logger.info(json.dumps(event, ensure_ascii=False, separators=(",", ":")))


class ApiHardeningMiddleware(BaseHTTPMiddleware):
    _EXEMPT_PATHS = {"/api/v1/health", "/api/v1/health/ready", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, *, limiter: FixedWindowRateLimiter | None, enabled: bool) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._enabled = enabled
        self._logger = logging.getLogger("izfin_api")

    async def dispatch(self, request: Request, call_next):
        request_id = request_id_for(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        if self._enabled and self._limiter and request.url.path not in self._EXEMPT_PATHS:
            bucket_key = self._bucket_key(request)
            allowed, retry_after = self._limiter.allow(bucket_key)
            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "İstek sınırına ulaşıldı. Lütfen kısa süre sonra tekrar deneyin."},
                    headers={"Retry-After": str(retry_after)},
                )
                response.headers["X-Request-ID"] = request_id
                log_request_event(
                    self._logger,
                    request_id=request_id,
                    method=request.method,
                    route=self._route_template(request),
                    status_code=429,
                    elapsed_ms=0,
                )
                return response
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        log_request_event(
            self._logger,
            request_id=request_id,
            method=request.method,
            route=self._route_template(request),
            status_code=response.status_code,
            elapsed_ms=int((perf_counter() - started) * 1000),
        )
        return response

    @staticmethod
    def _route_template(request: Request) -> str:
        route = request.scope.get("route")
        path = getattr(route, "path", None)
        if path:
            return str(path)
        for candidate in request.app.routes:
            match, _ = candidate.matches(request.scope)
            if match is Match.FULL:
                return str(getattr(candidate, "path", "/unmatched"))
        return "/unmatched"

    @staticmethod
    def _bucket_key(request: Request) -> str:
        credentials = request.headers.get("Authorization", "")
        runtime = request.app.state.izfin_runtime
        if credentials.startswith("Bearer ") and runtime.verify_id_token is not None:
            try:
                claims = runtime.verify_id_token(credentials.removeprefix("Bearer ").strip()) or {}
                uid = str(claims.get("uid") or claims.get("user_id") or "").strip()
                if uid:
                    return f"uid:{uid}"
            except Exception:
                pass
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"
