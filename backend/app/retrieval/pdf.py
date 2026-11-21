"""SSRF-safe arXiv PDF download and per-page text extraction (SECURITY §6, SRS FR-16/17).

- URL is always built from a validated arXiv ID: https://arxiv.org/pdf/{id}  (D-1, D-2)
- redirects followed manually, only to https://arxiv.org/...               (D-2)
- 30 s timeout, streamed with a 25 MB cap, body must start with %PDF        (D-3)
- saved only under data/pdfs/ with a sanitised file name                    (D-4)
- PyMuPDF parsing runs in a worker thread with a time budget                (D-5)
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from app.models.schemas import is_valid_arxiv_id
from app.services.arxiv_client import user_agent

log = logging.getLogger("litlens.pdf")

ALLOWED_HOST = "arxiv.org"
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT_S = 30.0
MAX_REDIRECTS = 3
PARSE_BUDGET_S = 20.0
MAX_PAGES = 40
POLITE_DELAY_S = 3.0  # arXiv terms: at most 1 request every 3 s


class PdfError(Exception):
    """Any download/parse failure. The caller falls back to the abstract."""


def pdf_filename(arxiv_id: str) -> str:
    """SECURITY V-3: old-style IDs contain '/', which becomes '_'."""
    if not is_valid_arxiv_id(arxiv_id):
        raise PdfError("invalid arXiv ID")
    return arxiv_id.replace("/", "_") + ".pdf"


def _check_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme != "https" or u.hostname != ALLOWED_HOST or u.port not in (None, 443):
        raise PdfError("redirect outside arxiv.org refused")


class PdfFetcher:
    def __init__(
        self,
        pdf_dir: Path,
        *,
        contact: str = "",
        offline: bool = False,
        client: httpx.AsyncClient | None = None,
        delay_s: float = POLITE_DELAY_S,
    ) -> None:
        self._dir = pdf_dir.resolve()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._offline = offline
        self._client = client or httpx.AsyncClient(
            timeout=TIMEOUT_S,
            follow_redirects=False,  # we follow them ourselves, arxiv.org only
            headers={"User-Agent": user_agent(contact)},
        )
        self._delay_s = delay_s
        self._lock = asyncio.Lock()  # one download at a time
        self._last = 0.0

    def path_for(self, arxiv_id: str) -> Path:
        path = (self._dir / pdf_filename(arxiv_id)).resolve()
        if path.parent != self._dir:  # D-4: must stay inside data/pdfs
            raise PdfError("unsafe path")
        return path

    async def fetch(self, arxiv_id: str) -> Path:
        """Return a local PDF path, downloading it once if needed."""
        path = self.path_for(arxiv_id)
        if path.is_file() and path.stat().st_size > 0:
            return path
        if self._offline:
            raise PdfError("offline: PDF not cached")
        async with self._lock:
            wait = self._last + self._delay_s - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                data = await self._download(f"https://arxiv.org/pdf/{arxiv_id}")
            finally:
                self._last = time.monotonic()
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        return path

    async def _download(self, url: str) -> bytes:
        for _ in range(MAX_REDIRECTS + 1):
            _check_url(url)
            try:
                async with self._client.stream("GET", url) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location", "")
                        url = urljoin(url, location)
                        continue
                    if resp.status_code != 200:
                        raise PdfError(f"HTTP {resp.status_code}")
                    declared = resp.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
                        raise PdfError("PDF too large")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise PdfError("PDF too large")
                        chunks.append(chunk)
            except httpx.HTTPError as e:
                raise PdfError(f"download failed ({type(e).__name__})") from None
            data = b"".join(chunks)
            if not data.startswith(b"%PDF"):
                raise PdfError("not a PDF")
            return data
        raise PdfError("too many redirects")

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_sync(path: Path, max_pages: int) -> list[tuple[int, str]]:
    import pymupdf

    pages: list[tuple[int, str]] = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text = page.get_text("text") or ""
            if text.strip():
                pages.append((i + 1, text))
    return pages


async def extract_pages(
    path: Path, *, max_pages: int = MAX_PAGES, budget_s: float = PARSE_BUDGET_S
) -> list[tuple[int, str]]:
    """[(page_number, text), ...] with 1-based page numbers. Raises PdfError."""
    try:
        pages = await asyncio.wait_for(
            asyncio.to_thread(_extract_sync, path, max_pages), timeout=budget_s
        )
    except TimeoutError:
        raise PdfError("PDF parsing took too long") from None
    except Exception as e:  # PyMuPDF raises several types on corrupt files
        raise PdfError(f"PDF parsing failed ({type(e).__name__})") from None
    if not pages:
        raise PdfError("no text in PDF (scanned?)")
    return pages
