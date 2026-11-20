"""Verifier (SRS FR-15, DESIGN §3.6): local hallucination guard, 0 LLM tokens.

1. Normalise citation styles ([1, 3] / [1-3] -> [1][3] / [1][2][3]).
2. Remove markers outside 1..N and record them (invalid_refs).
3. Support score per (cited sentence, ref) = max cosine(sentence, abstract),
   cosine(sentence, extraction summary). Below threshold -> weak claim.
4. Count factual sentences with no citation (except the Overview's first).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from app.models.schemas import NOT_REPORTED, Extraction, Paper, Verification, WeakClaim
from app.retrieval.embeddings import Embedder, aembed

MARKER = re.compile(r"\[(\d+)\]")
_LIST = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)+)\]")
_RANGE = re.compile(r"\[(\d+)\s*[-–]\s*(\d+)\]")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z*\[(\"'\d])")
_ONLY_MARKERS = re.compile(r"^(\s*\[\d+\])+[.,;:]?\s*$")
MIN_WORDS = 5
MAX_RANGE = 12


@dataclass
class _Sentence:
    text: str  # as it appears in the final Markdown
    section: str
    refs: list[int]


def normalise_markers(md: str) -> str:
    def expand_list(m: re.Match[str]) -> str:
        return "".join(f"[{n}]" for n in re.split(r"\s*[,;]\s*", m.group(1)))

    def expand_range(m: re.Match[str]) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        if a > b or b - a > MAX_RANGE:
            return m.group(0)
        return "".join(f"[{n}]" for n in range(a, b + 1))

    return _RANGE.sub(expand_range, _LIST.sub(expand_list, md))


def remove_invalid(md: str, n_papers: int) -> tuple[str, int, int, list[int]]:
    """Returns (clean_md, total_markers, valid_markers, invalid_refs)."""
    total = valid = 0
    invalid: set[int] = set()

    def repl(m: re.Match[str]) -> str:
        nonlocal total, valid
        total += 1
        ref = int(m.group(1))
        if 1 <= ref <= n_papers:
            valid += 1
            return m.group(0)
        invalid.add(ref)
        return ""

    clean = MARKER.sub(repl, md)
    clean = re.sub(r"[ \t]+([.,;:])", r"\1", clean)  # tidy "word [99]." -> "word."
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    return clean, total, valid, sorted(invalid)


def split_sentences(md: str) -> list[_Sentence]:
    out: list[_Sentence] = []
    section = ""
    for raw in md.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        if line.startswith("|"):
            continue  # table rows: refs validated above, no support scoring
        line = re.sub(r"^([-*+]|\d+\.)\s+", "", line)  # list bullets
        parts = _SPLIT.split(line)
        merged: list[str] = []
        for p in parts:
            if merged and _ONLY_MARKERS.match(p):
                merged[-1] = f"{merged[-1]} {p.strip()}"
            else:
                merged.append(p.strip())
        for s in merged:
            refs = [int(r) for r in MARKER.findall(s)]
            out.append(_Sentence(s, section, list(dict.fromkeys(refs))))
    return out


def plain(sentence: str) -> str:
    return " ".join(MARKER.sub("", sentence).replace("**", "").replace("*", "").split())


def extraction_summary(e: Extraction | None) -> str:
    if e is None:
        return ""
    bits = [e.problem, e.method, e.key_result, e.limitations, ", ".join(e.datasets)]
    bits += [f"{m.name} {m.value}" for m in e.metrics]
    return ". ".join(b for b in bits if b and b != NOT_REPORTED)


async def verify(
    review_md: str,
    papers: list[Paper],
    extractions: list[Extraction],
    embedder: Embedder,
    *,
    threshold: float,
) -> tuple[str, Verification]:
    n = len(papers)
    md, total, valid, invalid = remove_invalid(normalise_markers(review_md), n)
    validity = round(valid / total, 4) if total else 1.0

    sentences = split_sentences(md)
    uncited = 0
    first_overview_seen = False
    cited: list[_Sentence] = []
    for s in sentences:
        is_first_overview = s.section.lower() == "overview" and not first_overview_seen
        if s.section.lower() == "overview":
            first_overview_seen = True
        if s.refs:
            cited.append(s)
        elif len(plain(s.text).split()) >= MIN_WORDS and not is_first_overview:
            uncited += 1

    weak: list[WeakClaim] = []
    if cited:
        by_ref = {p.ref: p for p in papers}
        ex_by_ref = {e.ref: e for e in extractions}
        refs = sorted({r for s in cited for r in s.refs})
        texts = [plain(s.text) for s in cited]
        texts += [f"{by_ref[r].title}. {by_ref[r].abstract}" for r in refs]
        texts += [extraction_summary(ex_by_ref.get(r)) or by_ref[r].title for r in refs]
        vecs = await aembed(embedder, texts)
        k = len(cited)
        sent_vecs = vecs[:k]
        abs_vecs = {r: vecs[k + i] for i, r in enumerate(refs)}
        ex_vecs = {r: vecs[k + len(refs) + i] for i, r in enumerate(refs)}
        for s, sv in zip(cited, sent_vecs, strict=True):
            for r in s.refs:
                score = float(max(np.dot(sv, abs_vecs[r]), np.dot(sv, ex_vecs[r])))
                if score < threshold:
                    weak.append(
                        WeakClaim(sentence=s.text, ref=r, score=round(score, 3))
                    )

    return md, Verification(
        citation_validity=validity,
        invalid_refs=invalid,
        weak_claims=weak,
        uncited_sentences=uncited,
    )
