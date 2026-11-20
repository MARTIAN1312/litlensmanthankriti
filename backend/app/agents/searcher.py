"""Searcher (SRS FR-11, DESIGN §3.2): queries -> up to 25 unique arXiv candidates."""

from __future__ import annotations

from app.models.internal import Candidate
from app.pipeline.context import RunContext
from app.services.arxiv_client import ArxivUnavailableError

MAX_CANDIDATES = 25
PER_QUERY = 10


async def search(queries: list[str], ctx: RunContext) -> list[Candidate]:
    await ctx.emit("searching", "started", "Searching arXiv")
    found: dict[str, Candidate] = {}
    failures = 0
    total = len(queries)
    for i, q in enumerate(queries, start=1):
        try:
            results = await ctx.arxiv.search(q, max_results=PER_QUERY)
        except ArxivUnavailableError:
            failures += 1
            results = []
        for c in results:
            found.setdefault(c.arxiv_id, c)  # de-duplicate by ID without version
        if i < total:
            await ctx.emit(
                "searching",
                "progress",
                f"Query {i}/{total}: {len(results)} results",
                progress=(i, total),
            )

    if failures == total:
        await ctx.emit("searching", "failed", "arXiv could not be reached")
        raise ArxivUnavailableError("All arXiv searches failed")
    if failures:
        ctx.warn(f"{failures} of {total} arXiv searches failed.")

    candidates = list(found.values())[:MAX_CANDIDATES]
    if len(candidates) < 4:
        ctx.warn("Few papers found; try a broader topic.")
    await ctx.emit(
        "searching",
        "completed",
        f"{len(candidates)} unique candidate papers",
        progress=(total, total),
    )
    return candidates
