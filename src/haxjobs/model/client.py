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
    ToolCall,
    ToolSchema,
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
            kwargs: dict = {
                "model": self._model,
                "messages": [
                    m.model_dump(exclude_none=True) for m in request.messages
                ],
                "max_tokens": request.max_tokens,
            }
            if request.tools:
                kwargs["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.input_schema,
                        },
                    }
                    for t in request.tools
                ]
            response = await client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            finish_reason = choice.finish_reason or "stop"
            usage = None
            if response.usage:
                usage = ModelUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
            # Map provider tool calls to internal ToolCall
            tool_calls: list[ToolCall] = []
            tool_calls_unsafe = False
            msg = choice.message
            if msg.tool_calls:
                # If the response was cut off by output length and included tool calls,
                # mark them unsafe for execution
                if finish_reason == "length":
                    tool_calls_unsafe = True
                for tc in msg.tool_calls:
                    tool_calls.append(
                        ToolCall(
                            call_id=tc.id,
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        )
                    )
            return ModelResponse(
                text=msg.content or "",
                finish_reason=finish_reason,
                tool_calls=tool_calls,
                tool_calls_unsafe=tool_calls_unsafe,
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
