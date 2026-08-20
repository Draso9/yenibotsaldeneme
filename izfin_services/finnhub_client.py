"""Finnhub hız sınırı, retry ve quote dönüşümünü kapsülleyen istemci."""

from __future__ import annotations

import time
from threading import Lock

import requests


class FinnhubClient:
    def __init__(
        self,
        api_key,
        *,
        base_url="https://finnhub.io/api/v1",
        http_session=None,
        min_interval=0.10,
        error_handler=None,
        clock=None,
        sleeper=None,
    ):
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url).rstrip("/")
        self.http_session = http_session or requests.Session()
        self.min_interval = float(min_interval)
        self.error_handler = error_handler
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self._rate_lock = Lock()
        self._last_call = 0.0

    def get(self, endpoint, params, timeout=3, max_retry=2):
        if not self.api_key:
            return None
        for deneme in range(max_retry + 1):
            try:
                with self._rate_lock:
                    simdi = self.clock()
                    bekle = self.min_interval - (simdi - self._last_call)
                    if bekle > 0:
                        self.sleeper(bekle)
                    self._last_call = self.clock()

                response = self.http_session.get(
                    f"{self.base_url}/{endpoint}",
                    params={**params, "token": self.api_key},
                    timeout=timeout,
                )
                if response.status_code == 429:
                    try:
                        retry_after = float(response.headers.get("Retry-After", 0) or 0)
                    except Exception:
                        retry_after = 0.0
                    if deneme < max_retry:
                        self.sleeper(max(retry_after, 1.0 + deneme * 1.5))
                        continue
                    return None

                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
            except Exception as error:
                if deneme < max_retry:
                    self.sleeper(0.5 * (deneme + 1))
                    continue
                if self.error_handler:
                    self.error_handler("finnhub_get", error)
                return None
        return None

    def quote(self, symbol):
        data = self.get("quote", {"symbol": symbol})
        if not data or not data.get("c"):
            return None
        return {
            "open": float(data.get("o") or 0),
            "high": float(data.get("h") or 0),
            "low": float(data.get("l") or 0),
            "close": float(data.get("c") or 0),
            "previous_close": float(data.get("pc") or 0),
            "timestamp": int(data.get("t") or 0),
            "source": "Finnhub",
        }
