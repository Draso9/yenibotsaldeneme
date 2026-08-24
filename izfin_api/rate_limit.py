"""Small bounded fixed-window limiter for a single API process."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from time import time


class FixedWindowRateLimiter:
    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time,
    ) -> None:
        if max_requests < 1 or window_seconds < 1:
            raise ValueError("Rate limit values must be positive.")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._lock = RLock()
        self._buckets: dict[str, tuple[int, int]] = {}

    def allow(self, key: str) -> tuple[bool, int]:
        now = int(self._clock())
        window_start = now - (now % self._window_seconds)
        with self._lock:
            count, previous_window = self._buckets.get(str(key), (0, window_start))
            if previous_window != window_start:
                count = 0
            if count >= self._max_requests:
                return False, self._window_seconds - (now - window_start)
            self._buckets[str(key)] = (count + 1, window_start)
            return True, 0
