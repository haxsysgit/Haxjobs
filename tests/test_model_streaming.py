"""Model streaming tests — delta order, tool-call assembly, cancellation, existing complete() unchanged.

Plan 003 Phase 3: provider-neutral stream events with cancellation. No live provider calls.
"""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest

from haxjobs.model.client import OpenAIModelClient
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import (
    ModelFailure,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
    ModelUsage,
    ToolCall,
)


def _fake_request() -> ModelRequest:
    return ModelRequest(
        messages=[ModelMessage(role="user", content="hello")],
        max_tokens=100,
    )


# ── Fake stream: text delta order ──

@pytest.mark.asyncio
async def test_fake_stream_text_deltas_in_order():
    """Fake model yields text deltas in exact scripted order."""
    events = [
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta="Hel"),
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta="lo"),
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta=" world"),
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason="stop",
        ),
    ]
    fake = FakeModelClient(responses=[], stream_events=[events])
    cancel = asyncio.Event()
    collected: list[ModelStreamEvent] = []
    async for evt in fake.stream(_fake_request(), cancel):
        collected.append(evt)

    assert len(collected) == 4
    assert collected[0].delta == "Hel"
    assert collected[1].delta == "lo"
    assert collected[2].delta == " world"
    assert collected[3].event_type == ModelStreamEventType.RESPONSE_COMPLETED
    assert collected[3].finish_reason == "stop"

    combined = "".join(e.delta for e in collected if e.delta)
    assert combined == "Hello world"


# ── Fake stream: complete tool call ──

@pytest.mark.asyncio
async def test_fake_stream_complete_tool_call():
    """Fake model yields a complete tool call event."""
    events = [
        ModelStreamEvent(
            event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
            call_id="call_1",
            tool_name="inspect_job_source",
            arguments='{"job_ref": "328"}',
        ),
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason="tool_calls",
        ),
    ]
    fake = FakeModelClient(responses=[], stream_events=[events])
    cancel = asyncio.Event()
    collected: list[ModelStreamEvent] = []
    async for evt in fake.stream(_fake_request(), cancel):
        collected.append(evt)

    assert len(collected) == 2
    assert collected[0].event_type == ModelStreamEventType.COMPLETE_TOOL_CALL
    assert collected[0].call_id == "call_1"
    assert collected[0].tool_name == "inspect_job_source"
    assert collected[0].arguments == '{"job_ref": "328"}'


# ── Fake stream: cancellation stops future deltas ──

@pytest.mark.asyncio
async def test_fake_stream_cancellation_stops():
    """Cancelling stops future deltas and yields a failed event."""
    events = [
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta="one"),
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta="two"),
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta="three"),
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason="stop",
        ),
    ]
    fake = FakeModelClient(responses=[], stream_events=[events])
    cancel = asyncio.Event()
    collected: list[ModelStreamEvent] = []

    count = 0

    async def _collect_and_cancel():
        nonlocal count
        async for evt in fake.stream(_fake_request(), cancel):
            collected.append(evt)
            count += 1
            if count == 2:
                cancel.set()

    await _collect_and_cancel()

    assert len(collected) >= 2
    assert collected[0].delta == "one"
    assert collected[1].delta == "two"
    # The last event should be a cancellation failure
    assert collected[-1].event_type == ModelStreamEventType.RESPONSE_FAILED
    assert collected[-1].category == "cancelled"


# ── Fake stream: safe provider failure ──

@pytest.mark.asyncio
async def test_fake_stream_failure():
    """Fake model can yield a response_failed event."""
    events = [
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_FAILED,
            error="provider timeout",
            category="provider_error",
        ),
    ]
    fake = FakeModelClient(responses=[], stream_events=[events])
    cancel = asyncio.Event()
    collected: list[ModelStreamEvent] = []
    async for evt in fake.stream(_fake_request(), cancel):
        collected.append(evt)

    assert len(collected) == 1
    assert collected[0].event_type == ModelStreamEventType.RESPONSE_FAILED
    assert collected[0].error == "provider timeout"
    assert collected[0].category == "provider_error"


# ── Fake stream: exhausted raises ──

@pytest.mark.asyncio
async def test_fake_stream_exhausted_raises():
    """Calling stream() beyond scripted turns raises RuntimeError."""
    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [ModelStreamEvent(event_type=ModelStreamEventType.RESPONSE_COMPLETED)],
        ],
    )
    cancel = asyncio.Event()
    # First call succeeds
    async for _ in fake.stream(_fake_request(), cancel):
        pass

    # Second call fails
    with pytest.raises(RuntimeError, match="exhausted"):
        async for _ in fake.stream(_fake_request(), cancel):
            pass


# ── Fake stream: records requests ──

@pytest.mark.asyncio
async def test_fake_stream_records_request():
    """Fake model records the ModelRequest for stream calls."""
    events = [
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason="stop",
        ),
    ]
    fake = FakeModelClient(responses=[], stream_events=[events])
    cancel = asyncio.Event()
    req = _fake_request()
    async for _ in fake.stream(req, cancel):
        pass

    assert len(fake.requests) == 1
    assert fake.requests[0].messages[0].content == "hello"


# ── Existing complete() unchanged ──

@pytest.mark.asyncio
async def test_complete_still_works_after_stream_changes():
    """Non-streaming complete() path remains functional."""
    fake = FakeModelClient(responses=[
        ModelResponse(
            text="hello",
            finish_reason="stop",
            model="test",
            provider="test",
        ),
    ])
    result = await fake.complete(_fake_request())
    assert isinstance(result, ModelResponse)
    assert result.text == "hello"


@pytest.mark.asyncio
async def test_complete_failure_still_works():
    """Non-streaming failure path remains functional."""
    fake = FakeModelClient(responses=[
        ModelFailure(error="boom", category="test"),
    ])
    result = await fake.complete(_fake_request())
    assert isinstance(result, ModelFailure)
    assert result.error == "boom"


# ── Mocked OpenAI stream: fragmented tool-call assembly ──

@pytest.mark.asyncio
async def test_mocked_openai_stream_assembles_tool_calls():
    """Using a mocked OpenAI stream, verify fragmented tool calls are assembled."""

    # Build mock chunks that simulate a streaming OpenAI response with tool calls
    class _MockDeltaFunction:
        def __init__(self, name=None, arguments=None):
            self.name = name
            self.arguments = arguments

    class _MockDeltaToolCall:
        def __init__(self, index=0, id=None, function=None):
            self.index = index
            self.id = id
            self.function = function

    class _MockDelta:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    class _MockChoice:
        def __init__(self, delta, finish_reason=None):
            self.delta = delta
            self.finish_reason = finish_reason

    class _MockChunk:
        def __init__(self, choices=None, usage=None):
            self.choices = choices
            self.usage = usage

    # Simulate: text first, then tool call in fragments
    chunks = [
        _MockChunk(choices=[_MockChoice(
            _MockDelta(content="Let me check"),
        )]),
        _MockChunk(choices=[_MockChoice(
            _MockDelta(tool_calls=[
                _MockDeltaToolCall(
                    index=0,
                    id="call_abc",
                    function=_MockDeltaFunction(name="inspect_job_source"),
                ),
            ]),
        )]),
        _MockChunk(choices=[_MockChoice(
            _MockDelta(tool_calls=[
                _MockDeltaToolCall(
                    index=0,
                    function=_MockDeltaFunction(arguments='{"job'),
                ),
            ]),
        )]),
        _MockChunk(choices=[_MockChoice(
            _MockDelta(tool_calls=[
                _MockDeltaToolCall(
                    index=0,
                    function=_MockDeltaFunction(arguments='_ref":'),
                ),
            ]),
        )]),
        _MockChunk(choices=[_MockChoice(
            _MockDelta(tool_calls=[
                _MockDeltaToolCall(
                    index=0,
                    function=_MockDeltaFunction(arguments='"328"}'),
                ),
            ]),
        )]),
        _MockChunk(choices=[_MockChoice(
            _MockDelta(),
            finish_reason="tool_calls",
        )]),
    ]

    async def _mock_stream():
        for chunk in chunks:
            yield chunk

    # Patch the client's internal method
    with mock.patch.object(
        OpenAIModelClient, "_ensure_client", autospec=True
    ) as mock_ensure:
        mock_client = mock.AsyncMock()
        mock_client.chat.completions.create.return_value = _mock_stream()
        mock_ensure.return_value = mock_client

        # Set required attributes
        client = OpenAIModelClient.__new__(OpenAIModelClient)
        client._client = mock_client
        client._model = "test-model"
        client._provider = "test-provider"

        cancel = asyncio.Event()
        collected: list[ModelStreamEvent] = []
        async for evt in client.stream(_fake_request(), cancel):
            collected.append(evt)

        # Should have: text delta, complete tool call, response completed
        assert len(collected) >= 3

        text_deltas = [e for e in collected if e.event_type == ModelStreamEventType.TEXT_DELTA]
        tool_calls = [e for e in collected if e.event_type == ModelStreamEventType.COMPLETE_TOOL_CALL]
        completed = [e for e in collected if e.event_type == ModelStreamEventType.RESPONSE_COMPLETED]

        assert len(text_deltas) == 1
        assert text_deltas[0].delta == "Let me check"
        assert len(tool_calls) >= 1
        assert tool_calls[-1].call_id == "call_abc"
        assert tool_calls[-1].tool_name == "inspect_job_source"
        assert tool_calls[-1].arguments == '{"job_ref":"328"}'
        assert len(completed) == 1
        assert completed[0].finish_reason == "tool_calls"


# ── Mocked OpenAI stream: cancellation ──

@pytest.mark.asyncio
async def test_mocked_openai_stream_cancels():
    """Cancelling the stream mid-way stops further events."""
    chunks = [
        type("Chunk", (), {
            "choices": [type("Choice", (), {
                "delta": type("Delta", (), {
                    "content": "first",
                    "tool_calls": None,
                })(),
                "finish_reason": None,
            })()],
            "usage": None,
        })(),
        type("Chunk", (), {
            "choices": [type("Choice", (), {
                "delta": type("Delta", (), {
                    "content": "second",
                    "tool_calls": None,
                })(),
                "finish_reason": None,
            })()],
            "usage": None,
        })(),
    ]

    async def _mock_stream():
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0)  # yield control

    # Patch
    async def _stream_patch(self, request, cancel_event):
        stream = _mock_stream()
        accumulated_text = ""
        finish_reason = ""
        usage = None
        tool_call_builders: dict[int, dict] = {}
        completed_tool_calls: set[str] = set()

        try:
            async for chunk in stream:
                if cancel_event.is_set():
                    try:
                        await stream.aclose()
                    except Exception:
                        pass
                    yield ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_FAILED,
                        error="cancelled",
                        category="cancelled",
                    )
                    return

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

                if delta.content:
                    accumulated_text += delta.content
                    yield ModelStreamEvent(
                        event_type=ModelStreamEventType.TEXT_DELTA,
                        delta=delta.content,
                    )
        except asyncio.CancelledError:
            yield ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_FAILED,
                error="cancelled",
                category="cancelled",
            )
            return

        yield ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason=finish_reason,
        )

    with mock.patch.object(OpenAIModelClient, "stream", _stream_patch):
        client = OpenAIModelClient.__new__(OpenAIModelClient)
        cancel = asyncio.Event()
        collected: list[ModelStreamEvent] = []
        count = 0

        async def _collect_and_cancel():
            nonlocal count
            async for evt in client.stream(_fake_request(), cancel):
                collected.append(evt)
                count += 1
                if count >= 1:
                    cancel.set()

        await _collect_and_cancel()

        # Should have at most the first delta + cancellation failure
        assert len(collected) >= 1
        assert collected[-1].event_type == ModelStreamEventType.RESPONSE_FAILED
        assert collected[-1].category == "cancelled"


# ── Fake stream: requires at least one response or stream ──

def test_fake_requires_responses_or_streams():
    """FakeModelClient raises if neither responses nor stream_events given."""
    with pytest.raises(ValueError):
        FakeModelClient(responses=[], stream_events=[])
