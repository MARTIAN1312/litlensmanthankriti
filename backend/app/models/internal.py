"""Internal (non-API) models passed between agents. Not part of the DESIGN §4 contract."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.schemas import is_valid_arxiv_id


class Candidate(BaseModel):
    """A paper found by the searcher, before ranking assigns `ref` and `relevance`."""

    arxiv_id: str  # no version suffix
    title: str
    authors: list[str]
    published: date
    primary_category: str
    abstract: str

    @field_validator("arxiv_id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        if not is_valid_arxiv_id(v):
            raise ValueError("invalid arXiv ID")
        return v

    @property
    def year(self) -> int:
        return self.published.year


# --- LLM output schemas (strict mode: every field required, no extras) ---


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlannerOutput(_Strict):
    queries: Annotated[list[str], Field(min_length=1, max_length=5)]


class MetricOut(_Strict):
    name: str
    value: str


class ExtractionOut(_Strict):
    ref: int
    problem: str
    method: str
    datasets: list[str]
    metrics: list[MetricOut]
    key_result: str
    limitations: str


class ExtractorOutput(_Strict):
    extractions: list[ExtractionOut]
