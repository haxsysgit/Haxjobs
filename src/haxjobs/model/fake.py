"""FakeModelClient — deterministic, no network, records requests."""

from haxjobs.model.client import ModelClient
from haxjobs.model.types import ModelFailure, ModelRequest, ModelResponse


class FakeModelClient:
    """Returns ordered list of responses/failures. Never calls the network."""

    def __init__(self, responses: list[ModelResponse | ModelFailure]) -> None:
        if not responses:
            raise ValueError("FakeModelClient requires at least one response")
        self._responses = responses
        self._index = 0
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

    @property
    def call_count(self) -> int:
        return self._index
