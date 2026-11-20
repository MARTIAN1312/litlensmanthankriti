from __future__ import annotations

from app.agents.verifier import (
    normalise_markers,
    remove_invalid,
    split_sentences,
    verify,
)
from app.models.schemas import Extraction
from tests.fakes import StubEmbedder, paper


def test_normalise_marker_styles() -> None:
    assert normalise_markers("a [1, 3] b [2;4]") == "a [1][3] b [2][4]"
    assert normalise_markers("x [2-4] y [1–2]") == "x [2][3][4] y [1][2]"
    assert normalise_markers("huge [1-99]") == "huge [1-99]"  # not expanded


def test_remove_invalid_counts_and_tidies() -> None:
    md, total, valid, invalid = remove_invalid("A [1][9]. B [0]. C [2].", 3)
    assert (total, valid, invalid) == (4, 2, [0, 9])
    assert md == "A [1]. B. C [2]."


def test_split_sentences_handles_sections_tables_and_trailing_markers() -> None:
    md = (
        "## Overview\nFirst sentence here. Second one cites [1].\n\n"
        "## Key Themes\n- **Speed.** Small models run fast on phones [2]. [3]\n"
        "| Ref | Method |\n|---|---|\n| [1] | CNN |\n"
    )
    sents = split_sentences(md)
    texts = [s.text for s in sents]
    assert "First sentence here." in texts
    assert any(s.refs == [2, 3] and s.section == "Key Themes" for s in sents)
    assert all(not s.text.startswith("|") for s in sents)


async def test_verify_end_to_end() -> None:
    papers = [
        paper(
            1, "crop disease detection with CNN", "CNN detects crop disease on leaves"
        ),
        paper(2, "wheat rust drones", "multispectral drones detect wheat rust"),
    ]
    extractions = [Extraction(ref=1, method="CNN"), Extraction(ref=2, method="drones")]
    md = (
        "## Overview\nThis field studies plants.\n"
        "CNN models detect crop disease on leaves [1]. "
        "Quantum computing will replace farming entirely soon [2]. "
        "Bad ref here [7]. "
        "This sentence has no citation at all though.\n"
    )
    clean, v = await verify(md, papers, extractions, StubEmbedder(), threshold=0.35)
    assert "[7]" not in clean
    assert v.invalid_refs == [7]
    assert v.citation_validity == round(2 / 3, 4)
    weak_sentences = [w.sentence for w in v.weak_claims]
    assert any("Quantum" in s for s in weak_sentences)
    assert not any("CNN models" in s for s in weak_sentences)
    # first Overview sentence is exempt; "Bad ref here." is < 5 words
    assert v.uncited_sentences == 1


async def test_verify_no_citations() -> None:
    clean, v = await verify(
        "## Overview\nNothing.", [paper(1)], [], StubEmbedder(), threshold=0.35
    )
    assert v.citation_validity == 1.0 and v.weak_claims == []
