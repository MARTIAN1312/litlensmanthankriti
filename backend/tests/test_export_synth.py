from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.agents.synthesizer import clean_markdown, missing_sections, synthesize
from app.llm.base import PermanentError
from app.llm.prompts import synthesizer as synth_prompt
from app.models.schemas import Extraction, Paper, ReviewResult
from app.services.export import bibtex_escape, to_bibtex, to_markdown
from tests.fakes import FakeProvider, make_ctx, make_router, paper

FULL_REVIEW = "\n\n".join(f"## {s}\nText about it [1]." for s in synth_prompt.SECTIONS)

# ---------------- synthesizer ----------------


def test_clean_markdown_strips_fences_and_html() -> None:
    assert clean_markdown("```markdown\n## Overview\nHi <script>x</script>\n```") == (
        "## Overview\nHi x"
    )


def test_missing_sections() -> None:
    assert missing_sections(FULL_REVIEW) == []
    assert missing_sections("## Overview\nx") == list(synth_prompt.SECTIONS[1:])


def test_prompt_uses_facts_not_abstracts() -> None:
    p = paper(1, "T", abstract="SECRET ABSTRACT TEXT")
    msgs = synth_prompt.build_messages("topic", [p], [Extraction(ref=1, method="CNN")])
    assert "SECRET ABSTRACT TEXT" not in msgs[1].content
    assert '"method": "CNN"' in msgs[1].content
    assert "valid refs 1..1" in msgs[1].content


async def test_synthesize_success(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [FULL_REVIEW])
    ctx, events = make_ctx(tmp_path, make_router(tmp_path, groq=groq))
    md = await synthesize("t", [paper(1)], [Extraction(ref=1)], ctx)
    assert md.startswith("## Overview")
    assert groq.calls[0]["model"] == "openai/gpt-oss-120b"
    assert events[-1].status == "completed" and not ctx.warnings


async def test_synthesize_failure_degrades(tmp_path: Path) -> None:
    groq = FakeProvider("groq", [PermanentError("400")])
    ctx, events = make_ctx(tmp_path, make_router(tmp_path, groq=groq))
    assert await synthesize("t", [paper(1)], [], ctx) == ""
    assert events[-1].status == "failed" and ctx.warnings


async def test_synthesize_warns_on_missing_sections(tmp_path: Path) -> None:
    groq = FakeProvider("groq", ["## Overview\nOnly this [1]."])
    ctx, _ = make_ctx(tmp_path, make_router(tmp_path, groq=groq))
    await synthesize("t", [paper(1)], [], ctx)
    assert any("missing sections" in w for w in ctx.warnings)


# ---------------- export ----------------


def _result(papers: list[Paper]) -> ReviewResult:
    return ReviewResult(
        job_id=uuid4(),
        status="done",
        topic="Crop | disease",
        created_at=datetime(2026, 11, 21, tzinfo=UTC),
        papers=papers,
        extractions=[Extraction(ref=p.ref, method="CNN | ViT") for p in papers],
        review_md=FULL_REVIEW,
    )


def test_markdown_export() -> None:
    md = to_markdown(_result([paper(1, "A {weird} title")]))
    assert md.startswith("# Literature review: Crop | disease")
    assert "## Comparison table" in md and "CNN \\| ViT" in md
    assert (
        "[1] A (2024). A {weird} title. arXiv:2401.00001. https://arxiv.org/abs/2401.00001"
        in md
    )


def test_bibtex_escaping_and_keys() -> None:
    assert (
        bibtex_escape("a{b}c\\d 50% & x_y") == r"a\{b\}c\textbackslash{}d 50\% \& x\_y"
    )
    p1 = paper(1, "Deep {Learning} for Crops")
    p1.authors = ["Jürgen Müller", "B. Smith"]
    p2 = paper(2, "Deep {Learning} for Crops")
    p2.authors = ["Jürgen Müller"]
    bib = to_bibtex([p1, p2])
    assert "@misc{muller2024deep," in bib and "@misc{muller2024deep2," in bib
    assert "title = {{Deep \\{Learning\\} for Crops}}" in bib
    assert "author = {Jürgen Müller and B. Smith}" in bib
    assert "eprint = {2401.00001}" in bib
    # braces balanced in every entry
    for entry in bib.split("\n\n"):
        stripped = entry.replace("\\{", "").replace("\\}", "")
        assert stripped.count("{") == stripped.count("}")
    json.dumps(bib)  # plain text, serialisable
