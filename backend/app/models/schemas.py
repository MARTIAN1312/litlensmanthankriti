"""All API data contracts (DESIGN §4).

This file, `frontend/src/api/types.ts` and `frontend/src/mocks/*.json` must
always agree. `tests/test_mocks_match_schemas.py` enforces it for the mocks.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

# SECURITY V-3: strict arXiv ID patterns (new style, old style), optional version.
ARXIV_ID_NEW = r"\d{4}\.\d{4,5}(v\d+)?"
ARXIV_ID_OLD = r"[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?"
ARXIV_ID_RE = re.compile(rf"^(?:{ARXIV_ID_NEW}|{ARXIV_ID_OLD})$")

ARXIV_URL_PREFIX = "https://arxiv.org/"
MIN_YEAR = 1990

NOT_REPORTED = "Not reported"


def is_valid_arxiv_id(value: str) -> bool:
    return bool(ARXIV_ID_RE.fullmatch(value))


def clean_text(value: object) -> object:
    """Strip control characters and collapse whitespace (SECURITY V-1)."""
    if not isinstance(value, str):
        return value
    no_controls = "".join(
        " " if unicodedata.category(ch) == "Cc" else ch for ch in value
    )
    return " ".join(no_controls.split())


class _Request(BaseModel):
    """Request bodies reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# §4.1 Request / Job
# --------------------------------------------------------------------------- #


class ReviewRequest(_Request):
    topic: Annotated[
        str, BeforeValidator(clean_text), Field(min_length=3, max_length=200)
    ]
    max_papers: Annotated[int, Field(ge=4, le=12)] = 8
    year_from: int | None = None

    @field_validator("year_from")
    @classmethod
    def _year_in_range(cls, v: int | None) -> int | None:
        if v is None:
            return None
        current = date.today().year
        if not MIN_YEAR <= v <= current:
            raise ValueError(f"year_from must be between {MIN_YEAR} and {current}")
        return v


JobStatusQueued = Literal["queued"]


class JobCreated(BaseModel):
    job_id: UUID
    status: JobStatusQueued = "queued"


# --------------------------------------------------------------------------- #
# §4.2 SSE event
# --------------------------------------------------------------------------- #

Stage = Literal[
    "planning",
    "searching",
    "ranking",
    "extracting",
    "synthesizing",
    "verifying",
    "indexing",
    "done",
    "error",
]
EventStatus = Literal["started", "progress", "completed", "failed", "skipped"]
Provider = Literal["groq", "gemini", "cache"]


class Progress(BaseModel):
    current: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]


class StageEvent(BaseModel):
    job_id: UUID
    stage: Stage
    status: EventStatus
    message: str
    progress: Progress | None = None
    elapsed_ms: Annotated[int, Field(ge=0)]
    tokens: dict[str, int] | None = None  # model id -> cumulative tokens for the stage
    provider: Provider | None = None


# --------------------------------------------------------------------------- #
# §4.3 Review result
# --------------------------------------------------------------------------- #

FulltextStatus = Literal["pending", "indexed", "abstract_only", "failed"]
ReviewStatus = Literal["running", "done", "error"]


class Paper(BaseModel):
    ref: Annotated[int, Field(ge=1)]
    arxiv_id: str  # without version suffix
    title: str
    authors: list[str]
    year: int
    published: date
    primary_category: str
    abstract: str
    url_abs: str
    url_pdf: str
    relevance: Annotated[float, Field(ge=-1.0, le=1.0)]
    fulltext_status: FulltextStatus = "pending"

    @field_validator("arxiv_id")
    @classmethod
    def _valid_arxiv_id(cls, v: str) -> str:
        if not is_valid_arxiv_id(v):
            raise ValueError("invalid arXiv ID")
        return v

    @model_validator(mode="after")
    def _links_are_arxiv(self) -> Paper:
        # SECURITY P-5 / R-2: links shown in the UI always point at arxiv.org.
        for url in (self.url_abs, self.url_pdf):
            if not url.startswith(ARXIV_URL_PREFIX):
                raise ValueError("paper links must start with https://arxiv.org/")
        return self


class Metric(BaseModel):
    name: str
    value: str


class Extraction(BaseModel):
    ref: Annotated[int, Field(ge=1)]
    problem: str = NOT_REPORTED
    method: str = NOT_REPORTED
    datasets: list[str] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    key_result: str = NOT_REPORTED
    limitations: str = NOT_REPORTED


class WeakClaim(BaseModel):
    sentence: str
    ref: Annotated[int, Field(ge=1)]
    score: float


class Verification(BaseModel):
    citation_validity: Annotated[float, Field(ge=0.0, le=1.0)]
    invalid_refs: list[int] = Field(default_factory=list)
    weak_claims: list[WeakClaim] = Field(default_factory=list)
    uncited_sentences: Annotated[int, Field(ge=0)] = 0


class Stats(BaseModel):
    total_ms: Annotated[int, Field(ge=0)] = 0
    stage_ms: dict[str, int] = Field(default_factory=dict)
    tokens: dict[str, int] = Field(default_factory=dict)
    providers_used: list[Provider] = Field(default_factory=list)
    papers_considered: Annotated[int, Field(ge=0)] = 0
    papers_selected: Annotated[int, Field(ge=0)] = 0


class ReviewResult(BaseModel):
    job_id: UUID
    status: ReviewStatus
    topic: str
    created_at: datetime
    queries: list[str] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    extractions: list[Extraction] = Field(default_factory=list)
    review_md: str = ""
    verification: Verification | None = None
    stats: Stats = Field(default_factory=Stats)
    warnings: list[str] = Field(default_factory=list)
    qa_ready: bool = False


# --------------------------------------------------------------------------- #
# §4.4 Q&A
# --------------------------------------------------------------------------- #


class AskRequest(_Request):
    question: Annotated[
        str, BeforeValidator(clean_text), Field(min_length=3, max_length=500)
    ]


class QASource(BaseModel):
    ref: Annotated[int, Field(ge=1)]
    arxiv_id: str
    page: Annotated[int, Field(ge=1)]
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer_md: str
    sources: list[QASource] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# §4.5 Errors
# --------------------------------------------------------------------------- #

ErrorCode = Literal[
    "VALIDATION_ERROR",
    "NOT_FOUND",
    "NOT_READY",
    "RATE_LIMITED",
    "UPSTREAM_ERROR",
    "INTERNAL",
]


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --------------------------------------------------------------------------- #
# §4.6 Misc endpoints
# --------------------------------------------------------------------------- #


class ProvidersStatus(BaseModel):
    groq: bool
    gemini: bool


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    env: Literal["dev", "prod"]
    demo_mode: bool
    providers: ProvidersStatus


class DemoTopicsResponse(BaseModel):
    topics: list[str]
