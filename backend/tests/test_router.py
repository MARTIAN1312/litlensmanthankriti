from __future__ import annotations

from pathlib import Path

import pytest

from app.llm.base import (
    Message,
    PermanentError,
    RateLimitedError,
    TransientError,
    strict_json_schema,
)
from app.llm.router import NoProviderError
from app.models.internal import ExtractorOutput
from app.services.cache import Cache
from tests.fakes import FakeProvider, make_router

MSGS = [Message("system", "s"), Message("user", "u")]


async def _call(router, task="plan"):  # noqa: ANN001, ANN202
    return await router.complete(task, MSGS, prompt_version="v1", max_tokens=100)


async def test_primary_success_and_task_models(tmp_path: Path) -> None:
    groq = FakeProvider("groq", ["ok", "ok2"])
    router = make_router(tmp_path, groq=groq)
    r = await _call(router, "plan")
    assert (r.text, r.provider, r.model) == ("ok", "groq", "openai/gpt-oss-20b")
    r2 = await _call(router, "synthesize")
    assert r2.model == "openai/gpt-oss-120b"


async def test_second_identical_call_hits_cache(tmp_path: Path) -> None:
    groq = FakeProvider("groq", ["ok"])
    router = make_router(tmp_path, groq=groq)
    await _call(router)
    r = await _call(router)
    assert (r.text, r.provider, r.tokens) == ("ok", "cache", 0)
    assert len(groq.calls) == 1


async def test_prompt_version_changes_cache_key(tmp_path: Path) -> None:
    groq = FakeProvider("groq", ["a", "b"])
    router = make_router(tmp_path, groq=groq)
    await router.complete("plan", MSGS, prompt_version="v1", max_tokens=10)
    r = await router.complete("plan", MSGS, prompt_version="v2", max_tokens=10)
    assert r.text == "b"


async def test_short_429_waits_and_retries(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [RateLimitedError("429", retry_after=2), "ok"])
    gemini = FakeProvider("gemini", [])
    r = await _call(make_router(tmp_path, groq=groq, gemini=gemini))
    assert r.provider == "groq" and len(groq.calls) == 2


async def test_long_429_falls_back_to_gemini(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [RateLimitedError("429", retry_after=60)])
    gemini = FakeProvider("gemini", ["from gemini"])
    r = await _call(make_router(tmp_path, groq=groq, gemini=gemini))
    assert (r.provider, r.model, r.text) == ("gemini", "gemini-test", "from gemini")


async def test_transient_retried_once_then_fallback(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [TransientError("5xx"), TransientError("5xx")])
    gemini = FakeProvider("gemini", ["g"])
    r = await _call(make_router(tmp_path, groq=groq, gemini=gemini))
    assert r.provider == "gemini" and len(groq.calls) == 2


async def test_permanent_error_skips_retry(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [PermanentError("400")])
    gemini = FakeProvider("gemini", ["g"])
    r = await _call(make_router(tmp_path, groq=groq, gemini=gemini))
    assert r.provider == "gemini" and len(groq.calls) == 1


async def test_all_fail_raises(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [PermanentError("400")])
    with pytest.raises(PermanentError):
        await _call(make_router(tmp_path, groq=groq))


async def test_no_provider(tmp_path: Path) -> None:
    with pytest.raises(NoProviderError):
        await _call(make_router(tmp_path))


async def test_offline_uses_cache_only(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "c.sqlite")
    online = make_router(tmp_path, groq=FakeProvider("groq", ["cached"]), cache=cache)
    await _call(online)
    groq = FakeProvider("groq", [])
    offline = make_router(tmp_path, groq=groq, offline=True, cache=cache)
    assert (await _call(offline)).text == "cached"
    with pytest.raises(NoProviderError):
        await offline.complete("plan", MSGS, prompt_version="other", max_tokens=1)
    assert groq.calls == []


async def test_fallback_only(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [])
    gemini = FakeProvider("gemini", ["g"])
    router = make_router(tmp_path, groq=groq, gemini=gemini)
    r = await router.complete(
        "extract", MSGS, prompt_version="v", max_tokens=10, fallback_only=True
    )
    assert r.provider == "gemini" and groq.calls == []


def test_strict_schema_requires_all_fields_and_inlines_defs() -> None:
    s = strict_json_schema(ExtractorOutput)
    assert "$defs" not in str(s) and "$ref" not in str(s)
    item = s["properties"]["extractions"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])
    metric = item["properties"]["metrics"]["items"]
    assert metric["additionalProperties"] is False
    assert set(metric["required"]) == {"name", "value"}
