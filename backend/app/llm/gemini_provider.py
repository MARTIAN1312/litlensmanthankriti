"""Gemini provider (fallback). Model ID always comes from settings (GEMINI_MODEL)."""

from __future__ import annotations

from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.llm.base import (
    LLMResult,
    Message,
    PermanentError,
    RateLimitedError,
    TransientError,
)


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        *,
        thinking_level: str = "",
        timeout_s: float = 60.0,
    ) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),  # ms
        )
        # Allowed levels differ per model, so this is opt-in via GEMINI_THINKING_LEVEL.
        self._thinking_level = thinking_level.strip().upper()

    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        schema_name: str = "output",
    ) -> LLMResult:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part(text=m.content)],
            )
            for m in messages
            if m.role != "system"
        ]
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            max_output_tokens=max_tokens,
            temperature=0.2,
        )
        if json_schema is not None:
            config.response_mime_type = "application/json"
            config.response_json_schema = json_schema
        if self._thinking_level:
            config.thinking_config = types.ThinkingConfig(
                thinking_level=self._thinking_level
            )

        try:
            resp = await self._client.aio.models.generate_content(
                model=model, contents=contents, config=config
            )
        except errors.ClientError as e:
            if e.code == 429:
                raise RateLimitedError("gemini rate limited") from None
            raise PermanentError(f"gemini error {e.code}") from None
        except errors.ServerError as e:
            raise TransientError(f"gemini server error {e.code}") from None
        except TimeoutError, httpx.TimeoutException:
            raise TransientError("gemini timeout") from None
        except OSError, httpx.TransportError:
            raise TransientError(
                "gemini connection failed", reached_server=False
            ) from None

        usage = resp.usage_metadata
        tokens_in = (usage.prompt_token_count or 0) if usage else 0
        tokens_out = (
            (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
            if usage
            else 0
        )
        return LLMResult(
            text=resp.text or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider="gemini",
            model=model,
        )
