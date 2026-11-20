"""Client-side rate limiter: per-model tokens-per-minute and requests-per-minute
(DESIGN §5, SRS NFR-3, SECURITY Q-1).

Sliding 60-second window. Before a call we reserve an *estimate*; afterwards
we replace it with the real usage reported by the provider.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

WINDOW_S = 60.0
SAFETY = 0.9  # use at most 90% of the published limits


def estimate_tokens(prompt_chars: int, max_tokens: int) -> int:
    """≈ 4 characters per token, plus the full output budget."""
    return prompt_chars // 4 + max_tokens


@dataclass
class _Entry:
    at: float
    tokens: int


@dataclass
class Reservation:
    model: str
    entry: _Entry


@dataclass
class _Bucket:
    entries: deque[_Entry] = field(default_factory=deque)


class RateLimiter:
    def __init__(
        self,
        tpm: int,
        rpm: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.tpm = int(tpm * SAFETY)
        self.rpm = max(1, int(rpm * SAFETY))
        self._clock = clock
        self._sleep = sleep
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    def _bucket(self, model: str) -> _Bucket:
        return self._buckets.setdefault(model, _Bucket())

    def _prune(self, b: _Bucket, now: float) -> None:
        while b.entries and now - b.entries[0].at >= WINDOW_S:
            b.entries.popleft()

    def _wait_needed(self, b: _Bucket, tokens: int, now: float) -> float:
        self._prune(b, now)
        if not b.entries:
            return 0.0  # always allow one call into an empty window, even if huge
        used = sum(e.tokens for e in b.entries)
        if len(b.entries) < self.rpm and used + tokens <= self.tpm:
            return 0.0
        # Wait until enough old entries slide out of the window.
        freed = 0
        need_tokens = used + tokens - self.tpm
        for i, e in enumerate(b.entries):
            freed += e.tokens
            enough_tokens = freed >= need_tokens
            enough_requests = len(b.entries) - (i + 1) < self.rpm
            if enough_tokens and enough_requests:
                return max(0.0, e.at + WINDOW_S - now) + 0.01
        return max(0.0, b.entries[-1].at + WINDOW_S - now) + 0.01

    def wait_time(self, model: str, tokens: int) -> float:
        """Seconds until a call of `tokens` could start (0 = now). For logs/tests."""
        return self._wait_needed(self._bucket(model), tokens, self._clock())

    async def acquire(self, model: str, tokens: int) -> Reservation:
        async with self._lock:  # serialise so two callers can't overbook
            b = self._bucket(model)
            while True:
                wait = self._wait_needed(b, tokens, self._clock())
                if wait <= 0:
                    break
                await self._sleep(wait)
            entry = _Entry(at=self._clock(), tokens=tokens)
            b.entries.append(entry)
            return Reservation(model=model, entry=entry)

    def reconcile(self, reservation: Reservation, actual_tokens: int) -> None:
        """Replace the estimate with real usage once the provider reports it."""
        reservation.entry.tokens = max(0, actual_tokens)
