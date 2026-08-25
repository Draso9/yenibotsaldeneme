"""Production HTTP boundary shared by future web and mobile clients."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


LOGGER = logging.getLogger("izfin.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def request_id_from(request: Request) -> str:
    candidate = str(request.headers.get("X-Request-ID", "")).strip()
    return candidate if _REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex


def error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "authentication_required",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        503: "service_unavailable",
    }.get(int(status_code), "http_error")


def error_payload(request: Request, status_code: int, detail) -> dict:
    message = str(detail)
    return {
        "detail": detail,
        "error": {
            "code": error_code(status_code),
            "message": message,
            "request_id": getattr(request.state, "request_id", uuid4().hex),
        },
    }


async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    headers = dict(error.headers or {})
    headers["X-Request-ID"] = getattr(request.state, "request_id", uuid4().hex)
    return JSONResponse(
        status_code=error.status_code,
        content=error_payload(request, error.status_code, error.detail),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    payload = error_payload(request, 422, "İstek doğrulanamadı.")
    payload["details"] = error.errors()
    return JSONResponse(
        status_code=422,
        content=payload,
        headers={"X-Request-ID": payload["error"]["request_id"]},
    )


async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", uuid4().hex)
    LOGGER.exception("api_unhandled_error request_id=%s", request_id, exc_info=error)
    payload = {
        "detail": "Beklenmeyen bir sunucu hatası oluştu.",
        "error": {
            "code": "internal_server_error",
            "message": "Beklenmeyen bir sunucu hatası oluştu.",
            "request_id": request_id,
        },
    }
    return JSONResponse(
        status_code=500,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


class SlidingWindowRateLimiter:
    def __init__(self, *, requests: int, window_seconds: int) -> None:
        self.requests = max(0, int(requests))
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allows(self, key: str, *, now: float | None = None) -> bool:
        if self.requests == 0:
            return True
        moment = time.monotonic() if now is None else float(now)
        cutoff = moment - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.requests:
                return False
            events.append(moment)
            return True


class ApiHttpBoundaryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, rate_limit_requests: int, rate_limit_window_seconds: int):
        super().__init__(app)
        self.rate_limiter = SlidingWindowRateLimiter(
            requests=rate_limit_requests,
            window_seconds=rate_limit_window_seconds,
        )

    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request_id_from(request)
        started = time.perf_counter()
        path = request.url.path
        client_host = request.client.host if request.client is not None else "unknown"

        if path.startswith("/api/") and not path.startswith("/api/v1/health"):
            if not self.rate_limiter.allows(client_host):
                payload = error_payload(request, 429, "İstek sınırı aşıldı.")
                response = JSONResponse(
                    status_code=429,
                    content=payload,
                    headers={"Retry-After": str(self.rate_limiter.window_seconds)},
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        response.headers["X-Request-ID"] = request.state.request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        LOGGER.info(
            "api_request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            path,
            response.status_code,
            duration_ms,
            request.state.request_id,
        )
        return response
