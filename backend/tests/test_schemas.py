from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AskRequest,
    Extraction,
    Paper,
    ReviewRequest,
    is_valid_arxiv_id,
)


def _paper(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ref": 1,
        "arxiv_id": "2401.01234",
        "title": "T",
        "authors": ["A"],
        "year": 2024,
        "published": "2024-01-03",
        "primary_category": "cs.CV",
        "abstract": "x",
        "url_abs": "https://arxiv.org/abs/2401.01234",
        "url_pdf": "https://arxiv.org/pdf/2401.01234",
        "relevance": 0.5,
    }
    base.update(overrides)
    return base


class TestReviewRequest:
    def test_defaults(self) -> None:
        r = ReviewRequest(topic="graph neural networks")
        assert r.max_papers == 8
        assert r.year_from is None

    def test_strips_control_chars_and_whitespace(self) -> None:
        r = ReviewRequest(topic="  crop\x00 disease\n\tdetection  ")
        assert r.topic == "crop disease detection"

    @pytest.mark.parametrize("topic", ["", "  ", "ab", "\x00\x01ab", "x" * 201])
    def test_rejects_bad_topic_length(self, topic: str) -> None:
        with pytest.raises(ValidationError):
            ReviewRequest(topic=topic)

    @pytest.mark.parametrize("n", [3, 13])
    def test_rejects_bad_max_papers(self, n: int) -> None:
        with pytest.raises(ValidationError):
            ReviewRequest(topic="valid topic", max_papers=n)

    def test_year_from_range(self) -> None:
        assert ReviewRequest(topic="abc", year_from=2020).year_from == 2020
        with pytest.raises(ValidationError):
            ReviewRequest(topic="abc", year_from=1989)
        with pytest.raises(ValidationError):
            ReviewRequest(topic="abc", year_from=date.today().year + 1)

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ReviewRequest(topic="abc", extra="x")  # type: ignore[call-arg]


class TestAskRequest:
    def test_cleans_and_limits(self) -> None:
        assert AskRequest(question=" what\x07 datasets? ").question == "what datasets?"
        with pytest.raises(ValidationError):
            AskRequest(question="x" * 501)


class TestArxivId:
    @pytest.mark.parametrize(
        "value",
        [
            "2401.01234",
            "2401.01234v2",
            "0704.0001",
            "hep-th/9901001",
            "math.GT/0309136",
        ],
    )
    def test_valid(self, value: str) -> None:
        assert is_valid_arxiv_id(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "2401.1",
            "../etc/passwd",
            "2401.01234/../x",
            "http://evil/2401.01234",
            "2401.01234 ",
            "2401.01234\n",
            "HEP-TH/9901001",
        ],
    )
    def test_invalid(self, value: str) -> None:
        assert not is_valid_arxiv_id(value)


class TestPaper:
    def test_valid_paper(self) -> None:
        assert Paper(**_paper()).fulltext_status == "pending"

    def test_rejects_bad_id(self) -> None:
        with pytest.raises(ValidationError):
            Paper(**_paper(arxiv_id="../../secret"))

    def test_rejects_non_arxiv_links(self) -> None:
        with pytest.raises(ValidationError):
            Paper(**_paper(url_abs="https://evil.example/abs/2401.01234"))


def test_extraction_defaults_to_not_reported() -> None:
    e = Extraction(ref=1)
    assert e.problem == e.method == e.key_result == e.limitations == "Not reported"
    assert e.datasets == [] and e.metrics == []
