"""ModelClient protocol and OpenAI-compatible adapter."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI

from haxjobs.model.types import (
    ModelFailure,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)


class ModelClient(Protocol):
    """Async model-call boundary — one stable door for the rest of the system."""

    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure: ...


_DEFAULT_CREDENTIALS_PATH = Path.home() / ".haxjobs" / "haxjobs.toml"


class OpenAIModelClient:
    """OpenAI-compatible adapter. Reads provider config from ~/.haxjobs/haxjobs.toml."""

    def __init__(
        self,
        credentials_path: Path = _DEFAULT_CREDENTIALS_PATH,
    ) -> None:
        self._credentials_path = credentials_path
        self._client: AsyncOpenAI | None = None
        self._model: str = ""
        self._provider: str = ""

    def _ensure_client(self) -> AsyncOpenAI:
        if self._client is not None:
            return self._client
        raw = tomllib.loads(self._credentials_path.read_text())
        provider = raw.get("provider", {})
        if "model" not in provider:
            raise ValueError(
                f"provider config missing required 'model' key — check {self._credentials_path}"
            )
        self._model = provider["model"]
        self._provider = provider.get("name", "deepseek")
        self._client = AsyncOpenAI(
            api_key=provider["api_key"],
            base_url=provider.get("base_url", "https://api.deepseek.com/v1"),
            max_retries=0,
        )
        return self._client

    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure:
        try:
            client = self._ensure_client()
            response = await client.chat.completions.create(
                model=self._model,
                messages=[m.model_dump() for m in request.messages],
                max_tokens=request.max_tokens,
            )
            choice = response.choices[0]
            usage = None
            if response.usage:
                usage = ModelUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
            return ModelResponse(
                text=choice.message.content or "",
                finish_reason=choice.finish_reason or "stop",
                usage=usage,
                model=self._model,
                provider=self._provider,
            )
        except Exception as exc:
            return ModelFailure(
                error=str(exc),
                category="provider_error",
                retryable=False,
                model=getattr(self, "_model", ""),
                provider=getattr(self, "_provider", ""),
            )
