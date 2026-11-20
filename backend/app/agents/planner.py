"""Planner agent (SRS FR-10, DESIGN §3.1): topic -> 2-3 arXiv search queries."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.llm.base import LLMError, strict_json_schema
from app.llm.prompts import planner as prompt
from app.models.internal import PlannerOutput
from app.pipeline.context import RunContext
from app.services.arxiv_client import query_terms

log = logging.getLogger("litlens.planner")
MAX_QUERIES = 3


def clean_queries(topic: str, raw: list[str]) -> list[str]:
    """Keep the topic first, drop empty/duplicate queries, cap at 3."""
    out: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for q in [topic, *raw]:
        q = " ".join(q.split())[:200]
        terms = tuple(sorted(query_terms(q)))
        if len(terms) == 0 or terms in seen:
            continue
        seen.add(terms)
        out.append(q)
    return out[:MAX_QUERIES]


async def plan(topic: str, ctx: RunContext) -> list[str]:
    await ctx.emit("planning", "started", "Planning search queries")
    provider = None
    try:
        result = await ctx.router.complete(
            "plan",
            prompt.build_messages(topic),
            prompt_version=prompt.PROMPT_VERSION,
            max_tokens=prompt.MAX_TOKENS,
            json_schema=strict_json_schema(PlannerOutput),
            schema_name="search_queries",
        )
        ctx.record("planning", result)
        provider = result.provider
        queries = clean_queries(
            topic, PlannerOutput.model_validate_json(result.text).queries
        )
    except (LLMError, ValidationError) as e:
        log.warning("planner failed, using raw topic: %s", type(e).__name__)
        ctx.warn("Query planning failed; searched with your topic only.")
        queries = [topic]
    await ctx.emit(
        "planning",
        "completed",
        f"{len(queries)} search quer{'y' if len(queries) == 1 else 'ies'} ready",
        provider=provider,
    )
    return queries
