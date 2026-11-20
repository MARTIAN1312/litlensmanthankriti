"""Provider-neutral LLM types (DESIGN §5)."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]
ProviderName = Literal["groq", "gemini"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    provider: str  # "groq" | "gemini" | "cache"
    model: str

    @property
    def tokens(self) -> int:
        return self.tokens_in + self.tokens_out


class LLMError(Exception):
    """Base class for provider failures. Messages never include keys or headers."""


class RateLimitedError(LLMError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(LLMError):
    """5xx, timeouts, connection problems: worth one retry.

    `reached_server=False` means the request never got there (e.g. connect/TLS
    failure), so it used no quota.
    """

    def __init__(self, message: str, *, reached_server: bool = True) -> None:
        super().__init__(message)
        self.reached_server = reached_server


class PermanentError(LLMError):
    """Bad request, auth failure, schema rejected: retrying the same call won't help."""


class InvalidOutputError(PermanentError):
    """The provider rejected the model's own output (e.g. Groq json_validate_failed).

    `failed_output` is the model's text, so a caller can try to salvage it;
    `detail` is the provider's validation message (no secrets in either).
    """

    def __init__(
        self, message: str, *, failed_output: str = "", detail: str = ""
    ) -> None:
        super().__init__(message)
        self.failed_output = failed_output
        self.detail = detail


class LLMProvider(Protocol):
    name: ProviderName

    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        schema_name: str = "output",
    ) -> LLMResult: ...


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic JSON schema adapted for strict structured output.

    Inlines `$defs`, drops `title`s, and makes every property required with
    `additionalProperties: false` (Groq strict-mode rules).
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def fix(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].rsplit("/", 1)[-1]
                return fix(copy.deepcopy(defs[name]))
            out = {k: fix(v) for k, v in node.items() if k != "title"}
            if out.get("type") == "object" and "properties" in out:
                out["required"] = list(out["properties"].keys())
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [fix(v) for v in node]
        return node

    return fix(raw)
