"""The frontend mock fixtures must match the backend contracts (DESIGN §4)."""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter

from app.config import REPO_ROOT
from app.models.schemas import (
    AskResponse,
    DemoTopicsResponse,
    HealthResponse,
    ReviewResult,
    StageEvent,
)

MOCKS = REPO_ROOT / "frontend" / "src" / "mocks"


def _load(name: str) -> Any:
    return json.loads((MOCKS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("file", "model"),
    [
        ("review.json", ReviewResult),
        ("ask.json", AskResponse),
        ("health.json", HealthResponse),
        ("demo-topics.json", DemoTopicsResponse),
    ],
)
def test_mock_matches_model(file: str, model: type[BaseModel]) -> None:
    data = _load(file)
    parsed = model.model_validate(data)
    # Round-trip equality: no unknown keys silently dropped, no missing fields.
    assert parsed.model_dump(mode="json") == data


def test_events_mock_matches_model() -> None:
    data = _load("events.json")
    events = TypeAdapter(list[StageEvent]).validate_python(data)
    assert events, "events.json must not be empty"
    assert [e.model_dump(mode="json", exclude_none=True) for e in events] == data
    assert any(e.stage == "done" for e in events)
    elapsed = [e.elapsed_ms for e in events]
    assert elapsed == sorted(elapsed), "events must be in time order"


def test_review_mock_is_internally_consistent() -> None:
    review = ReviewResult.model_validate(_load("review.json"))
    refs = [p.ref for p in review.papers]
    assert refs == list(range(1, len(refs) + 1))
    assert sorted(e.ref for e in review.extractions) == refs
    assert review.stats.papers_selected == len(refs)
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", review.review_md)}
    assert cited <= set(refs), "review cites a paper that is not in the list"
    for claim in review.verification.weak_claims if review.verification else []:
        assert claim.ref in refs
