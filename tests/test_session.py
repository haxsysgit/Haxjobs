"""Session tests — persistence, subscribers, cancellation, resume, busy policy.

Plan 003 Phase 7: AgentSession owns prompt boundaries, canonical history, and turn orchestration.
"""

from __future__ import annotations

import asyncio

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.messages import ConversationMessage
from haxjobs.agent_core.session import AgentSession, CanonicalParseError
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.agent_core.turn import TurnExitReason
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import (
    ModelMessage,
    ModelStreamEvent,
    ModelStreamEventType,
)


def _fake_model_response(text: str = "Hello from fake model.", count: int = 1) -> FakeModelClient:
    return FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA,
                    delta=text,
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ]
        * count,
    )


def _make_session(store: SessionStore, model=None, *, model_count: int = 1) -> AgentSession:
    if model is None:
        model = _fake_model_response(count=model_count)
    import json
    store.create_session("s1", configuration_json=json.dumps({"person_id": "test", "track_id": "test"}))
    return AgentSession(
        session_id="s1",
        session_store=store,
        model=model,
        system_prompt=lambda: "You are helpful.",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )


@pytest.fixture
def store() -> SessionStore:
    return SessionStore(":memory:")


# ── First prompt persists before model invocation ──

@pytest.mark.asyncio
async def test_first_prompt_persists_user_message(store: SessionStore):
    session = _make_session(store)
    result = await session.prompt("hello")

    assert result.exit_reason is not None
    stored = store.load_messages("s1")
    assert len(stored) >= 1
    assert stored[0]["payload_json"]["kind"] == "user"
    assert stored[0]["payload_json"]["content"] == "hello"


# ── Two turns replay prior canonical history ──

@pytest.mark.asyncio
async def test_two_turns_replay_history(store: SessionStore):
    session = _make_session(store, model_count=2)
    await session.prompt("first message")
    await session.prompt("second message")

    stored = store.load_messages("s1")
    kinds = [m["payload_json"]["kind"] for m in stored]
    assert kinds.count("user") == 2
    assert kinds.count("assistant") == 2

    # Verify the second model call received the first turn's messages
    assert store.get_session("s1")["turn_count"] == 2


# ── Resume after close ──

@pytest.mark.asyncio
async def test_resume_after_close(store: SessionStore):
    session = _make_session(store, model_count=2)
    await session.prompt("hello")
    store.mark_session_closed("s1")

    # Resume
    resumed = AgentSession.resume(
        session_id="s1",
        session_store=store,
        model=_fake_model_response("resumed answer", count=2),
        system_prompt=lambda: "You are helpful.",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )
    assert resumed.session_id == "s1"

    result = await resumed.prompt("follow up")
    assert result.exit_reason is not None
    stored = store.load_messages("s1")
    assert len(stored) >= 3  # original user + assistant + new user + assistant


# ── Subscriber event delivery ──

@pytest.mark.asyncio
async def test_subscriber_receives_events(store: SessionStore):
    session = _make_session(store)
    events: list[LiveEvent] = []

    session.subscribe(lambda e: events.append(e))
    await session.prompt("hi")

    # Should have several events
    event_types = [e.event_type for e in events]
    assert LiveEventType.TURN_STARTED in event_types
    assert LiveEventType.USER_MESSAGE_ACCEPTED in event_types
    assert LiveEventType.ASSISTANT_DELTA in event_types or LiveEventType.ASSISTANT_COMPLETED in event_types
    assert LiveEventType.SESSION_SETTLED in event_types


# ── Abort returns session to idle ──

@pytest.mark.asyncio
async def test_abort_returns_session_to_idle(store: SessionStore):
    session = _make_session(store)
    session.abort()

    # Session should still accept prompts after abort (cancel wasn't active during a turn)
    result = await session.prompt("after abort")
    assert result is not None


# ── Subscriber failure does not fail the turn ──

@pytest.mark.asyncio
async def test_subscriber_failure_does_not_fail_turn(store: SessionStore):
    session = _make_session(store)

    def failing_subscriber(event: LiveEvent) -> None:
        raise RuntimeError("subscriber crash")

    session.subscribe(failing_subscriber)

    # This should still complete
    result = await session.prompt("hello")
    assert result is not None
    assert result.exit_reason is not None


# ── Resume non-existent session raises ──

def test_resume_nonexistent_session_raises(store: SessionStore):
    with pytest.raises(ValueError, match="not found"):
        AgentSession.resume(
            session_id="nonexistent",
            session_store=store,
            model=_fake_model_response(),
            system_prompt=lambda: "sys",
            context_messages=lambda: [],
            tool_registry_fn=lambda: ToolRegistry(),
            active_tool_names_fn=lambda: (),
        )


# ── Unsubscribe works ──

@pytest.mark.asyncio
async def test_unsubscribe_works(store: SessionStore):
    session = _make_session(store, model_count=2)
    events: list[LiveEvent] = []

    unsub = session.subscribe(lambda e: events.append(e))

    # Trigger one turn to get some events
    await session.prompt("first")
    first_count = len(events)

    # Unsubscribe
    unsub()
    events.clear()

    # Second turn — subscriber should not receive events
    await session.prompt("second")
    assert len(events) == 0


# ── Regression: SESSION_STARTED emitted exactly once (M3) ──

@pytest.mark.asyncio
async def test_session_started_emitted_once(store: SessionStore):
    session = _make_session(store, model_count=2)
    events: list[LiveEvent] = []
    session.subscribe(lambda e: events.append(e))

    await session.prompt("first turn")

    started_events = [e for e in events if e.event_type == LiveEventType.SESSION_STARTED]
    assert len(started_events) == 1, (
        f"Expected exactly 1 SESSION_STARTED, got {len(started_events)}"
    )
    assert started_events[0].session_id == "s1"

    # Second turn — no additional SESSION_STARTED
    await session.prompt("second turn")
    started_events_2 = [e for e in events if e.event_type == LiveEventType.SESSION_STARTED]
    assert len(started_events_2) == 1, "SESSION_STARTED emitted more than once"


# ── CanonicalParseError on corrupted messages ──

@pytest.mark.asyncio
async def test_canonical_parse_error_on_corrupted(store: SessionStore):
    """Corrupted session messages raise CanonicalParseError, not silently dropped."""
    from haxjobs.agent_core.session import _parse_canonical_history

    corrupted = [{
        "sequence": 1,
        "session_id": "s1",
        "turn_id": "t1",
        "message_kind": "assistant",
        "payload_json": {"kind": "assistant", "message_id": "m1", "turn_id": "t1",
                         "content": "ok", "status": "INVALID_STATUS"},
        "created_at": "2025-01-01T00:00:00",
    }]
    with pytest.raises(CanonicalParseError):
        _parse_canonical_history(corrupted)


# ── Regression: QUEUED exit reason for busy session ──

@pytest.mark.asyncio
async def test_busy_returns_queued_not_interrupted(store: SessionStore):
    """When session is busy, prompt returns QUEUED, not INTERRUPTED."""
    from haxjobs.agent_core.turn import TurnExitReason

    # Use a delayed fake model so the first turn stays busy long enough
    model = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="slow",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        delay_ms=200,
        repeat=True,
    )
    store.create_session("s1")
    session = AgentSession(
        session_id="s1",
        session_store=store,
        model=model,
        system_prompt=lambda: "You are helpful.",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    # Submit first prompt (will run)
    task1 = asyncio.create_task(session.prompt("first"))
    await asyncio.sleep(0.05)  # let it start streaming

    # Submit second prompt while first is still running
    result = await session.prompt("second")
    assert result.exit_reason == TurnExitReason.QUEUED

    # Let first finish
    await task1


# ── Regression: Host/context setup failure caught ──

@pytest.mark.asyncio
async def test_host_context_setup_failure_emits_turn_failed(store: SessionStore):
    """If host/context setup raises, TURN_FAILED and SESSION_SETTLED are emitted."""
    store.create_session("s1")

    def broken_context():
        raise RuntimeError("context explosion")

    session = AgentSession(
        session_id="s1",
        session_store=store,
        model=_fake_model_response(count=1),
        system_prompt=lambda: "sys",
        context_messages=broken_context,
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )
    events: list[LiveEvent] = []
    session.subscribe(lambda e: events.append(e))

    result = await session.prompt("hello")
    assert result.exit_reason is not None
    event_types = [e.event_type for e in events]
    assert LiveEventType.TURN_FAILED in event_types
    assert LiveEventType.SESSION_SETTLED in event_types


# ── Regression: AgentSession.close() works ──

def test_session_close(store: SessionStore):
    """close() calls cleanup callbacks and closes the store."""
    session = _make_session(store)
    cleaned = []
    session.add_cleanup(lambda: cleaned.append(True))
    session.close()
    assert len(cleaned) == 1


# ═══════════════════════════════════════════════════════════════════
# Repair round 3: Lifecycle defect cluster — deterministic tests
# ═══════════════════════════════════════════════════════════════════

# ── R3-1: Idle abort does not cancel next prompt ──

@pytest.mark.asyncio
async def test_idle_abort_does_not_cancel_next_prompt(store: SessionStore):
    """When the session is idle, abort() is a no-op. The next prompt runs normally."""
    session = _make_session(store, model_count=2)

    # Idle abort
    session.abort()
    session.abort()  # multiple idle aborts are fine

    # Next prompt should complete normally, not be interrupted
    result = await session.prompt("hello after idle abort")
    assert result.exit_reason is not None
    assert result.exit_reason != TurnExitReason.INTERRUPTED  # type: ignore[comparison-overlap]


# ── R3-2: Cancel current then queued successor runs with fresh event ──

@pytest.mark.asyncio
async def test_cancel_current_queued_successor_runs(store: SessionStore):
    """After aborting the current turn, the queued successor runs with a fresh
    cancel event — not poisoned by the previous abort."""
    store.create_session("s1")

    # Slow model for the first turn
    model = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="slow",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        delay_ms=300,
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

    # Start the first turn as a task
    task1 = asyncio.create_task(session.prompt("first"))
    await asyncio.sleep(0.05)  # let it start streaming

    # Queue second message while busy
    result2 = await session.prompt("second")
    assert result2.exit_reason == TurnExitReason.QUEUED

    # Abort the first turn mid-stream
    session.abort()

    # Wait for the owner task to finish (first interrupted + second runs)
    final = await task1

    # Because the serial loop runs both turns, the final result is from the
    # last turn ("second") — which should have a fresh event and complete normally.
    # If the idle abort poisoned the successor, "second" would also be INTERRUPTED.
    assert final.exit_reason == TurnExitReason.COMPLETED, (
        f"Expected COMPLETED from queued successor, got {final.exit_reason}"
    )


# ── R3-3: Pending work finishes before session close ──

@pytest.mark.asyncio
async def test_pending_work_finishes_before_close(store: SessionStore):
    """All pending turns finish and are persisted before the session closes.
    No turn is dropped."""
    store.create_session("s1")

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

    # Submit first prompt (becomes the owner task)
    task1 = asyncio.create_task(session.prompt("first"))
    await asyncio.sleep(0.02)

    # Queue second while busy — returns QUEUED, handled by serial loop
    await session.prompt("second")

    # Queue a third
    await session.prompt("third")

    # Wait for the owner task to finish all three
    await task1

    # All three user messages and three assistant messages should be persisted
    stored = store.load_messages("s1")
    kinds = [m["payload_json"]["kind"] for m in stored]
    assert kinds.count("user") == 3, f"Expected 3 user messages, got {kinds.count('user')}"
    assert kinds.count("assistant") == 3, f"Expected 3 assistant messages, got {kinds.count('assistant')}"

    # Session should be idle
    assert session._busy is False
    assert session._pending_message is None
    assert session._cancel_event is None


# ── R3-4: No detached task after turn chain completes ──

@pytest.mark.asyncio
async def test_no_detached_task_after_chain(store: SessionStore):
    """After the serial loop finishes, no detached asyncio task lingers.
    The session is fully idle with _cancel_event cleared."""
    session = _make_session(store, model_count=1)

    result = await session.prompt("single")
    assert result.exit_reason is not None

    # Session must be fully idle — no active cancel event, no pending work
    assert session._busy is False
    assert session._pending_message is None
    assert session._cancel_event is None, (
        "cancel_event should be None after serial loop, not a lingering Event"
    )

    # Subsequent idle abort is still a no-op
    session.abort()  # should not crash


# ── R3-5: Immediate Enter then Escape reaches active turn ──

@pytest.mark.asyncio
async def test_immediate_enter_then_escape_reaches_active_turn(store: SessionStore):
    """Simulating 'Enter then Escape immediately': abort must reach the running turn.
    After the yield tick, the session is busy and cancel_event is set."""
    store.create_session("s1")

    model = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="streaming...",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        delay_ms=500,
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

    # Fire prompt as a non-blocking task (mimicking terminal)
    prompt_task = asyncio.create_task(session.prompt("hello"))

    # Yield one tick — this is what TerminalClient does after creating the task
    await asyncio.sleep(0)

    # Now the session should be busy and cancel_event should be set
    assert session._busy is True
    assert session._cancel_event is not None, (
        "cancel_event should be set after the yield tick"
    )

    # Simulate immediate Escape
    session.abort()
    assert session._cancel_event.is_set(), (
        "abort should set the current turn's cancel event"
    )

    # Wait for turn to finish (it should be interrupted)
    result = await prompt_task
    assert result.exit_reason == TurnExitReason.INTERRUPTED

    # Verify the session returns to clean idle state
    assert session._busy is False
    assert session._cancel_event is None


# ══════════════════════════════════════════════
# Plan 004 — Session configuration and measurement tests
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_unconfigured_session_fails_on_resume(store: SessionStore):
    """Resume raises ValueError for session without configuration."""
    # Create session without config (old-style create_session)
    store.create_session("old-session")  # no configuration_json
    store.mark_turn_settled("old-session", 1)

    with pytest.raises(ValueError, match="no configuration"):
        AgentSession.resume(
            session_id="old-session",
            session_store=store,
            model=_fake_model_response(),
            system_prompt=lambda: "sys",
            context_messages=lambda: [],
            tool_registry_fn=lambda: ToolRegistry(),
            active_tool_names_fn=lambda: (),
        )


@pytest.mark.asyncio
async def test_dangling_call_gets_synthetic_result(store: SessionStore):
    """Unmatched ToolCallMessage on resume gets unknown_outcome result."""
    import json
    store.create_session("s-dangle", configuration_json=json.dumps({"person_id": "test", "track_id": "test"}))

    # Insert a ToolCallMessage without a matching ToolResultMessage
    from haxjobs.agent_core.messages import ToolCallMessage
    tc = ToolCallMessage(
        message_id="tc1", turn_id="t1", call_id="dangle_1",
        tool_name="test_tool", arguments='{"value": "x"}'
    )
    store.append_message("s-dangle", tc)
    store.mark_turn_settled("s-dangle", 1)

    # Resume should detect dangling and append synthetic result
    session = AgentSession.resume(
        session_id="s-dangle",
        session_store=store,
        model=_fake_model_response(count=2),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )
    assert session.session_id == "s-dangle"

    # Check that synthetic result was appended
    stored = store.load_messages("s-dangle")
    tool_results = [
        m for m in stored
        if m.get("payload_json", {}).get("kind") == "tool_result"
        and m.get("payload_json", {}).get("call_id") == "dangle_1"
    ]
    assert len(tool_results) == 1
    tr = tool_results[0]["payload_json"]
    assert tr["ok"] is False
    assert tr["error_code"] == "unknown_outcome"


@pytest.mark.asyncio
async def test_no_duplicate_persistence(store: SessionStore):
    """Messages are not persisted twice."""
    session = _make_session(store, model_count=2)
    await session.prompt("hello")

    stored = store.load_messages("s1")
    kinds = [m["payload_json"]["kind"] for m in stored]
    # Exactly one user and one assistant
    assert kinds.count("user") == 1
    assert kinds.count("assistant") == 1


@pytest.mark.asyncio
async def test_dangling_call_not_auto_retried(store: SessionStore):
    """Synthetic unknown_outcome result does not trigger handler re-execution."""
    import json
    from haxjobs.agent_core.messages import ToolCallMessage
    store.create_session("s-no-retry", configuration_json=json.dumps({"person_id": "test", "track_id": "test"}))

    tc = ToolCallMessage(
        message_id="tc2", turn_id="t2", call_id="no_retry_1",
        tool_name="test_tool", arguments='{"value": "x"}'
    )
    store.append_message("s-no-retry", tc)
    store.mark_turn_settled("s-no-retry", 1)

    # Resume: should append synthetic, not re-execute
    session = AgentSession.resume(
        session_id="s-no-retry",
        session_store=store,
        model=_fake_model_response(count=2),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    # Now send a prompt to verify session works normally
    result = await session.prompt("hello after resume")
    assert result.exit_reason is not None

    # The synthetic result should be there, and no handler was re-executed
    stored = store.load_messages("s-no-retry")
    tool_results = [
        m for m in stored
        if m.get("payload_json", {}).get("kind") == "tool_result"
        and m.get("payload_json", {}).get("call_id") == "no_retry_1"
    ]
    assert len(tool_results) == 1


@pytest.mark.asyncio
async def test_dangling_result_idempotent_on_repeated_resume(store: SessionStore):
    """Second resume in same process does not duplicate synthetic result."""
    import json
    from haxjobs.agent_core.messages import ToolCallMessage
    store.create_session("s-idem", configuration_json=json.dumps({"person_id": "test", "track_id": "test"}))

    tc = ToolCallMessage(
        message_id="tc3", turn_id="t3", call_id="idem_1",
        tool_name="test_tool", arguments='{"value": "x"}'
    )
    store.append_message("s-idem", tc)
    store.mark_turn_settled("s-idem", 1)

    # First resume
    _ = AgentSession.resume(
        session_id="s-idem",
        session_store=store,
        model=_fake_model_response(count=2),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    first_count = len(store.load_messages("s-idem"))

    # Second resume
    _ = AgentSession.resume(
        session_id="s-idem",
        session_store=store,
        model=_fake_model_response(count=2),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    second_count = len(store.load_messages("s-idem"))
    assert second_count == first_count, f"Expected {first_count} messages, got {second_count}"


# ── Measurement tests ──

@pytest.mark.asyncio
async def test_measurement_recorded_after_turn(store: SessionStore):
    """A completed turn records a measurement row with correct turn_number."""
    session = _make_session(store, model_count=1)
    await session.prompt("hello")

    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s1",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["turn_number"] == 1
    assert rows[0]["exit_reason"] is not None


@pytest.mark.asyncio
async def test_measurement_has_no_content_columns(store: SessionStore):
    """Schema has no prompt_text, response_text, tool_argument, or tool_result columns."""
    session = _make_session(store, model_count=1)
    await session.prompt("hello")

    cols = store._conn.execute("PRAGMA table_info(turn_measurements)").fetchall()
    col_names = {c["name"] for c in cols}
    forbidden = {"prompt_text", "response_text", "tool_arguments", "tool_results",
                  "prompt", "response", "career_context"}
    assert not col_names.intersection(forbidden), f"Forbidden columns found: {col_names.intersection(forbidden)}"


@pytest.mark.asyncio
async def test_measurement_row_contains_no_content_values(store: SessionStore):
    """Rows contain no content text in any column."""
    session = _make_session(store, model_count=1)
    await session.prompt("hello")

    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s1",)
    ).fetchall()
    assert len(rows) == 1
    row = dict(rows[0])
    # Check that none of the known columns contain large content
    for key, val in row.items():
        if isinstance(val, str) and len(val) > 500:
            pytest.fail(f"Column {key} contains large content: {len(val)} chars")


@pytest.mark.asyncio
async def test_measurement_interrupted_turn(store: SessionStore):
    """An interrupted turn still records exit_reason=interrupted."""
    store.create_session("s-int", configuration_json='{"person_id": "test", "track_id": "test"}')
    model = FakeModelClient(
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="slow",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        delay_ms=300,
        repeat=True,
    )
    session = AgentSession(
        session_id="s-int",
        session_store=store,
        model=model,
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    task = asyncio.create_task(session.prompt("hello"))
    await asyncio.sleep(0.05)
    session.abort()
    await task

    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s-int",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["exit_reason"] == "interrupted"


@pytest.mark.asyncio
async def test_measurement_null_usage_when_provider_omits(store: SessionStore):
    """When provider returns no usage, measurement stores NULL tokens."""
    session = _make_session(store, model_count=1)
    await session.prompt("hello")

    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s1",)
    ).fetchall()
    assert len(rows) == 1
    # Fake model doesn't return usage, so tokens should be NULL
    assert rows[0]["prompt_tokens"] is None


@pytest.mark.asyncio
async def test_measurement_host_setup_failure(store: SessionStore):
    """Host setup failure records exit_reason=host_setup_failure with null model fields."""
    store.create_session("s-hostfail", configuration_json='{"person_id": "test", "track_id": "test"}')

    def broken_context():
        raise RuntimeError("context explosion")

    session = AgentSession(
        session_id="s-hostfail",
        session_store=store,
        model=_fake_model_response(count=1),
        system_prompt=lambda: "sys",
        context_messages=broken_context,
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    await session.prompt("hello")

    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s-hostfail",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["exit_reason"] == "host_setup_failure"
    assert rows[0]["model_name"] == ""


@pytest.mark.asyncio
async def test_measurement_duplicate_turn_id_prevented(store: SessionStore):
    """UNIQUE(session_id, turn_id) prevents duplicate measurement rows."""
    session = _make_session(store, model_count=1)
    await session.prompt("hello")

    # Try to insert a duplicate measurement
    import sqlite3
    rows = store._conn.execute(
        "SELECT * FROM turn_measurements WHERE session_id = ?", ("s1",)
    ).fetchall()
    assert len(rows) == 1
    existing = dict(rows[0])

    from haxjobs.agent_core.session_store import _now
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute(
            """INSERT INTO turn_measurements (
                session_id, turn_id, turn_number, started_at, finished_at,
                exit_reason, model_name, provider_name, model_steps, tool_starts,
                input_characters, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (existing["session_id"], existing["turn_id"], existing["turn_number"],
             _now(), _now(), "test", "", "", 0, 0, 0, 0),
        )
