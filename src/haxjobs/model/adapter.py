"""GenericAdapter — flag-driven OpenAI-compatible provider adapter.

Implements ModelClient. Reads ProviderProfile flags, never branches on
provider name (except one flag check for thinking format chunk attribute).
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from openai import AsyncOpenAI

from haxjobs.model.protocol import ModelClient
from haxjobs.model.profiles import ProviderProfile
from haxjobs.model.provider import ProviderConfig
from haxjobs.model.schemas import tools_to_openai_schemas
from haxjobs.model.streaming import StreamAccumulator
from haxjobs.model.types import (
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelUsage,
    ToolCall,
)


class GenericAdapter:
    """Flag-driven OpenAI-compatible adapter. Never branches on provider name."""

    def __init__(self, config: ProviderConfig, profile: ProviderProfile) -> None:
        self._config = config
        self._profile = profile
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=0,
        )

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def provider_name(self) -> str:
        return self._config.provider

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Non-streaming model call."""
        kwargs = self._build_params(request, stream=False)
        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise exc

        choice = response.choices[0]
        finish_reason = choice.finish_reason or "stop"
        usage = None
        if response.usage:
            usage = ModelUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        # Tool calls
        tool_calls: list[ToolCall] = []
        tool_calls_unsafe = finish_reason == "length"
        msg = choice.message
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        # Reasoning content (DeepSeek thinking mode)
        reasoning_content = ""
        if self._profile.requires_reasoning_preservation:
            reasoning_content = getattr(msg, "reasoning_content", "") or ""

        return ModelResponse(
            text=msg.content or "",
            finish_reason=finish_reason,
            tool_calls=tool_calls,
            tool_calls_unsafe=tool_calls_unsafe,
            usage=usage,
            model=self._config.model,
            provider=self._config.provider,
            reasoning_content=reasoning_content,
        )

    async def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]:
        """Streaming model call with cancellation support."""
        params = self._build_params(request, stream=True)
        if self._profile.supports_stream_options:
            params["stream_options"] = {"include_usage": True}

        try:
            stream = await self._client.chat.completions.create(**params)
        except Exception as exc:
            yield ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_FAILED,
                error=str(exc),
                category="provider_error",
                model=self._config.model,
                provider=self._config.provider,
            )
            return

        accumulator = StreamAccumulator(profile=self._profile)
        accumulator.set_model_info(self._config.model, self._config.provider)
        usage: ModelUsage | None = None

        try:
            async for chunk in stream:
                if cancel_event.is_set():
                    try:
                        await stream.close()
                    except (AttributeError, NotImplementedError):
                        await stream.aclose()
                    yield accumulator.failed_event("cancelled", "cancelled")
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
                    accumulator.feed_finish(choice.finish_reason)

                # Text delta
                if delta.content:
                    yield accumulator.feed_text(delta.content)

                # Reasoning content (DeepSeek thinking mode)
                if self._profile.thinking_format == "deepseek":
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        event = accumulator.feed_reasoning(reasoning)
                        if event is not None:
                            yield event

                # Tool call deltas
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        accumulator.feed_tool_call_delta(
                            index=tc_delta.index,
                            call_id=tc_delta.id or None,
                            name=tc_delta.function.name if tc_delta.function else None,
                            arguments=tc_delta.function.arguments if tc_delta.function else None,
                        )

        except asyncio.CancelledError:
            try:
                await stream.close()
            except (AttributeError, NotImplementedError):
                await stream.aclose()
            yield accumulator.failed_event("cancelled", "cancelled")
            return

        # Emit assembled tool calls
        unsafe = accumulator.finish_reason == "length"
        for event in accumulator.complete_tool_calls(unsafe):
            yield event

        # Emit completion
        yield accumulator.done_event(usage)

    def _build_params(self, request: ModelRequest, *, stream: bool) -> dict:
        """Build provider params from request and profile flags."""
        params: dict = {
            "model": self._config.model,
            "messages": [
                m.model_dump(exclude_none=True) for m in request.messages
            ],
            self._profile.max_tokens_field: request.max_tokens,
            "stream": stream,
        }

        if request.tools:
            params["tools"] = tools_to_openai_schemas(request.tools)

        if self._profile.reasoning_effort_field:
            params[self._profile.reasoning_effort_field] = "high"

        if self._profile.extra_body:
            params["extra_body"] = self._profile.extra_body

        return params
