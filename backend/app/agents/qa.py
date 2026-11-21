"""RAG Q&A agent (SRS FR-30..33, DESIGN §3.7).

question -> embed -> top-4 chunks (max 2 per paper) -> answer citing [n, p.X].
Citations to papers/pages that weren't retrieved are removed (SECURITY P-5).
"""

from __future__ import annotations

import asyncio
import logging
import re
from uuid import UUID

from app.agents.synthesizer import clean_markdown
from app.agents.verifier import ascii_brackets
from app.llm.base import LLMError
from app.llm.prompts import qa as prompt
from app.llm.router import LLMRouter
from app.models.schemas import AskResponse, QASource
from app.retrieval.embeddings import Embedder, aembed
from app.retrieval.vectorstore import VectorStore

log = logging.getLogger("litlens.qa")

TOP_K = 4
MAX_PER_PAPER = 2
# Measured on real papers: off-topic questions top out ~0.18-0.24, vague but
# valid ones ("main limitations?") ~0.28. Below this we refuse without an LLM call;
# borderline cases still go to the LLM, which refuses if the chunks don't help.
MIN_SCORE = 0.22
SNIPPET_CHARS = 400
_CITE = re.compile(r"\[\s*(\d+)\s*,\s*p\.?\s*(\d+)\s*\]")


class QAUnavailableError(Exception):
    """Both LLM providers failed."""


def snippet(text: str) -> str:
    return (
        text
        if len(text) <= SNIPPET_CHARS
        else text[: SNIPPET_CHARS - 1].rsplit(" ", 1)[0] + "…"
    )


def keep_valid_citations(md: str, allowed: set[tuple[int, int]]) -> str:
    """Normalise to [n, p.X]; drop citations of chunks we didn't retrieve."""

    def repl(m: re.Match[str]) -> str:
        ref, page = int(m.group(1)), int(m.group(2))
        return f"[{ref}, p.{page}]" if (ref, page) in allowed else ""

    out = _CITE.sub(repl, ascii_brackets(md))
    return re.sub(r"[ \t]+([.,;:])", r"\1", out).strip()


async def answer(
    job_id: UUID,
    question: str,
    *,
    embedder: Embedder,
    store: VectorStore,
    router: LLMRouter,
) -> AskResponse:
    qvec = (await aembed(embedder, [question]))[0]
    hits = await asyncio.to_thread(
        store.query, job_id, qvec, k=TOP_K, max_per_paper=MAX_PER_PAPER
    )
    if not hits or hits[0][1] < MIN_SCORE:
        return AskResponse(answer_md=prompt.NOT_COVERED, sources=[])

    chunks = [c for c, _ in hits]
    try:
        result = await router.complete(
            "answer",
            prompt.build_messages(question, chunks),
            prompt_version=prompt.PROMPT_VERSION,
            max_tokens=prompt.MAX_TOKENS,
        )
    except LLMError as e:
        log.warning("Q&A failed: %s", e)
        raise QAUnavailableError from None
    log.info("qa job=%s provider=%s tokens=%d", job_id, result.provider, result.tokens)

    allowed = {(c.ref, c.page) for c in chunks}
    answer_md = keep_valid_citations(clean_markdown(result.text), allowed)
    if not answer_md or prompt.NOT_COVERED.lower() in answer_md.lower():
        return AskResponse(answer_md=prompt.NOT_COVERED, sources=[])
    return AskResponse(
        answer_md=answer_md,
        sources=[
            QASource(
                ref=c.ref,
                arxiv_id=c.arxiv_id,
                page=c.page,
                snippet=snippet(c.text),
                score=score,
            )
            for c, score in hits
        ],
    )
