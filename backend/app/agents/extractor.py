"""Extractor agent (SRS FR-13, DESIGN §3.4): papers -> schema-validated facts.

Per batch of ~4 papers:
1. primary route (router already falls back to Gemini on provider errors)
2. same again with the validation error appended
3. fallback provider only (if configured)
4. "Not reported" placeholders, so one bad batch never breaks the run
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.llm.base import InvalidOutputError, LLMError, LLMResult, strict_json_schema
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


_STR_FIELDS = ("problem", "method", "key_result", "limitations")


def _as_text(v: object) -> str:
    if v is None:
        return NOT_REPORTED
    if isinstance(v, list):
        return "; ".join(str(x) for x in v) or NOT_REPORTED
    return str(v)


def coerce(data: object) -> dict[str, object]:
    """Repair common near-misses before strict validation.

    e.g. `"datasets": "Not reported"` -> `[]`, a single metric object -> a list,
    unknown keys dropped. Values are still re-validated by Pydantic afterwards.
    """
    items = data.get("extractions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise _BatchInvalidError("expected an object with an 'extractions' list")
    fixed: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            ref = int(it.get("ref"))  # type: ignore[arg-type]
        except TypeError, ValueError:
            continue
        ds = it.get("datasets")
        if isinstance(ds, str):
            ds = [] if _short(ds) == NOT_REPORTED else [ds]
        elif not isinstance(ds, list):
            ds = []
        ms = it.get("metrics")
        if isinstance(ms, dict):
            ms = [ms]
        elif not isinstance(ms, list):
            ms = []
        metrics = [
            {"name": str(m.get("name", "")), "value": str(m.get("value", ""))}
            for m in ms
            if isinstance(m, dict)
        ]
        row: dict[str, object] = {
            "ref": ref,
            "datasets": [str(d) for d in ds],
            "metrics": metrics,
        }
        for f in _STR_FIELDS:
            row[f] = _as_text(it.get(f))
        fixed.append(row)
    return {"extractions": fixed}


def parse_batch(text: str, refs: set[int]) -> dict[int, Extraction]:
    """Parse (leniently) and validate the LLM JSON; returns the refs it covers."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise _BatchInvalidError("the answer was not valid JSON") from None
    try:
        out = ExtractorOutput.model_validate(coerce(data))
    except ValidationError as e:
        raise _BatchInvalidError(
            f"JSON did not match the schema ({e.error_count()} errors)"
        ) from None
    return {e.ref: normalise(e) for e in out.extractions if e.ref in refs}


async def _extract_batch(batch: list[Paper], ctx: RunContext) -> dict[int, Extraction]:
    got: dict[int, Extraction] = {}
    error_note: str | None = None
    attempts: list[tuple[bool, bool]] = [(False, False), (True, False)]
    if ctx.router.fallback_available:
        attempts.append((True, True))

    for with_note, fallback_only in attempts:
        remaining = [p for p in batch if p.ref not in got]
        if not remaining:
            break
        refs = {p.ref for p in remaining}
        text: str | None = None
        try:
            result = await ctx.router.complete(
                "extract",
                prompt.build_messages(remaining, error_note if with_note else None),
                prompt_version=prompt.PROMPT_VERSION,
                max_tokens=prompt.max_tokens(len(remaining)),
                json_schema=_SCHEMA,
                schema_name="paper_extractions",
                fallback_only=fallback_only,
            )
            ctx.record("extracting", result)
            text = result.text
        except InvalidOutputError as e:
            # The provider rejected the model's JSON but returned it: try to salvage.
            log.warning("extract batch %s: %s", sorted(refs), e)
            text = e.failed_output or None
            error_note = e.detail or "the JSON did not match the schema"
            if text:
                # A rejected generation still used quota; the 400 has no usage numbers,
                # so count an estimate (≈ 4 chars per token) to keep stats honest.
                prompt_chars = sum(
                    len(m.content) for m in prompt.build_messages(remaining)
                )
                ctx.record(
                    "extracting",
                    LLMResult(
                        text,
                        prompt_chars // 4,
                        len(text) // 4,
                        "groq",
                        ctx.router.model_for("extract"),
                    ),
                )
        except LLMError as e:
            log.warning("extract batch %s: provider error %s", sorted(refs), e)
            error_note = error_note or "the request failed"
            continue
        if text is None:
            continue
        try:
            got.update(parse_batch(text, refs))
        except _BatchInvalidError as e:
            log.warning("extract batch %s invalid: %s", sorted(refs), e)
            error_note = str(e)
            continue
        missing = sorted(refs - got.keys())
        if missing:
            error_note = f"missing extractions for refs {missing}"

    failed = sorted({p.ref for p in batch} - got.keys())
    if failed:
        ctx.failed_extractions.update(failed)
        ctx.warn(f"Could not extract details for papers {failed}.")
        got.update({r: Extraction(ref=r) for r in failed})
    return got


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
