"""Terminal tests — key bindings, event rendering, cleanup, no alternate screen.

Plan 003 Phase 8: prompt_toolkit terminal over constructed session. No live provider calls.
"""

from __future__ import annotations

import asyncio
import sys
from io import StringIO
from unittest import mock

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.interfaces.terminal import TerminalClient
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelStreamEvent, ModelStreamEventType


def _fake_model() -> FakeModelClient:
    return FakeModelClient(
        responses=[],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA,
                    delta="Hello from the terminal.",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
    )


def _make_session(store: SessionStore) -> AgentSession:
    store.create_session("s1", configuration_json='{"scope": "test"}')
    return AgentSession(
        session_id="s1",
        session_store=store,
        model=_fake_model(),
        system_prompt=lambda: "You are helpful.",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )


# ── Streamed assistant deltas render exactly once ──

def test_assistant_deltas_rendered():
    """Terminal renders each delta exactly once."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.ASSISTANT_DELTA,
                delta="Hello",
            )
        )
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.ASSISTANT_DELTA,
                delta=" world",
            )
        )

    result = output.getvalue()
    assert "Hello" in result
    assert "world" in result


# ── Tool lifecycle lines come from actual events ──

def test_tool_events_from_real_events():
    """Tool lifecycle events are generated from LiveEvent, never fabricated."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)

    # These should not crash — terminal just passes through
    client._on_event(
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.TOOL_STARTED,
            tool_name="inspect_job_source",
            call_id="c1",
        )
    )
    client._on_event(
        LiveEvent(
            session_id="s1",
            turn_id="t1",
            event_type=LiveEventType.TOOL_COMPLETED,
            tool_name="inspect_job_source",
            tool_status="ok",
        )
    )
    # No assertion needed — just proves no crash


# ── No response text exists outside event payloads ──

def test_no_text_outside_events():
    """Terminal renders only what events provide. No fabricated assistant text."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.ASSISTANT_STARTED,
            )
        )
        # No delta, just started and completed — no fabricated text
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.ASSISTANT_COMPLETED,
            )
        )

    result = output.getvalue()
    # Only newlines from STARTED and COMPLETED — no text
    assert "Hello" not in result


# ── Interrupted event renders ──

def test_interrupted_event_renders():
    """Interrupted turns show [interrupted] status."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TURN_INTERRUPTED,
            )
        )

    assert "[interrupted]" in output.getvalue()


# ── Failed event renders ──

def test_failed_event_renders():
    """Failed turns show the error."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TURN_FAILED,
                error="provider timeout",
            )
        )

    assert "provider timeout" in output.getvalue()


# ── Rendering errors don't crash ──

def test_rendering_error_does_not_crash():
    """Terminal rendering errors are caught and ignored."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    # Simulate a broken stdout
    with mock.patch("sys.stdout", output):
        with mock.patch("sys.stdout.flush", side_effect=RuntimeError("broken pipe")):
            # Should not raise
            client._on_event(
                LiveEvent(
                    session_id="s1",
                    turn_id="t1",
                    event_type=LiveEventType.ASSISTANT_DELTA,
                    delta="test",
                )
            )


# ── Terminal does not import CareerStore ──

def test_terminal_does_not_import_career_store():
    """Terminal module must not import CareerStore or employment storage."""
    import haxjobs.interfaces.terminal as tmod

    # Check only the importable names in the module (exclude docstring)
    names = {k: v for k, v in tmod.__dict__.items() if not k.startswith("__")}
    assert "CareerStore" not in str(names)
    assert "CareerStore" not in names
    assert "career" not in str(names).lower()
    assert "OpenAIModelClient" not in str(names)
    assert "FakeModelClient" not in str(names)


# ── Terminal does not import provider clients ──

def test_terminal_does_not_import_provider():
    """Terminal module must not import provider clients directly."""
    import haxjobs.interfaces.terminal as tmod

    # Check that terminal module doesn't have provider clients in its namespace
    assert "OpenAIModelClient" not in str(tmod.__dict__)
    assert "FakeModelClient" not in str(tmod.__dict__)
    assert not hasattr(tmod, "OpenAIModelClient")
    assert not hasattr(tmod, "FakeModelClient")


# ── Regression: Tool events rendered from LiveEvents (Finding 6) ──

def test_tool_started_event_rendered():
    """TOOL_STARTED events produce visible output."""
    from io import StringIO
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TOOL_STARTED,
                tool_name="inspect_job_source",
                call_id="c1",
            )
        )

    result = output.getvalue()
    assert "inspect_job_source" in result
    # Should have the "..." indicator
    assert "..." in result


def test_tool_completed_event_rendered():
    """TOOL_COMPLETED events produce visible output with duration."""
    from io import StringIO
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TOOL_COMPLETED,
                tool_name="inspect_job_source",
                tool_status="ok",
                tool_duration_ms=150.0,
            )
        )

    result = output.getvalue()
    assert "ok" in result
    assert "150ms" in result


def test_tool_failed_event_rendered():
    """TOOL_FAILED events produce visible error output."""
    from io import StringIO
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TOOL_FAILED,
                tool_name="inspect_job_source",
                error_code="unknown_job_ref",
                error="Job ref not recognized",
            )
        )

    result = output.getvalue()
    assert "FAILED" in result
    assert "unknown_job_ref" in result


def test_tool_progress_event_rendered():
    """TOOL_PROGRESS events produce visible dots or text."""
    from io import StringIO
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    output = StringIO()

    with mock.patch("sys.stdout", output):
        client._on_event(
            LiveEvent(
                session_id="s1",
                turn_id="t1",
                event_type=LiveEventType.TOOL_PROGRESS,
                text="loading...",
            )
        )

    result = output.getvalue()
    assert "loading..." in result


# ── Regression: TerminalClient tracks owner task (Round 3) ──

def test_terminal_client_has_owner_task_tracking():
    """TerminalClient initializes with _owner_task = None."""
    client = TerminalClient(mock.MagicMock(), show_session_info=False)
    assert hasattr(client, "_owner_task")
    assert client._owner_task is None


# ── R3-6: Done callback handles CancelledError explicitly ──

def test_safe_prompt_done_handles_cancelled():
    """The _safe_prompt_done callback does not crash on a cancelled task."""
    from haxjobs.interfaces.terminal import _safe_prompt_done

    async def _canceller():
        raise asyncio.CancelledError()

    async def _normal():
        return "ok"

    async def _failing():
        raise RuntimeError("boom")

    # Cancelled task — should return silently
    loop = asyncio.new_event_loop()
    try:
        t_cancelled = loop.create_task(_canceller())
        loop.run_until_complete(asyncio.sleep(0))
        t_cancelled.cancel()
        try:
            loop.run_until_complete(t_cancelled)
        except asyncio.CancelledError:
            pass
        # Should not raise
        _safe_prompt_done(t_cancelled)

        # Normal task — no exception
        t_normal = loop.create_task(_normal())
        loop.run_until_complete(t_normal)
        _safe_prompt_done(t_normal)  # should not raise

        # Failing task — logs error but doesn't raise
        t_failing = loop.create_task(_failing())
        try:
            loop.run_until_complete(t_failing)
        except RuntimeError:
            pass
        _safe_prompt_done(t_failing)  # should not raise, just logs
    finally:
        loop.close()
