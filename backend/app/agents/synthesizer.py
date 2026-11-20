"""Synthesizer agent (SRS FR-14, DESIGN §3.5): papers + facts -> cited Markdown review.

If both providers fail, returns "" and a warning: the run still finishes with
papers, extractions and the table (DESIGN §9).
"""

from __future__ import annotations

import logging
import re

from app.llm.base import LLMError
from app.llm.prompts import synthesizer as prompt
from app.models.schemas import Extraction, Paper
from app.pipeline.context import RunContext

log = logging.getLogger("litlens.synthesizer")

_FENCE = re.compile(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", re.DOTALL)
_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")


def clean_markdown(text: str) -> str:
    """Strip code fences and raw HTML tags; normalise line endings."""
    text = text.replace("\r\n", "\n").strip()
    m = _FENCE.match(text)
    if m:
        text = m.group(1).strip()
    return _HTML_TAG.sub("", text)


def missing_sections(md: str) -> list[str]:
    present = {h.strip().lower() for h in re.findall(r"^##\s+(.+)$", md, re.MULTILINE)}
    return [s for s in prompt.SECTIONS if s.lower() not in present]


async def synthesize(
    topic: str, papers: list[Paper], extractions: list[Extraction], ctx: RunContext
) -> str:
    await ctx.emit("synthesizing", "started", "Writing the literature review")
    if not papers:
        await ctx.emit("synthesizing", "skipped", "No papers to review")
        return ""
    try:
        result = await ctx.router.complete(
            "synthesize",
            prompt.build_messages(topic, papers, extractions, ctx.failed_extractions),
            prompt_version=prompt.PROMPT_VERSION,
            max_tokens=prompt.MAX_TOKENS,
        )
    except LLMError as e:
        log.warning("synthesis failed: %s", e)
        ctx.warn(
            "The review could not be written; papers and table are still available."
        )
        await ctx.emit("synthesizing", "failed", "Review generation failed")
        return ""

    ctx.record("synthesizing", result)
    md = clean_markdown(result.text)
    if not md:
        ctx.warn("The model returned an empty review.")
        await ctx.emit(
            "synthesizing", "failed", "Empty review", provider=result.provider
        )
        return ""
    missing = missing_sections(md)
    if missing:
        ctx.warn(f"Review is missing sections: {', '.join(missing)}.")
    words = len(re.findall(r"\w+", md))
    await ctx.emit(
        "synthesizing",
        "completed",
        f"Review written ({words} words)",
        provider=result.provider,
    )
    return md
