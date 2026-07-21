"""ModelClient protocol and OpenAI-compatible adapter."""

from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path
from typing import AsyncIterator, Protocol

from openai import AsyncOpenAI

from haxjobs.model.types import (
    ModelFailure,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
    ModelUsage,
    ToolCall,
    ToolSchema,
)


class ModelClient(Protocol):
    """Async model-call boundary — one stable door for the rest of the system."""

    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure: ...

    def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]: ...


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

    async def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]:
        """Stream model output as ModelStreamEvent sequence.

        Yields text_delta, complete_tool_call (when fully assembled),
        response_completed, or response_failed events.
        Stops and closes the provider stream when cancellation is set.
        """
        try:
            client = self._ensure_client()
            kwargs: dict = {
                "model": self._model,
                "messages": [
                    m.model_dump(exclude_none=True) for m in request.messages
                ],
                "max_tokens": request.max_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
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

            stream = await client.chat.completions.create(**kwargs)
            accumulated_text = ""
            finish_reason = ""
            usage = None
            # Accumulate tool calls by index
            tool_call_builders: dict[int, dict] = {}

            try:
                async for chunk in stream:
                    if cancel_event.is_set():
                        # Stop consuming, close the stream
                        await stream.close()
                        yield ModelStreamEvent(
                            event_type=ModelStreamEventType.RESPONSE_FAILED,
                            error="cancelled",
                            category="cancelled",
                            model=self._model,
                            provider=self._provider,
                        )
                        return

                    if not chunk.choices:
                        # Usage chunk may have no choices
                        if chunk.usage:
                            usage = ModelUsage(
                                prompt_tokens=chunk.usage.prompt_tokens,
                                completion_tokens=chunk.usage.completion_tokens,
                                total_tokens=chunk.usage.total_tokens,
                            )
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                    # Text delta
                    if delta.content:
                        accumulated_text += delta.content
                        yield ModelStreamEvent(
                            event_type=ModelStreamEventType.TEXT_DELTA,
                            delta=delta.content,
                            model=self._model,
                            provider=self._provider,
                        )

                    # Tool call deltas — accumulate only, emit after loop
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_call_builders:
                                tool_call_builders[idx] = {
                                    "call_id": "",
                                    "name": "",
                                    "arguments": "",
                                }
                            builder = tool_call_builders[idx]
                            if tc_delta.id:
                                builder["call_id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    builder["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    builder["arguments"] += tc_delta.function.arguments

            except asyncio.CancelledError:
                # Task was cancelled externally — close the stream
                try:
                    await stream.close()
                except Exception:
                    pass
                yield ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_FAILED,
                    error="cancelled",
                    category="cancelled",
                    model=self._model,
                    provider=self._provider,
                )
                return

            # Emit any remaining tool calls that have arguments.
            # Emit assembled tool calls even when the response was truncated (finish_reason == "length"),
            # but mark them with tool_calls_unsafe=True so the runtime can reject them.
            unsafe = finish_reason == "length"
            for idx, builder in tool_call_builders.items():
                if (
                    builder["call_id"]
                    and builder["name"]
                    and builder["arguments"]
                ):
                    yield ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id=builder["call_id"],
                        tool_name=builder["name"],
                        arguments=builder["arguments"],
                        tool_calls_unsafe=unsafe,
                        model=self._model,
                        provider=self._provider,
                    )

            yield ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason=finish_reason,
                usage=usage,
                model=self._model,
                provider=self._provider,
            )

        except Exception as exc:
            yield ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_FAILED,
                error=str(exc),
                category="provider_error",
                model=getattr(self, "_model", ""),
                provider=getattr(self, "_provider", ""),
            )
