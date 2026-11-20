from __future__ import annotations

from pathlib import Path

import arxiv
import pytest

from app.agents.ranker import rank
from app.agents.searcher import search
from app.llm.router import LLMRouter
from app.services.arxiv_client import (
    ArxivClient,
    ArxivUnavailableError,
    build_query,
    query_terms,
    strip_version,
)
from app.services.cache import Cache
from tests.fakes import FakeArxiv, StubEmbedder, candidate, make_ctx, make_router

# ---------------- query building ----------------


def test_query_terms_drop_stopwords_and_operators() -> None:
    assert query_terms("Crop disease detection using deep learning") == [
        "crop",
        "disease",
        "detection",
        "deep",
        "learning",
    ]
    # quotes, parens, field prefixes and boolean syntax can't get through
    terms = query_terms('ti:"evil" OR (cat:cs.AI) AND all:x')
    assert all(t.replace("-", "").isalnum() for t in terms)
    assert ":" not in build_query(terms).replace("all:", "")


def test_build_query() -> None:
    assert build_query(["a", "b"]) == "all:a AND all:b"


def test_strip_version() -> None:
    assert strip_version("2401.01234v3") == "2401.01234"
    assert strip_version("hep-th/9901001v1") == "hep-th/9901001"


# ---------------- client (network stubbed) ----------------


def _client(tmp_path: Path, offline: bool = False) -> ArxivClient:
    return ArxivClient(Cache(tmp_path / "c.sqlite"), contact="me@x", offline=offline)


async def test_client_caches_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    calls: list[str] = []

    def fake(q: str, n: int):  # noqa: ANN202
        calls.append(q)
        return [candidate(f"2401.0000{i}", f"p{i}") for i in range(5)]

    monkeypatch.setattr(client, "_search_sync", fake)
    a = await client.search("graph neural networks")
    b = await client.search("graph neural networks")
    assert len(a) == 5 and a == b and len(calls) == 1


async def test_client_drops_terms_when_few_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    seen: list[str] = []

    def fake(q: str, n: int):  # noqa: ANN202
        seen.append(q)
        return (
            []
            if q.count("AND") >= 2
            else [candidate(f"2401.0000{i}", "p") for i in range(4)]
        )

    monkeypatch.setattr(client, "_search_sync", fake)
    res = await client.search("alpha beta gamma delta")
    assert len(res) == 4
    assert seen[0] == "all:alpha AND all:beta AND all:gamma AND all:delta"
    assert seen[-1] == "all:alpha AND all:beta"


async def test_offline_cache_miss_raises(tmp_path: Path) -> None:
    with pytest.raises(ArxivUnavailableError):
        await _client(tmp_path, offline=True).search("anything here")


async def test_network_error_becomes_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)

    def boom(q: str, n: int):  # noqa: ANN202
        raise ConnectionError("down")

    monkeypatch.setattr(client, "_search_sync", boom)
    with pytest.raises(ArxivUnavailableError):
        await client.search("some topic words")


def test_user_agent_is_descriptive(tmp_path: Path) -> None:
    _client(tmp_path)
    assert arxiv._USER_AGENT.startswith("LitLens/1.0 (student project; me@x")


# ---------------- searcher ----------------


async def test_searcher_dedupes_and_caps(tmp_path: Path) -> None:
    shared = candidate("2401.00001", "shared")
    fa = FakeArxiv(
        {
            "q1": [shared] + [candidate(f"2402.{i:05d}", f"a{i}") for i in range(15)],
            "q2": [shared] + [candidate(f"2403.{i:05d}", f"b{i}") for i in range(15)],
            "q3": [shared] + [candidate(f"2404.{i:05d}", f"c{i}") for i in range(15)],
        }
    )
    router: LLMRouter = make_router(tmp_path)
    ctx, events = make_ctx(tmp_path, router, fa)
    res = await search(["q1", "q2", "q3"], ctx)  # 10 + 9 + 9 unique -> capped at 25
    assert len(res) == 25
    assert len({c.arxiv_id for c in res}) == 25
    assert events[-1].stage == "searching" and events[-1].status == "completed"


async def test_searcher_all_fail_raises(tmp_path: Path) -> None:
    fa = FakeArxiv()
    fa.fail = True
    ctx, events = make_ctx(tmp_path, make_router(tmp_path), fa)
    with pytest.raises(ArxivUnavailableError):
        await search(["q"], ctx)
    assert events[-1].status == "failed"


async def test_searcher_partial_failure_warns(tmp_path: Path) -> None:
    class Flaky(FakeArxiv):
        async def search(self, query: str, max_results: int = 10):  # noqa: ANN201
            if query == "bad":
                raise ArxivUnavailableError("x")
            return [candidate(f"2401.0000{i}", "p") for i in range(5)]

    ctx, _ = make_ctx(tmp_path, make_router(tmp_path), Flaky())
    res = await search(["good", "bad"], ctx)
    assert len(res) == 5
    assert any("failed" in w for w in ctx.warnings)


# ---------------- ranker ----------------


async def test_ranker_orders_by_similarity_and_builds_links() -> None:
    cands = [
        candidate("2401.00001", "cooking pasta recipes"),
        candidate("2401.00002", "crop disease detection with deep learning"),
        candidate("2401.00003", "crop yield prediction"),
    ]
    papers = await rank("crop disease detection", cands, StubEmbedder(), top_n=2)
    assert [p.arxiv_id for p in papers] == ["2401.00002", "2401.00003"]
    assert [p.ref for p in papers] == [1, 2]
    assert papers[0].url_abs == "https://arxiv.org/abs/2401.00002"
    assert papers[0].url_pdf == "https://arxiv.org/pdf/2401.00002"
    assert papers[0].relevance >= papers[1].relevance


async def test_ranker_year_filter_and_empty() -> None:
    cands = [
        candidate("2401.00001", "old crop", year=2015),
        candidate("2401.00002", "new crop"),
    ]
    papers = await rank("crop", cands, StubEmbedder(), top_n=5, year_from=2020)
    assert [p.arxiv_id for p in papers] == ["2401.00002"]
    assert await rank("crop", [], StubEmbedder(), top_n=5) == []
