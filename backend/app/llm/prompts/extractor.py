"""Extractor prompt (DESIGN §3.4). Bump PROMPT_VERSION on any wording change."""

from __future__ import annotations

from app.llm.base import Message
from app.llm.prompts.common import UNTRUSTED_NOTICE, wrap_paper
from app.models.schemas import Paper

PROMPT_VERSION = "extractor-v1"
MAX_TOKENS_PER_PAPER = 350

SYSTEM = f"""You extract structured facts from research paper abstracts.
{UNTRUSTED_NOTICE}

For EVERY paper given, return one object in "extractions" with:
- ref: the paper's ref number exactly as given
- problem: the problem the paper addresses
- method: the main method or model proposed or used
- datasets: list of dataset names mentioned ([] if none)
- metrics: list of {{"name", "value"}} for reported numbers, copied exactly as written
- key_result: the single most important result
- limitations: limitations stated by the authors

Rules:
- Use only what the title and abstract state. Never guess or use outside knowledge.
- If something is not stated, use exactly "Not reported" (for lists use []).
- Keep each text value under 25 words.
- Copy metric values exactly as written (keep units and % signs)."""


def build_messages(papers: list[Paper], error_note: str | None = None) -> list[Message]:
    body = "\n\n".join(wrap_paper(p.ref, p.title, p.abstract) for p in papers)
    refs = ", ".join(str(p.ref) for p in papers)
    user = f"Papers (refs {refs}):\n\n{body}"
    msgs = [Message("system", SYSTEM), Message("user", user)]
    if error_note:
        msgs.append(
            Message(
                "user",
                "Your previous answer was invalid: "
                f"{error_note}\nReturn corrected JSON for refs {refs} only.",
            )
        )
    return msgs


def max_tokens(n_papers: int) -> int:
    return 200 + MAX_TOKENS_PER_PAPER * n_papers
