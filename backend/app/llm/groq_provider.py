"""Groq provider (primary). Uses JSON-schema structured output in strict mode."""

from __future__ import annotations

from typing import Any, Literal

import groq

from app.llm.base import (
    LLMResult,
    Message,
    PermanentError,
    RateLimitedError,
    TransientError,
)

ReasoningEffort = Literal["low", "medium", "high"]


def _retry_after(exc: groq.APIStatusError) -> float | None:
    raw = exc.response.headers.get("retry-after") if exc.response is not None else None
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        api_key: str,
        *,
        reasoning_effort: ReasoningEffort = "low",
        timeout_s: float = 60.0,
    ) -> None:
        # max_retries=0: the router owns retry/fallback policy (DESIGN §5).
        self._client = groq.AsyncGroq(api_key=api_key, max_retries=0, timeout=timeout_s)
        self._effort = reasoning_effort

    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        schema_name: str = "output",
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [m.as_dict() for m in messages],
            "max_completion_tokens": max_tokens,
            "temperature": 0.2,
        }
        if model.startswith("openai/gpt-oss"):
            # Reasoning tokens count toward TPM, so keep them low (DESIGN §3.4).
            kwargs["reasoning_effort"] = self._effort
            kwargs["include_reasoning"] = False
        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            }
        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except groq.RateLimitError as e:
            raise RateLimitedError("groq rate limited", _retry_after(e)) from None
        except groq.APITimeoutError:
            raise TransientError("groq timeout") from None
        except groq.APIConnectionError as e:
            # Name the root cause (e.g. a TLS certificate problem) without any secrets.
            root = e.__cause__ or e.__context__
            detail = type(root).__name__ if root else "unknown"
            if root and "CERTIFICATE_VERIFY_FAILED" in str(root):
                detail = "TLS certificate verification failed"
            raise TransientError(
                f"groq connection failed ({detail})", reached_server=False
            ) from None
        except groq.InternalServerError as e:
            raise TransientError(f"groq server error {e.status_code}") from None
        except groq.APIStatusError as e:
            raise PermanentError(f"groq error {e.status_code}") from None

        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return LLMResult(
            text=text,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            provider="groq",
            model=model,
        )
