"""Synthesizer prompt (DESIGN §3.5). Bump PROMPT_VERSION on any wording change.

Input is the numbered paper list + extracted facts, NOT raw abstracts (saves tokens).
"""

from __future__ import annotations

import json

from app.llm.base import Message
from app.llm.prompts.common import UNTRUSTED_NOTICE, neutralise_tags
from app.models.schemas import Extraction, Paper

PROMPT_VERSION = "synthesizer-v2"
MAX_TOKENS = 1800  # ~600 words of Markdown plus low reasoning

SECTIONS = (
    "Overview",
    "Key Themes",
    "Methods & Results Comparison",
    "Research Gaps",
    "Conclusion",
)

SYSTEM = f"""You write concise, accurate literature reviews for researchers.
{UNTRUSTED_NOTICE}

Write the review in Markdown with exactly these H2 sections, in this order:
{chr(10).join(f"## {s}" for s in SECTIONS)}

Citation rules (most important):
- Cite papers ONLY by their ref number in square brackets, e.g. [3] or [2][5].
- Use only refs from the list you are given. Never invent papers, authors or numbers.
- Every factual sentence must end with at least one citation.
- Only state what the extracted facts support. Do not add outside knowledge.
- A paper marked "FACTS: unavailable" could not be analysed. You may mention it by title,
  but never claim anything about what it reports or omits.

Content rules:
- Overview: 2-3 sentences on what the field is trying to do.
- Key Themes: 3-4 short themes, each as a bold label followed by 1-2 cited sentences.
- Methods & Results Comparison: a Markdown table with columns Ref | Method | Data | Result,
  using the extracted values, then 1-2 cited sentences comparing them.
- Research Gaps: grounded in stated limitations and in what papers do NOT report
  (e.g. many papers report no real-world evaluation). Cite the papers concerned.
- Conclusion: 2 sentences.
- 350-600 words in total. Plain Markdown only: no HTML, no links, no images."""


def _facts(e: Extraction) -> dict[str, object]:
    return {
        "problem": e.problem,
        "method": e.method,
        "datasets": e.datasets or ["Not reported"],
        "metrics": [f"{m.name}: {m.value}" for m in e.metrics] or ["Not reported"],
        "key_result": e.key_result,
        "limitations": e.limitations,
    }


def build_messages(
    topic: str,
    papers: list[Paper],
    extractions: list[Extraction],
    failed_refs: frozenset[int] | set[int] = frozenset(),
) -> list[Message]:
    by_ref = {e.ref: e for e in extractions}
    blocks = []
    for p in papers:
        if p.ref in failed_refs or p.ref not in by_ref:
            facts = "unavailable (could not be extracted)"
        else:
            facts = json.dumps(_facts(by_ref[p.ref]), ensure_ascii=False)
        blocks.append(
            f'<paper ref="{p.ref}">\nTITLE: {neutralise_tags(p.title)} ({p.year})\n'
            f"FACTS: {neutralise_tags(facts)}\n</paper>"
        )
    refs = f"1..{len(papers)}"
    user = (
        f"Topic: {topic}\n\nPapers (valid refs {refs}):\n\n"
        + "\n\n".join(blocks)
        + f"\n\nWrite the literature review now. Cite only refs {refs}."
    )
    return [Message("system", SYSTEM), Message("user", user)]
