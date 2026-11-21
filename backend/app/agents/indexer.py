"""Background indexer (SRS FR-16, FR-17, DESIGN §3.7).

After the review is returned: download each selected paper's PDF, extract
page text, chunk, embed and store. If a PDF fails, index its abstract instead
(`abstract_only`). Q&A becomes ready once at least one paper is indexed.
"""

from __future__ import annotations

import asyncio
import logging

from app.models.schemas import FulltextStatus, Paper
from app.pipeline.context import RunContext
from app.retrieval.chunker import Chunk, abstract_chunk, chunk_pages
from app.retrieval.embeddings import aembed
from app.retrieval.pdf import PdfError, PdfFetcher, extract_pages
from app.retrieval.vectorstore import VectorStore

log = logging.getLogger("litlens.indexer")


async def _chunks_for(
    p: Paper, fetcher: PdfFetcher
) -> tuple[list[Chunk], FulltextStatus]:
    try:
        path = await fetcher.fetch(p.arxiv_id)
        pages = await extract_pages(path)
        chunks = chunk_pages(pages, ref=p.ref, arxiv_id=p.arxiv_id)
        if not chunks:
            raise PdfError("no usable text")
        return chunks, "indexed"
    except PdfError as e:
        log.warning("paper [%d] %s: %s; using abstract", p.ref, p.arxiv_id, e)
        chunk = abstract_chunk(
            ref=p.ref, arxiv_id=p.arxiv_id, title=p.title, abstract=p.abstract
        )
        return [chunk], "abstract_only"


async def index_papers(
    papers: list[Paper],
    ctx: RunContext,
    *,
    fetcher: PdfFetcher,
    store: VectorStore,
) -> bool:
    """Index all papers for ctx.job_id. Updates each paper's fulltext_status.

    Returns True if Q&A can be used (at least one paper indexed in some form).
    """
    total = len(papers)
    if total == 0:
        await ctx.emit("indexing", "skipped", "No papers to index")
        return False
    await ctx.emit("indexing", "started", "Indexing full text", progress=(0, total))
    await asyncio.to_thread(store.delete, ctx.job_id)  # re-runs start clean

    for i, p in enumerate(papers, start=1):
        chunks, status = await _chunks_for(p, fetcher)
        try:
            vectors = await aembed(ctx.embedder, [c.text for c in chunks])
            await asyncio.to_thread(store.add, ctx.job_id, chunks, vectors)
        except Exception as e:
            log.warning("paper [%d] could not be stored: %s", p.ref, type(e).__name__)
            status = "failed"
        p.fulltext_status = status
        if i < total:
            await ctx.emit(
                "indexing",
                "progress",
                f"Indexing full text {i}/{total}",
                progress=(i, total),
            )

    n_full = sum(p.fulltext_status == "indexed" for p in papers)
    n_abs = sum(p.fulltext_status == "abstract_only" for p in papers)
    n_fail = sum(p.fulltext_status == "failed" for p in papers)
    parts = [f"Indexed {n_full} PDF{'' if n_full == 1 else 's'}"]
    if n_abs:
        parts.append(f"{n_abs} abstract only")
    if n_fail:
        parts.append(f"{n_fail} failed")
    ready = n_full + n_abs > 0
    if n_abs:
        ctx.warn(
            f"Full text unavailable for {n_abs} paper(s); Q&A uses their abstracts."
        )
    await ctx.emit(
        "indexing",
        "completed" if ready else "failed",
        ", ".join(parts),
        progress=(total, total),
    )
    return ready
