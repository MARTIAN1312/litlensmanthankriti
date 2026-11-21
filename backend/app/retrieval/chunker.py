"""Page-aware text chunker (DESIGN §3.7): ~500 tokens (~2,000 chars), ~100-token overlap.

Chunks never cross pages (so citations can say "p.X") and never split a word.
The reference list at the end of a paper is dropped: it matches many questions
but never answers them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

CHUNK_CHARS = 2000
OVERLAP_CHARS = 400
MIN_CHUNK_CHARS = 200

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
# "References", "8. REFERENCES", "VII Bibliography", "References:" ...
_REFS_HEADING = re.compile(
    r"^\s*(?:(?:\d+|[IVXLC]+)\.?\s+)?(references|bibliography)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class Chunk:
    ref: int
    arxiv_id: str
    page: int  # 1-based; abstract-only chunks use page 1
    text: str

    @property
    def id(self) -> str:
        digest = hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:12]  # noqa: S324
        return f"{self.ref}-{self.page}-{digest}"


def clean_text(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1\2", text)  # "detec-\ntion" -> "detection"
    return " ".join(text.split())


def drop_references(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Cut everything after a 'References' heading in the last 40% of the paper."""
    if not pages:
        return pages
    start = int(len(pages) * 0.6)
    for i in range(start, len(pages)):
        page_no, text = pages[i]
        m = _REFS_HEADING.search(text)
        if m:
            kept = pages[:i]
            head = text[: m.start()]
            if head.strip():
                kept.append((page_no, head))
            return kept
    return pages


def split_text(
    text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS
) -> list[str]:
    """Windows of ~size chars on word boundaries, each overlapping the previous."""
    words = text.split(" ")
    out: list[str] = []
    start = 0
    while start < len(words):
        length = 0
        end = start
        while end < len(words) and (
            length + len(words[end]) + 1 <= size or end == start
        ):
            length += len(words[end]) + 1
            end += 1
        out.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        # step back ~overlap chars, but always move forward
        back, back_len = end, 0
        while back > start + 1 and back_len < overlap:
            back -= 1
            back_len += len(words[back]) + 1
        start = back
    return out


def chunk_pages(
    pages: list[tuple[int, str]], *, ref: int, arxiv_id: str
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_no, raw in drop_references(pages):
        text = clean_text(raw)
        if len(text) < MIN_CHUNK_CHARS // 2:
            continue  # near-empty pages (figures only, etc.)
        for piece in split_text(text):
            if len(piece) >= MIN_CHUNK_CHARS or len(text) < MIN_CHUNK_CHARS:
                chunks.append(Chunk(ref, arxiv_id, page_no, piece))
    return chunks


def abstract_chunk(*, ref: int, arxiv_id: str, title: str, abstract: str) -> Chunk:
    """FR-17: when the PDF is unavailable, index the abstract instead."""
    return Chunk(ref, arxiv_id, 1, clean_text(f"{title}. {abstract}"))
