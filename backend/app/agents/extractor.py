"""Extractor agent (SRS FR-13, DESIGN §3.4): papers -> schema-validated facts.

Per batch of ~4 papers:
1. primary route (router already falls back to Gemini on provider errors)
2. same again with the validation error appended
3. fallback provider only (if configured)
4. "Not reported" placeholders, so one bad batch never breaks the run
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.llm.base import LLMError, strict_json_schema
from app.llm.prompts import extractor as prompt
from app.models.internal import ExtractionOut, ExtractorOutput
from app.models.schemas import NOT_REPORTED, Extraction, Metric, Paper
from app.pipeline.context import RunContext

log = logging.getLogger("litlens.extractor")

BATCH_SIZE = 4
MAX_WORDS = 25
MAX_LIST = 8
_SCHEMA = strict_json_schema(ExtractorOutput)


class _BatchInvalidError(Exception):
    pass


def _short(text: str) -> str:
    text = " ".join(text.split())
    if not text or text.lower().rstrip(".") in {
        "not reported",
        "n/a",
        "none",
        "unknown",
    }:
        return NOT_REPORTED
    words = text.split(" ")
    return text if len(words) <= MAX_WORDS else " ".join(words[:MAX_WORDS]) + "…"


def _real(items: list[str]) -> list[str]:
    out = [" ".join(i.split()) for i in items]
    return [i for i in out if i and i.lower() != "not reported"][:MAX_LIST]


def normalise(e: ExtractionOut) -> Extraction:
    return Extraction(
        ref=e.ref,
        problem=_short(e.problem),
        method=_short(e.method),
        datasets=_real(e.datasets),
        metrics=[
            Metric(name=_short(m.name), value=" ".join(m.value.split())[:60])
            for m in e.metrics
            if m.name.strip() and m.value.strip()
        ][:MAX_LIST],
        key_result=_short(e.key_result),
        limitations=_short(e.limitations),
    )


def parse_batch(text: str, refs: set[int]) -> dict[int, Extraction]:
    """Validate the LLM JSON and check it covers exactly the expected refs."""
    try:
        out = ExtractorOutput.model_validate_json(text)
    except ValidationError as e:
        raise _BatchInvalidError(
            f"JSON did not match the schema ({e.error_count()} errors)"
        ) from None
    got = {e.ref: normalise(e) for e in out.extractions if e.ref in refs}
    missing = sorted(refs - got.keys())
    if missing:
        raise _BatchInvalidError(f"missing extractions for refs {missing}")
    return got


async def _extract_batch(batch: list[Paper], ctx: RunContext) -> dict[int, Extraction]:
    refs = {p.ref for p in batch}
    error_note: str | None = None
    attempts: list[tuple[bool, bool]] = [(False, False), (True, False)]
    if ctx.router.fallback_available:
        attempts.append((True, True))

    for with_note, fallback_only in attempts:
        try:
            result = await ctx.router.complete(
                "extract",
                prompt.build_messages(batch, error_note if with_note else None),
                prompt_version=prompt.PROMPT_VERSION,
                max_tokens=prompt.max_tokens(len(batch)),
                json_schema=_SCHEMA,
                schema_name="paper_extractions",
                fallback_only=fallback_only,
            )
        except LLMError as e:
            log.warning("extract batch %s: provider error %s", sorted(refs), e)
            error_note = error_note or "the request failed"
            continue
        ctx.record("extracting", result)
        try:
            return parse_batch(result.text, refs)
        except _BatchInvalidError as e:
            log.warning("extract batch %s invalid: %s", sorted(refs), e)
            error_note = str(e)

    ctx.warn(f"Could not extract details for papers {sorted(refs)}.")
    return {r: Extraction(ref=r) for r in refs}


async def extract(papers: list[Paper], ctx: RunContext) -> list[Extraction]:
    total = len(papers)
    await ctx.emit(
        "extracting",
        "started",
        f"Extracting facts from {total} papers",
        progress=(0, total),
    )
    done: dict[int, Extraction] = {}
    for start in range(0, total, BATCH_SIZE):
        batch = papers[start : start + BATCH_SIZE]
        done.update(await _extract_batch(batch, ctx))
        status = "completed" if len(done) >= total else "progress"
        verb = "Extracted" if status == "completed" else "Extracting"
        await ctx.emit(
            "extracting",
            status,
            f"{verb} {len(done)}/{total} papers",
            progress=(len(done), total),
            provider=ctx.providers_used[-1] if ctx.providers_used else None,
        )
    if total == 0:
        await ctx.emit("extracting", "skipped", "No papers to extract")
    return [done[p.ref] for p in papers]
