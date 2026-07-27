"""StreamAccumulator — pure sync, testable in isolation.

Takes stream deltas, accumulates state, emits typed events.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from haxjobs.model.profiles import ProviderProfile
from haxjobs.model.types import ModelStreamEvent, ModelStreamEventType, ModelUsage


@dataclass
class StreamAccumulator:
    """Pure sync accumulator for streaming model output.

    Takes deltas from a provider stream and emits typed ModelStreamEvents.
    Zero async. Testable with plain strings. Replaces the inline state machine
    that was buried inside client.py:stream().
    """

    profile: ProviderProfile

    # Internal state
    _accumulated_text: str = ""
    _accumulated_reasoning: str = ""
    _tool_calls: dict[int, dict] = field(default_factory=dict)
    _finish_reason: str | None = None
    _model: str = ""
    _provider: str = ""

    def set_model_info(self, model: str, provider: str) -> None:
        """Set model/provider for events."""
        self._model = model
        self._provider = provider

    def feed_text(self, text: str) -> ModelStreamEvent:
        """Feed a text delta. Returns TEXT_DELTA event."""
        self._accumulated_text += text
        return ModelStreamEvent(
            event_type=ModelStreamEventType.TEXT_DELTA,
            delta=text,
            model=self._model,
            provider=self._provider,
        )

    def feed_reasoning(self, text: str) -> ModelStreamEvent | None:
        """Feed a reasoning delta. Returns THINKING_DELTA event or None."""
        if self.profile.thinking_format == "disabled":
            return None
        self._accumulated_reasoning += text
        return ModelStreamEvent(
            event_type=ModelStreamEventType.THINKING_DELTA,
            delta=text,
            model=self._model,
            provider=self._provider,
        )

    def feed_tool_call_delta(
        self, index: int, call_id: str | None, name: str | None, arguments: str | None
    ) -> None:
        """Feed a tool call delta chunk. Accumulates internally."""
        if index not in self._tool_calls:
            self._tool_calls[index] = {
                "call_id": "",
                "name": "",
                "arguments": "",
            }
        builder = self._tool_calls[index]
        if call_id:
            builder["call_id"] = call_id
        if name:
            builder["name"] = name
        if arguments:
            builder["arguments"] += arguments

    def complete_tool_calls(self, unsafe: bool) -> list[ModelStreamEvent]:
        """Emit assembled COMPLETE_TOOL_CALL events and reset state."""
        events: list[ModelStreamEvent] = []
        for idx in sorted(self._tool_calls.keys()):
            builder = self._tool_calls[idx]
            if builder["call_id"] and builder["name"] and builder["arguments"]:
                events.append(
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id=builder["call_id"],
                        tool_name=builder["name"],
                        arguments=builder["arguments"],
                        tool_calls_unsafe=unsafe,
                        model=self._model,
                        provider=self._provider,
                    )
                )
        self._tool_calls = {}
        return events

    def feed_finish(self, reason: str) -> None:
        """Set finish reason."""
        self._finish_reason = reason or "stop"

    def done_event(self, usage: ModelUsage | None) -> ModelStreamEvent:
        """Build the terminal RESPONSE_COMPLETED event."""
        return ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason=self._finish_reason or "stop",
            usage=usage,
            model=self._model,
            provider=self._provider,
        )

    def failed_event(self, error: str, category: str) -> ModelStreamEvent:
        """Build a RESPONSE_FAILED event."""
        return ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_FAILED,
            error=error,
            category=category,
            model=self._model,
            provider=self._provider,
        )

    @property
    def accumulated_text(self) -> str:
        return self._accumulated_text

    @property
    def accumulated_reasoning(self) -> str:
        return self._accumulated_reasoning

    @property
    def finish_reason(self) -> str:
        return self._finish_reason or "stop"

    @property
    def has_tool_calls(self) -> bool:
        return any(
            b["call_id"] and b["name"] and b["arguments"]
            for b in self._tool_calls.values()
        )
