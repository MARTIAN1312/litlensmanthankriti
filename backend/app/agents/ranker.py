"""Ranker (SRS FR-12, DESIGN §3.3): cosine similarity of local embeddings, top N."""

from __future__ import annotations

from app.models.internal import Candidate
from app.models.schemas import Paper
from app.retrieval.embeddings import Embedder, aembed


def paper_text(c: Candidate) -> str:
    return f"{c.title}. {c.abstract}"


async def rank(
    topic: str,
    candidates: list[Candidate],
    embedder: Embedder,
    *,
    top_n: int,
    year_from: int | None = None,
) -> list[Paper]:
    pool = [c for c in candidates if year_from is None or c.year >= year_from]
    if not pool:
        return []
    vecs = await aembed(embedder, [topic] + [paper_text(c) for c in pool])
    topic_vec, paper_vecs = vecs[0], vecs[1:]
    scores = paper_vecs @ topic_vec  # vectors are normalised -> cosine
    order = sorted(range(len(pool)), key=lambda i: float(scores[i]), reverse=True)

    papers: list[Paper] = []
    for ref, i in enumerate(order[:top_n], start=1):
        c = pool[i]
        papers.append(
            Paper(
                ref=ref,
                arxiv_id=c.arxiv_id,
                title=c.title,
                authors=c.authors,
                year=c.year,
                published=c.published,
                primary_category=c.primary_category,
                abstract=c.abstract,
                # Links are built here from the validated ID, never from LLM text (P-5).
                url_abs=f"https://arxiv.org/abs/{c.arxiv_id}",
                url_pdf=f"https://arxiv.org/pdf/{c.arxiv_id}",
                relevance=round(max(-1.0, min(1.0, float(scores[i]))), 4),
            )
        )
    return papers
