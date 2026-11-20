"""Per-client request limit for expensive endpoints (SECURITY N-4)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.api.errors import AppError

WINDOW_S = 60.0


class ClientLimiter:
    def __init__(self, per_minute: int = 10) -> None:
        self.per_minute = per_minute
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, request: Request, bucket: str) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[(ip, bucket)]
        while hits and now - hits[0] >= WINDOW_S:
            hits.popleft()
        if len(hits) >= self.per_minute:
            raise AppError(
                429, "RATE_LIMITED", "Too many requests. Please wait a minute."
            )
        hits.append(now)


def client_limiter(request: Request) -> ClientLimiter:
    return request.app.state.client_limiter
