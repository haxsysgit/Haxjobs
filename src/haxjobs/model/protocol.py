"""ModelClient protocol — what agent_core sees, a sealed provider boundary."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from haxjobs.model.types import ModelRequest, ModelResponse, ModelStreamEvent


@runtime_checkable
class ModelClient(Protocol):
    """What agent_core sees — a sealed provider boundary.

    Implementations: GenericAdapter (real), FakeModelClient (tests).
    """

    async def complete(self, request: ModelRequest) -> ModelResponse: ...

    def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]: ...
