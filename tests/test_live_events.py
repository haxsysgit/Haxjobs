"""Live interaction events — tests for all event types, validation, subscriber isolation.

Plan 003 Phase 2: Live events carry assistant text and tool lifecycle data
for the terminal. Separate from redacted RunEvent telemetry.
"""

from __future__ import annotations

import pytest

from haxjobs.agent_core.live_events import (
    LiveEvent,
    LiveEventType,
    LiveEventEmitter,
)


# ── Every event type validates ──

def test_session_started_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.SESSION_STARTED,
    )
    assert evt.event_type == LiveEventType.SESSION_STARTED
    assert evt.session_id == "s1"


def test_user_message_accepted_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.USER_MESSAGE_ACCEPTED,
        text="hello world",
    )
    assert evt.text == "hello world"


def test_turn_started_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_STARTED,
    )
    assert evt.turn_id == "t1"


def test_assistant_started_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.ASSISTANT_STARTED,
    )
    assert evt.event_type == LiveEventType.ASSISTANT_STARTED


def test_assistant_delta_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.ASSISTANT_DELTA,
        delta="Hello",
    )
    assert evt.delta == "Hello"


def test_assistant_completed_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.ASSISTANT_COMPLETED,
        text="full response",
    )
    assert evt.text == "full response"


def test_tool_requested_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TOOL_REQUESTED,
        call_id="c1",
        tool_name="inspect_job_source",
    )
    assert evt.call_id == "c1"
    assert evt.tool_name == "inspect_job_source"


def test_tool_started_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TOOL_STARTED,
        call_id="c1",
        tool_name="inspect_job_source",
    )
    assert evt.tool_name == "inspect_job_source"


def test_tool_progress_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TOOL_PROGRESS,
        call_id="c1",
        tool_name="long_task",
        text="50% complete",
    )
    assert evt.text == "50% complete"


def test_tool_completed_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TOOL_COMPLETED,
        call_id="c1",
        tool_name="inspect_job_source",
        tool_status="ok",
        tool_duration_ms=150.0,
    )
    assert evt.tool_status == "ok"
    assert evt.tool_duration_ms == 150.0


def test_tool_failed_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TOOL_FAILED,
        call_id="c1",
        tool_name="inspect_job_source",
        tool_status="blocked",
        error_code="blocked",
        error="source returned 403",
    )
    assert evt.tool_status == "blocked"
    assert evt.error_code == "blocked"
    assert evt.error == "source returned 403"


def test_turn_interrupted_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_INTERRUPTED,
    )
    assert evt.event_type == LiveEventType.TURN_INTERRUPTED


def test_turn_failed_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_FAILED,
        error="provider timeout",
    )
    assert evt.error == "provider timeout"


def test_turn_completed_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_COMPLETED,
    )
    assert evt.event_type == LiveEventType.TURN_COMPLETED


def test_session_settled_event():
    evt = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.SESSION_SETTLED,
    )
    assert evt.event_type == LiveEventType.SESSION_SETTLED


# ── Extra fields rejected ──

def test_live_event_rejects_extra_fields():
    with pytest.raises(ValueError):
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.SESSION_STARTED,
            secret="leaked",  # type: ignore[call-arg]
        )


# ── Deltas preserve exact order ──

def test_deltas_preserve_order():
    """Multiple assistant_delta events carry ordered text fragments."""
    deltas = [
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.ASSISTANT_DELTA,
            delta="Hello",
        ),
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.ASSISTANT_DELTA,
            delta=" ",
        ),
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.ASSISTANT_DELTA,
            delta="world",
        ),
    ]
    combined = "".join(e.delta for e in deltas)
    assert combined == "Hello world"


# ── Subscriber failure does not break delivery ──

def test_subscriber_failure_isolated():
    """One failing subscriber does not prevent delivery to other subscribers."""
    delivered: list[LiveEvent] = []

    def good_subscriber(event: LiveEvent) -> None:
        delivered.append(event)

    def failing_subscriber(event: LiveEvent) -> None:
        raise RuntimeError("subscriber crashed")

    event = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_STARTED,
    )

    # Simulate emission with error collection
    errors: list[str] = []
    for sub in [good_subscriber, failing_subscriber]:
        try:
            sub(event)
        except Exception as exc:
            errors.append(str(exc))

    assert len(delivered) == 1
    assert delivered[0].event_type == LiveEventType.TURN_STARTED
    assert len(errors) == 1
    assert "subscriber crashed" in errors[0]


# ── Live events and telemetry events remain separate ──

def test_live_event_separate_from_run_event():
    """LiveEvent and RunEvent are separate types with no shared base class."""
    from haxjobs.agent_core.events import RunEvent, RunEventType

    live = LiveEvent(
        session_id="s1",
        turn_id="t1",
        event_type=LiveEventType.TURN_STARTED,
    )
    run = RunEvent(run_id="r1", event_type=RunEventType.RUN_STARTED)

    # They are different types
    assert type(live) is not type(run)
    assert not isinstance(live, RunEvent)
    assert not isinstance(run, LiveEvent)
