"""arXiv search client: cached, polite (≤ 1 request / 3 s, single connection).

SECURITY D-6, SRS C3, FR-11, FR-50.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading

import arxiv

from app.models.internal import Candidate
from app.models.schemas import is_valid_arxiv_id
from app.services.cache import Cache, make_key

log = logging.getLogger("litlens.arxiv")

CACHE_VERSION = 1
_VERSION_SUFFIX = re.compile(r"v\d+$")
_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")
_STOPWORDS = frozenset(
    "a an and are as at by for from in into is of on or the to using via with "
    "based towards toward".split()
)
MAX_TERMS = 6
MIN_TERMS = 2


class ArxivUnavailableError(Exception):
    """arXiv could not be reached, or a cache miss in offline/demo mode."""


def strip_version(arxiv_id: str) -> str:
    return _VERSION_SUFFIX.sub("", arxiv_id)


def query_terms(query: str) -> list[str]:
    """Plain keywords only: no quotes, parentheses or field prefixes can get through."""
    terms = [t.lower() for t in _TERM.findall(query)]
    seen: list[str] = []
    for t in terms:
        if t not in _STOPWORDS and t not in seen:
            seen.append(t)
    return seen[:MAX_TERMS]


def build_query(terms: list[str]) -> str:
    """`all:a AND all:b ...`: a plain phrase matches far too loosely on arXiv."""
    return " AND ".join(f"all:{t}" for t in terms)


def _clean(text: str) -> str:
    return " ".join(text.split())


def user_agent(contact: str) -> str:
    safe = "".join(ch for ch in contact if 32 < ord(ch) < 127 and ch not in "()")
    return f"LitLens/1.0 (student project; {safe or 'no contact set'})"


class ArxivClient:
    def __init__(
        self,
        cache: Cache,
        *,
        contact: str = "",
        offline: bool = False,
        delay_seconds: float = 3.0,
    ) -> None:
        self._cache = cache
        self._offline = offline
        self._client = arxiv.Client(
            page_size=25, delay_seconds=delay_seconds, num_retries=3
        )
        self._lock = threading.Lock()  # single connection to arXiv
        # The arxiv package hard-codes its User-Agent; D-6 asks for ours + a contact.
        if hasattr(arxiv, "_USER_AGENT"):
            arxiv._USER_AGENT = user_agent(contact)

    async def search(self, query: str, max_results: int = 10) -> list[Candidate]:
        """Search with progressively fewer terms until we get a few results."""
        terms = query_terms(query)
        if not terms:
            return []
        best: list[Candidate] = []
        while True:
            results = await self._search_terms(terms, max_results)
            if len(results) > len(best):
                best = results
            if len(results) >= 3 or len(terms) <= MIN_TERMS:
                return best
            terms = terms[:-1]

    async def _search_terms(
        self, terms: list[str], max_results: int
    ) -> list[Candidate]:
        q = build_query(terms)
        key = make_key("arxiv_search", CACHE_VERSION, q, max_results)
        cached = self._cache.get_http(key)
        if cached is not None:
            return [Candidate.model_validate(c) for c in cached]
        if self._offline:
            raise ArxivUnavailableError("Offline demo mode: query not in cache")
        try:
            results = await asyncio.to_thread(self._search_sync, q, max_results)
        except Exception as e:  # arxiv raises several error types
            log.warning("arXiv search failed: %s", type(e).__name__)
            raise ArxivUnavailableError("arXiv search failed") from None
        self._cache.set_http(key, [c.model_dump(mode="json") for c in results])
        return results

    def _search_sync(self, q: str, max_results: int) -> list[Candidate]:
        search = arxiv.Search(
            query=q, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
        )
        out: list[Candidate] = []
        with self._lock:
            for r in self._client.results(search):
                arxiv_id = strip_version(r.get_short_id())
                if not is_valid_arxiv_id(arxiv_id):
                    continue
                out.append(
                    Candidate(
                        arxiv_id=arxiv_id,
                        title=_clean(r.title),
                        authors=[a.name for a in r.authors],
                        published=r.published.date(),
                        primary_category=r.primary_category,
                        abstract=_clean(r.summary),
                    )
                )
        return out
