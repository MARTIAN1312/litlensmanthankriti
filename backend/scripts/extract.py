"""M2 CLI: plan -> search -> rank -> extract for one topic, then print the table.

Run from backend/ with the venv active:
    python -m scripts.extract "crop disease detection using deep learning"
    python -m scripts.extract "graph neural networks" --papers 6 --year-from 2022

Uses real arXiv and Groq calls on a cache miss; a repeat run is free (cached).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from app.agents.extractor import extract
from app.agents.planner import plan
from app.agents.ranker import rank
from app.agents.searcher import search
from app.config import get_settings
from app.llm.router import build_router
from app.models.schemas import ReviewRequest, StageEvent
from app.pipeline.context import RunContext
from app.retrieval.embeddings import SentenceTransformerEmbedder
from app.services.arxiv_client import ArxivClient, ArxivUnavailableError
from app.services.cache import Cache


def _cut(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


async def _print_event(e: StageEvent) -> None:
    tokens = f"  tokens={e.tokens}" if e.tokens else ""
    provider = f"  [{e.provider}]" if e.provider else ""
    print(
        f"{e.elapsed_ms / 1000:6.1f}s  {e.stage:<11} {e.status:<9} {e.message}{provider}{tokens}"
    )


async def main(topic: str, papers: int, year_from: int | None) -> int:
    req = ReviewRequest(topic=topic, max_papers=papers, year_from=year_from)
    settings = get_settings()
    if not settings.groq_configured and not settings.demo_mode:
        print("GROQ_API_KEY is not set in .env (repo root). See .env.example.")
        return 2

    cache = Cache(settings.data_dir / "cache.sqlite")
    ctx = RunContext(
        settings=settings,
        router=build_router(settings, cache),
        arxiv=ArxivClient(
            cache, contact=settings.arxiv_contact, offline=settings.demo_mode
        ),
        embedder=SentenceTransformerEmbedder(),
        emit_fn=_print_event,
    )

    t0 = time.monotonic()
    queries = await plan(req.topic, ctx)
    print("          queries:", " | ".join(queries))
    try:
        candidates = await search(queries, ctx)
    except ArxivUnavailableError as e:
        print(f"arXiv unavailable: {e}")
        return 1

    await ctx.emit("ranking", "started", "Ranking by semantic relevance")
    selected = await rank(
        req.topic,
        candidates,
        ctx.embedder,
        top_n=req.max_papers,
        year_from=req.year_from,
    )
    await ctx.emit(
        "ranking",
        "completed",
        f"Selected top {len(selected)} of {len(candidates)} papers",
    )
    extractions = await extract(selected, ctx)
    total_s = time.monotonic() - t0

    print()
    print(
        f"{'Ref':<4}{'Year':<6}{'Rel':<6}{'Title':<46}{'Method':<36}{'Datasets':<24}Key result"
    )
    print("-" * 160)
    for p, x in zip(selected, extractions, strict=True):
        print(
            f"[{p.ref}] {p.year:<6}{p.relevance:<6.2f}{_cut(p.title, 44):<46}"
            f"{_cut(x.method, 34):<36}{_cut(', '.join(x.datasets) or '-', 22):<24}"
            f"{_cut(x.key_result, 50)}"
        )
    print()
    print(f"Total {total_s:.1f}s  tokens={ctx.tokens}  providers={ctx.providers_used}")
    for w in ctx.warnings:
        print(f"WARNING: {w}")
    cache.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="LitLens M2: print the extraction table"
    )
    parser.add_argument("topic")
    parser.add_argument("--papers", type=int, default=8, help="4-12 (default 8)")
    parser.add_argument("--year-from", type=int, default=None)
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.topic, args.papers, args.year_from)))
