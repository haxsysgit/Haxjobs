"""FakeModelClient — deterministic, no network, records requests."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from haxjobs.model.client import ModelClient
from haxjobs.model.types import (
    ModelFailure,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)


class FakeModelClient:
    """Returns ordered list of responses/failures. Never calls the network."""

    def __init__(
        self,
        responses: list[ModelResponse | ModelFailure],
        stream_events: list[list[ModelStreamEvent]] | None = None,
    ) -> None:
        if not responses and not stream_events:
            raise ValueError("FakeModelClient requires at least one response or stream")
        self._responses = responses
        self._stream_events = stream_events or []
        self._index = 0
        self._stream_index = 0
        self.requests: list[ModelRequest] = []

    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure:
        self.requests.append(request)
        if self._index >= len(self._responses):
            raise RuntimeError(
                f"FakeModelClient exhausted: {len(self._responses)} responses, "
                f"call {self._index + 1}"
            )
        result = self._responses[self._index]
        self._index += 1
        return result

    async def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]:
        """Yield scripted stream events. Supports optional per-event delay for cancellation tests."""
        self.requests.append(request)
        if self._stream_index >= len(self._stream_events):
            raise RuntimeError(
                f"FakeModelClient stream exhausted: {len(self._stream_events)} streams, "
                f"stream {self._stream_index + 1}"
            )
        events = self._stream_events[self._stream_index]
        self._stream_index += 1
        for event in events:
            if cancel_event.is_set():
                yield ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_FAILED,
                    error="cancelled",
                    category="cancelled",
                )
                return
            yield event

    @property
    def call_count(self) -> int:
        return self._index

    @property
    def stream_call_count(self) -> int:
        return self._stream_index
