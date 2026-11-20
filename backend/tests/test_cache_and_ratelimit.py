from __future__ import annotations

from pathlib import Path

import pytest

from app.llm.ratelimit import SAFETY, RateLimiter, estimate_tokens
from app.services.cache import Cache, make_key

# ---------------- cache ----------------


def test_make_key_is_stable_and_order_independent() -> None:
    assert make_key("a", {"x": 1, "y": 2}) == make_key("a", {"y": 2, "x": 1})
    assert make_key("a", 1) != make_key("a", 2)
    assert len(make_key("x")) == 64


def test_cache_roundtrip_and_persistence(tmp_path: Path) -> None:
    path = tmp_path / "c.sqlite"
    c = Cache(path)
    c.set_http("k", [{"a": 1}])
    c.set_llm("l", "text", 10, 5)
    c.close()

    c2 = Cache(path)
    assert c2.get_http("k") == [{"a": 1}]
    hit = c2.get_llm("l")
    assert hit is not None and (hit.text, hit.tokens_in, hit.tokens_out) == (
        "text",
        10,
        5,
    )
    assert c2.get_http("missing") is None
    assert c2.get_llm("missing") is None


# ---------------- rate limiter ----------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.now += s


def test_estimate_tokens() -> None:
    assert estimate_tokens(400, 100) == 200


async def test_allows_calls_under_the_limit() -> None:
    clk = FakeClock()
    rl = RateLimiter(8000, 30, clock=clk, sleep=clk.sleep)
    for _ in range(3):
        await rl.acquire("m", 2000)
    assert clk.slept == []


async def test_waits_when_tpm_would_be_exceeded() -> None:
    clk = FakeClock()
    rl = RateLimiter(8000, 30, clock=clk, sleep=clk.sleep)
    await rl.acquire("m", 4000)
    clk.now += 10
    await rl.acquire("m", 3000)  # 7000 <= 7200 (90%)
    assert clk.slept == []
    await rl.acquire("m", 3000)  # would be 10000 -> wait for the first to expire
    assert clk.slept and sum(clk.slept) == pytest.approx(50.01, abs=0.05)


async def test_rpm_limit() -> None:
    clk = FakeClock()
    rl = RateLimiter(10**9, 10, clock=clk, sleep=clk.sleep)
    for _ in range(int(10 * SAFETY)):
        await rl.acquire("m", 1)
    assert clk.slept == []
    await rl.acquire("m", 1)
    assert clk.slept  # 10th call within a minute had to wait


async def test_models_have_separate_buckets() -> None:
    clk = FakeClock()
    rl = RateLimiter(8000, 30, clock=clk, sleep=clk.sleep)
    await rl.acquire("small", 7000)
    await rl.acquire("big", 7000)
    assert clk.slept == []


async def test_reconcile_frees_overestimate() -> None:
    clk = FakeClock()
    rl = RateLimiter(8000, 30, clock=clk, sleep=clk.sleep)
    r = await rl.acquire("m", 7000)
    rl.reconcile(r, 1000)
    assert rl.wait_time("m", 5000) == 0
