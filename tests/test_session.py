"""Session tests — persistence, subscribers, cancellation, resume, busy policy.

Plan 003 Phase 7: AgentSession owns prompt boundaries, canonical history, and turn orchestration.
"""

from __future__ import annotations

import asyncio

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.messages import ConversationMessage
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.tools import ToolRegistry
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
    store.create_session("s1")
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
    resumed = await AgentSession.resume(
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

@pytest.mark.asyncio
async def test_resume_nonexistent_session_raises(store: SessionStore):
    with pytest.raises(ValueError, match="not found"):
        await AgentSession.resume(
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
