"""Turn runtime tests — streaming, tool calls, events, cancellation, error recovery.

Plan 003 Phase 5: domain-free bounded streaming model and tool turn runtime.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.messages import (
    AssistantMessage,
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
)
from haxjobs.agent_core.tools import ToolDefinition, ToolRegistry
from haxjobs.agent_core.turn import TurnExitReason, TurnResult, run_turn
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import (
    ModelMessage,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)


# ── Helpers ──

def _fake_stream(text: str, finish: str = "stop") -> list[ModelStreamEvent]:
    """Script a simple text-only stream."""
    return [
        ModelStreamEvent(event_type=ModelStreamEventType.TEXT_DELTA, delta=text),
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason=finish,
        ),
    ]


def _fake_stream_with_tool(
    call_id: str, tool_name: str, arguments: str, final_text: str
) -> list[list[ModelStreamEvent]]:
    """Script a tool-call stream then final text stream (two model calls)."""
    return [
        [
            ModelStreamEvent(
                event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                call_id=call_id,
                tool_name=tool_name,
                arguments=arguments,
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="tool_calls",
            ),
        ],
        [
            ModelStreamEvent(
                event_type=ModelStreamEventType.TEXT_DELTA, delta=final_text
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="stop",
            ),
        ],
    ]


def _fake_registry() -> tuple[ToolRegistry, tuple[str, ...]]:
    """Simple tool registry for testing."""
    from pydantic import BaseModel

    class _TestInput(BaseModel):
        value: str

    class _TestOutput(BaseModel):
        ok: bool

    class _TestOutput(BaseModel):
        ok: bool

    registry = ToolRegistry()

    async def handler(input_obj):
        return {"ok": True, "data": f"processed: {input_obj.value}"}

    registry.register(
        ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_model=_TestInput,
            output_model=_TestOutput,
            handler=handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="crash_tool",
            description="A tool that crashes",
            input_model=_TestInput,
            output_model=_TestOutput,
            handler=lambda x: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    )
    return registry, ("test_tool", "crash_tool")


def _fake_emit(events: list[LiveEvent]):
    """Create an emitter that collects events."""

    def emit(event: LiveEvent) -> None:
        events.append(event)

    return emit


# ── Text-only response ──

@pytest.mark.asyncio
async def test_text_only_response():
    """A simple text response from the model produces a completed turn."""
    events: list[LiveEvent] = []
    fake = FakeModelClient(
        responses=[],
        stream_events=[_fake_stream("Hello, how can I help?")],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="You are helpful.",
        context_messages=[],
        history=[],
        tool_registry=ToolRegistry(),
        active_tools=(),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    assert "Hello, how can I help?" in result.final_text
    assert result.model_steps == 1
    assert result.tool_starts == 0

    # Verify new messages: one assistant message
    assert len(result.new_messages) == 1
    assert result.new_messages[0].kind == "assistant"
    assert result.new_messages[0].status == "complete"


# ── Model → tool → model response ──

@pytest.mark.asyncio
async def test_model_tool_model_response():
    """Model requests a tool, gets result, then responds with final text."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    fake = FakeModelClient(
        responses=[],
        stream_events=_fake_stream_with_tool(
            "call_1",
            "test_tool",
            '{"value": "hello"}',
            "The tool processed 'hello'. What next?",
        ),
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    assert "What next?" in result.final_text
    assert result.model_steps == 2
    assert result.tool_starts == 1

    # Verify new messages: assistant(tool_calls), tool_call, tool_result, assistant(final)
    kinds = [m.kind for m in result.new_messages]
    assert kinds == ["assistant", "tool_call", "tool_result", "assistant"]


# ── Event ordering ──

@pytest.mark.asyncio
async def test_event_ordering():
    """Events are emitted in correct order during a tool-call turn."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    fake = FakeModelClient(
        responses=[],
        stream_events=_fake_stream_with_tool(
            "call_1",
            "test_tool",
            '{"value": "x"}',
            "Done.",
        ),
    )
    cancel = asyncio.Event()

    await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    event_types = [e.event_type for e in events]
    # Expected: turn_started, assistant_started, tool_requested, assistant_completed,
    # tool_started, tool_completed, assistant_started, assistant_delta,
    # assistant_completed, turn_completed
    assert LiveEventType.TURN_STARTED in event_types
    assert LiveEventType.ASSISTANT_STARTED in event_types
    assert LiveEventType.TOOL_REQUESTED in event_types
    assert LiveEventType.TOOL_STARTED in event_types
    assert LiveEventType.TOOL_COMPLETED in event_types
    assert LiveEventType.ASSISTANT_DELTA in event_types
    assert LiveEventType.ASSISTANT_COMPLETED in event_types
    assert LiveEventType.TURN_COMPLETED in event_types

    # Verify tool_requested comes before tool_started
    req_idx = event_types.index(LiveEventType.TOOL_REQUESTED)
    start_idx = event_types.index(LiveEventType.TOOL_STARTED)
    assert req_idx < start_idx

    # tool_completed comes after tool_started
    comp_idx = event_types.index(LiveEventType.TOOL_COMPLETED)
    assert start_idx < comp_idx

    # turn_completed is the last event
    assert event_types[-1] == LiveEventType.TURN_COMPLETED


# ── Canonical tool call and result messages ──

@pytest.mark.asyncio
async def test_canonical_tool_call_and_result_messages():
    """New messages include canonical ToolCallMessage and ToolResultMessage."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    fake = FakeModelClient(
        responses=[],
        stream_events=_fake_stream_with_tool(
            "call_abc",
            "test_tool",
            '{"value": "test"}',
            "Done.",
        ),
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    tool_calls = [m for m in result.new_messages if m.kind == "tool_call"]
    tool_results = [m for m in result.new_messages if m.kind == "tool_result"]

    assert len(tool_calls) == 1
    assert tool_calls[0].call_id == "call_abc"
    assert tool_calls[0].tool_name == "test_tool"
    assert tool_calls[0].arguments == '{"value": "test"}'

    assert len(tool_results) == 1
    assert tool_results[0].call_id == "call_abc"
    assert tool_results[0].tool_name == "test_tool"
    assert tool_results[0].ok is True


# ── Malformed arguments recover ──

@pytest.mark.asyncio
async def test_malformed_arguments_recover():
    """Model calling tool with malformed JSON still completes — tool fails gracefully."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c1",
                    tool_name="test_tool",
                    arguments="{bad json",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="Recovered."
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    # Tool result should show failure
    tool_results = [m for m in result.new_messages if m.kind == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0].ok is False
    assert tool_results[0].error_code == "malformed_arguments"


# ── Handler error recovers ──

@pytest.mark.asyncio
async def test_handler_error_recovers():
    """A tool whose handler throws does not crash the turn."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c1",
                    tool_name="crash_tool",
                    arguments='{"value": "x"}',
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="Recovered."
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    tool_results = [m for m in result.new_messages if m.kind == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0].ok is False
    assert tool_results[0].error_code == "handler_error"


# ── Model-step limit ──

@pytest.mark.asyncio
async def test_model_step_limit():
    """Turn stops after max_model_steps even if model keeps requesting tools."""
    events: list[LiveEvent] = []
    registry, active = _fake_registry()

    # Each stream returns a tool call — model never gives final text
    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c1",
                    tool_name="test_tool",
                    arguments='{"value": "1"}',
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c2",
                    tool_name="test_tool",
                    arguments='{"value": "2"}',
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=active,
        cancel_event=cancel,
        emit=_fake_emit(events),
        max_model_steps=2,
    )

    assert result.exit_reason == TurnExitReason.LIMIT_REACHED
    assert result.model_steps == 2


# ── Cancellation during text streaming (real mid-stream) ──

@pytest.mark.asyncio
async def test_cancellation_during_text_streaming_mid_stream():
    """Setting cancel_event mid-stream via delayed fake model returns INTERRUPTED."""
    events: list[LiveEvent] = []
    cancel = asyncio.Event()

    # Use delayed fake model so we have time to cancel mid-stream
    fake = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="Hel",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="lo",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta=" world",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        delay_ms=50,
    )

    async def _cancel_soon():
        await asyncio.sleep(0.06)  # Cancel after first delta, before third
        cancel.set()

    cancel_task = asyncio.create_task(_cancel_soon())

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=ToolRegistry(),
        active_tools=(),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    await cancel_task

    assert result.exit_reason == TurnExitReason.INTERRUPTED
    interrupted_events = [e for e in events if e.event_type == LiveEventType.TURN_INTERRUPTED]
    assert len(interrupted_events) >= 1


# ── Cancellation while waiting for tool task ──

@pytest.mark.asyncio
async def test_cancellation_while_waiting_for_tool():
    """Cancelling while a slow tool is executing cancels the tool task."""
    from pydantic import BaseModel

    events: list[LiveEvent] = []
    registry = ToolRegistry()

    class _SlowInput(BaseModel):
        value: str

    class _SlowOutput(BaseModel):
        ok: bool

    async def slow_handler(input_obj):
        await asyncio.sleep(10)  # would take 10 seconds
        return {"ok": True}

    registry.register(
        ToolDefinition(
            name="slow_tool",
            description="slow",
            input_model=_SlowInput,
            output_model=_SlowOutput,
            handler=slow_handler,
        )
    )

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c1",
                    tool_name="slow_tool",
                    arguments='{"value": "test"}',
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    async def _cancel_soon():
        await asyncio.sleep(0.05)
        cancel.set()

    async def _run_and_cancel():
        task = asyncio.create_task(
            run_turn(
                session_id="s1",
                turn_id="t1",
                model=fake,
                system_prompt="sys",
                context_messages=[],
                history=[],
                tool_registry=registry,
                active_tools=("slow_tool",),
                cancel_event=cancel,
                emit=_fake_emit(events),
            )
        )
        await asyncio.sleep(0.05)
        cancel.set()
        return await task

    result = await _run_and_cancel()

    assert result.exit_reason == TurnExitReason.INTERRUPTED


# ── Provider failure after partial text ──

@pytest.mark.asyncio
async def test_provider_failure_after_partial_text():
    """Provider failure mid-stream returns failed status with partial text."""
    events: list[LiveEvent] = []

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="Partial",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_FAILED,
                    error="connection reset",
                    category="provider_error",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=ToolRegistry(),
        active_tools=(),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.MODEL_FAILED
    assert "Partial" in result.final_text or result.final_text == "Partial"
    # Should have an interrupted assistant message
    assistant_msgs = [m for m in result.new_messages if m.kind == "assistant"]
    assert len(assistant_msgs) >= 1
    assert assistant_msgs[-1].status in ("interrupted", "failed")


# ── History projection includes prior turns ──

@pytest.mark.asyncio
async def test_history_includes_prior_turns():
    """Prior canonical history is projected into the model request."""
    events: list[LiveEvent] = []
    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t0", content="previous question"),
        AssistantMessage(
            message_id="a1", turn_id="t0", content="previous answer", status="complete"
        ),
    ]

    fake = FakeModelClient(
        responses=[],
        stream_events=[_fake_stream("New answer.")],
    )
    cancel = asyncio.Event()

    await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=history,
        tool_registry=ToolRegistry(),
        active_tools=(),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    # The stream request should have contained the prior history
    assert len(fake.requests) == 1
    request_messages = fake.requests[0].messages
    roles = [m.role for m in request_messages]
    assert "user" in roles
    assert "assistant" in roles


# ── Regression: unsafe tool calls rejected (F1) ──

@pytest.mark.asyncio
async def test_unsafe_tool_calls_rejected():
    """COMPLETE_TOOL_CALL with tool_calls_unsafe=True is not dispatched."""
    events: list[LiveEvent] = []
    registry = ToolRegistry()

    from pydantic import BaseModel

    class _DummyInput(BaseModel):
        value: str

    class _DummyOutput(BaseModel):
        ok: bool

    async def dummy_handler(input_obj):
        return {"ok": True, "data": input_obj.value}

    registry.register(
        ToolDefinition(
            name="dummy",
            description="a dummy tool",
            input_model=_DummyInput,
            output_model=_DummyOutput,
            handler=dummy_handler,
        )
    )

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="unsafe_1",
                    tool_name="dummy",
                    arguments='{"value": "should not execute"}',
                    tool_calls_unsafe=True,
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="length",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=("dummy",),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    # No tool calls were dispatched — only assistant message
    tool_msgs = [m for m in result.new_messages if m.kind in ("tool_call", "tool_result")]
    assert len(tool_msgs) == 0

    # TOOL_FAILED with tool_calls_unsafe should have been emitted
    tool_failed_events = [e for e in events if e.event_type == LiveEventType.TOOL_FAILED]
    assert len(tool_failed_events) >= 1
    assert tool_failed_events[0].error_code == "tool_calls_unsafe"


# ── Regression: single TURN_FAILED emission (F2) ──

@pytest.mark.asyncio
async def test_single_turn_failed_emission():
    """RESPONSE_FAILED path emits TURN_FAILED exactly once."""
    events: list[LiveEvent] = []

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_FAILED,
                    error="provider error",
                    category="provider_error",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=ToolRegistry(),
        active_tools=(),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.MODEL_FAILED
    turn_failed_events = [e for e in events if e.event_type == LiveEventType.TURN_FAILED]
    assert len(turn_failed_events) == 1, (
        f"Expected exactly 1 TURN_FAILED, got {len(turn_failed_events)}"
    )


# ── Regression: responsive tool cancellation (F3) ──

@pytest.mark.asyncio
async def test_responsive_tool_cancellation():
    """Tool dispatch is cancelled promptly when cancel_event is set mid-execution."""
    import time as time_mod
    from pydantic import BaseModel

    events: list[LiveEvent] = []
    registry = ToolRegistry()

    class _SlowInput(BaseModel):
        value: str

    class _SlowOutput(BaseModel):
        ok: bool

    async def slow_handler(input_obj):
        await asyncio.sleep(5)  # long enough to be interrupted
        return {"ok": True}

    registry.register(
        ToolDefinition(
            name="slow",
            description="slow",
            input_model=_SlowInput,
            output_model=_SlowOutput,
            handler=slow_handler,
        )
    )

    fake = FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                    call_id="c1",
                    tool_name="slow",
                    arguments='{"value": "test"}',
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="tool_calls",
                ),
            ],
        ],
    )
    cancel = asyncio.Event()

    start = time_mod.monotonic()

    async def _run_with_cancel():
        task = asyncio.create_task(
            run_turn(
                session_id="s1",
                turn_id="t1",
                model=fake,
                system_prompt="sys",
                context_messages=[],
                history=[],
                tool_registry=registry,
                active_tools=("slow",),
                cancel_event=cancel,
                emit=_fake_emit(events),
            )
        )
        await asyncio.sleep(0.05)
        cancel.set()
        return await task

    result = await _run_with_cancel()
    elapsed = time_mod.monotonic() - start

    assert result.exit_reason == TurnExitReason.INTERRUPTED
    # Must complete within 2 seconds — proves cancellation didn't wait for 5s tool
    assert elapsed < 2.0, f"Cancellation took {elapsed:.2f}s, expected < 2s"


# ── Regression: QUEUED exit reason exists and is not INTERRUPTED ──

def test_queued_reason_is_distinct():
    """QUEUED is a distinct exit reason, not the same as INTERRUPTED."""
    assert TurnExitReason.QUEUED == "queued"
    assert TurnExitReason.QUEUED != TurnExitReason.INTERRUPTED


# ── Regression: active_schemas failure caught and returned as MODEL_FAILED ──

@pytest.mark.asyncio
async def test_active_schemas_failure_returns_model_failed():
    """If active_schemas raises ValueError, the turn returns MODEL_FAILED."""
    events: list[LiveEvent] = []
    registry = ToolRegistry()

    fake = FakeModelClient(
        stream_events=[_fake_stream("Should not be called.")],
    )
    cancel = asyncio.Event()

    result = await run_turn(
        session_id="s1",
        turn_id="t1",
        model=fake,
        system_prompt="sys",
        context_messages=[],
        history=[],
        tool_registry=registry,
        active_tools=("nonexistent_tool",),
        cancel_event=cancel,
        emit=_fake_emit(events),
    )

    assert result.exit_reason == TurnExitReason.MODEL_FAILED
    assert "active tool" in result.safe_failure.lower()
    turn_failed_events = [e for e in events if e.event_type == LiveEventType.TURN_FAILED]
    assert len(turn_failed_events) == 1


# ── Regression: deterministic abort race — Escape right after Enter ──

@pytest.mark.asyncio
async def test_abort_before_turn_clears_cancel():
    """If abort() sets cancel_event before _run_turn clears it, the turn is INTERRUPTED.

    This is tested through the session layer where the window between prompt()
    scheduling _run_turn and the clear() call is meaningful."""
    from haxjobs.agent_core.session import AgentSession
    from haxjobs.agent_core.session_store import SessionStore

    store = SessionStore(":memory:")
    store.create_session("s1")

    # Use a delayed fake model so the stream doesn't finish instantly
    session = AgentSession(
        session_id="s1",
        session_store=store,
        model=FakeModelClient(
            stream_events=[
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.TEXT_DELTA, delta="Hello",
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="stop",
                    ),
                ],
            ],
            delay_ms=200,
            repeat=True,
        ),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    # Schedule a prompt and abort immediately
    prompt_task = asyncio.create_task(session.prompt("hello"))
    await asyncio.sleep(0)  # yield to let prompt() schedule _run_turn
    session.abort()

    result = await prompt_task
    assert result.exit_reason == TurnExitReason.INTERRUPTED


# ── Regression: pending-turn race — no gap between settled and pending ──

@pytest.mark.asyncio
async def test_pending_turn_no_gap():
    """When a pending message is ready, _busy never goes False between turns."""
    from haxjobs.agent_core.session import AgentSession
    from haxjobs.agent_core.session_store import SessionStore

    store = SessionStore(":memory:")
    store.create_session("s1")

    # Use repeated streams so multiple turns work
    model = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="ok",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        repeat=True,
    )

    session = AgentSession(
        session_id="s1",
        session_store=store,
        model=model,
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    busy_snaps: list[bool] = []

    async def _monitor():
        for _ in range(20):
            busy_snaps.append(session._busy)
            await asyncio.sleep(0.005)

    # Start a turn, send a second message while busy, then monitor
    t1 = asyncio.create_task(session.prompt("first"))
    await asyncio.sleep(0.02)  # let the turn start

    # Send second message (will become pending)
    await session.prompt("second")

    monitor = asyncio.create_task(_monitor())
    await t1  # wait for first turn to finish and pending to start
    await asyncio.sleep(0.1)
    monitor.cancel()
    try:
        await monitor
    except asyncio.CancelledError:
        pass

    # _busy should stay True once it becomes True (no gap)
    # Skip initial samples before the first turn started
    found_true = False
    for i, v in enumerate(busy_snaps):
        if v:
            found_true = True
        if found_true and not v:
            pytest.fail(f"_busy was False at snap {i} after it became True — gap detected")
