"""RunContext: everything an agent needs besides its inputs (CLAUDE.md conventions).

Side effects (events, token accounting, warnings) go through here, so agents
stay simple `async def agent(inputs, ctx) -> outputs` functions.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.config import Settings
from app.llm.base import LLMResult
from app.llm.router import LLMRouter
from app.models.schemas import EventStatus, Progress, Provider, Stage, StageEvent
from app.retrieval.embeddings import Embedder
from app.services.arxiv_client import ArxivClient

EmitFn = Callable[[StageEvent], Awaitable[None]]


async def _discard(_: StageEvent) -> None:
    return None


@dataclass
class RunContext:
    settings: Settings
    router: LLMRouter
    arxiv: ArxivClient
    embedder: Embedder
    emit_fn: EmitFn = _discard
    job_id: UUID = field(default_factory=uuid4)
    started: float = field(default_factory=time.monotonic)
    warnings: list[str] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)  # model -> total
    stage_tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    providers_used: list[Provider] = field(default_factory=list)
    failed_extractions: set[int] = field(default_factory=set)  # refs

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def record(self, stage: Stage, result: LLMResult) -> None:
        """Account tokens and provider for one LLM call."""
        provider: Provider = result.provider  # type: ignore[assignment]
        if provider not in self.providers_used:
            self.providers_used.append(provider)
        if result.tokens:
            self.tokens[result.model] = self.tokens.get(result.model, 0) + result.tokens
            st = self.stage_tokens.setdefault(stage, {})
            st[result.model] = st.get(result.model, 0) + result.tokens

    async def emit(
        self,
        stage: Stage,
        status: EventStatus,
        message: str,
        *,
        progress: tuple[int, int] | None = None,
        provider: str | None = None,
    ) -> None:
        tokens = self.stage_tokens.get(stage)
        await self.emit_fn(
            StageEvent(
                job_id=self.job_id,
                stage=stage,
                status=status,
                message=message,
                progress=Progress(current=progress[0], total=progress[1])
                if progress
                else None,
                elapsed_ms=self.elapsed_ms(),
                tokens=dict(tokens) if tokens else None,
                provider=provider,  # type: ignore[arg-type]
            )
        )
