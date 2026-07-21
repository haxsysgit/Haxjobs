"""Canonical conversation messages — strict validation, projection, JSON round trip.

Plan 003 Phase 1: provider-neutral messages a session can persist and replay.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from haxjobs.agent_core.messages import (
    AssistantMessage,
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
    project_messages,
)
from haxjobs.model.types import ModelMessage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── UserMessage ──

def test_user_message_creates():
    msg = UserMessage(message_id="u1", turn_id="t1", content="hello")
    assert msg.kind == "user"
    assert msg.message_id == "u1"
    assert msg.turn_id == "t1"
    assert msg.content == "hello"
    assert msg.created_at


def test_user_message_rejects_extra_fields():
    with pytest.raises(ValueError):
        UserMessage(message_id="u1", turn_id="t1", content="hello", extra="nope")  # type: ignore[call-arg]


def test_user_message_json_round_trip():
    msg = UserMessage(message_id="u1", turn_id="t1", content="hello", created_at=_now())
    data = msg.model_dump_json()
    parsed = UserMessage.model_validate_json(data)
    assert parsed.message_id == "u1"
    assert parsed.content == "hello"


# ── AssistantMessage ──

def test_assistant_message_complete():
    msg = AssistantMessage(
        message_id="a1", turn_id="t1", content="here is the answer", status="complete"
    )
    assert msg.kind == "assistant"
    assert msg.status == "complete"


def test_assistant_message_interrupted():
    msg = AssistantMessage(
        message_id="a1", turn_id="t1", content="partial answer", status="interrupted"
    )
    assert msg.status == "interrupted"


def test_assistant_message_rejects_bad_status():
    with pytest.raises(ValueError):
        AssistantMessage(message_id="a1", turn_id="t1", content="x", status="pending")  # type: ignore[arg-type]


def test_assistant_message_json_round_trip():
    msg = AssistantMessage(
        message_id="a1", turn_id="t1", content="done", status="complete", created_at=_now()
    )
    data = msg.model_dump_json()
    parsed = AssistantMessage.model_validate_json(data)
    assert parsed.message_id == "a1"
    assert parsed.status == "complete"


# ── ToolCallMessage ──

def test_tool_call_message():
    msg = ToolCallMessage(
        message_id="tc1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="inspect_job_source",
        arguments='{"job_ref": "328"}',
    )
    assert msg.kind == "tool_call"
    assert msg.call_id == "call_abc"
    assert msg.tool_name == "inspect_job_source"


def test_tool_call_message_json_round_trip():
    msg = ToolCallMessage(
        message_id="tc1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="read_file",
        arguments='{"path": "/tmp/x"}',
        created_at=_now(),
    )
    data = msg.model_dump_json()
    parsed = ToolCallMessage.model_validate_json(data)
    assert parsed.call_id == "call_abc"
    assert parsed.tool_name == "read_file"
    assert parsed.arguments == '{"path": "/tmp/x"}'


# ── ToolResultMessage ──

def test_tool_result_message_ok():
    msg = ToolResultMessage(
        message_id="tr1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="inspect_job_source",
        ok=True,
        result={"status": "current", "text": "job desc"},
    )
    assert msg.kind == "tool_result"
    assert msg.ok is True
    assert msg.error_code is None
    assert msg.error is None


def test_tool_result_message_failed():
    msg = ToolResultMessage(
        message_id="tr1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="inspect_job_source",
        ok=False,
        result=None,
        error_code="blocked",
        error="source returned HTTP 403",
    )
    assert msg.ok is False
    assert msg.error_code == "blocked"
    assert msg.error == "source returned HTTP 403"


def test_tool_result_message_json_round_trip():
    msg = ToolResultMessage(
        message_id="tr1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="t1",
        ok=True,
        result={"x": 1},
        created_at=_now(),
    )
    data = msg.model_dump_json()
    parsed = ToolResultMessage.model_validate_json(data)
    assert parsed.ok is True
    assert parsed.result == {"x": 1}


# ── ConversationMessage union ──

def test_conversation_message_union_discriminates():
    """ConversationMessage union validates correct kind via discriminator."""
    from pydantic import TypeAdapter

    adapter = TypeAdapter(ConversationMessage)

    user = UserMessage(message_id="u1", turn_id="t1", content="hi")
    asst = AssistantMessage(message_id="a1", turn_id="t1", content="hey", status="complete")
    tc = ToolCallMessage(
        message_id="tc1", turn_id="t1", call_id="c1", tool_name="t", arguments="{}"
    )
    tr = ToolResultMessage(
        message_id="tr1", turn_id="t1", call_id="c1", tool_name="t", ok=True, result={}
    )

    for msg in [user, asst, tc, tr]:
        parsed = adapter.validate_python(msg.model_dump())
        assert parsed.kind == msg.kind


# ── project_messages ──

def test_project_messages_system_first():
    """System prompt is always the first projected message."""
    history: list[ConversationMessage] = []
    result = project_messages(
        system_prompt="You are helpful.",
        context_messages=[ModelMessage(role="system", content="career context: backend engineer")],
        history=history,
    )
    assert result[0].role == "system"
    assert result[0].content == "You are helpful."


def test_project_messages_context_after_system():
    """Career context appears after system prompt, before history."""
    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t1", content="hello"),
    ]
    result = project_messages(
        system_prompt="You are helpful.",
        context_messages=[ModelMessage(role="system", content="career context: backend engineer")],
        history=history,
    )
    roles = [m.role for m in result]
    assert roles[0] == "system"
    assert roles[1] == "system"  # career context as system
    assert roles[2] == "user"


def test_project_messages_history_after_context():
    """Canonical history follows career context."""
    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t1", content="first question"),
        AssistantMessage(message_id="a1", turn_id="t1", content="answer one", status="complete"),
        UserMessage(message_id="u2", turn_id="t2", content="second question"),
    ]
    result = project_messages(
        system_prompt="sys",
        context_messages=[],
        history=history,
    )
    assert len(result) == 4  # sys + 3 history messages
    assert result[1].role == "user"
    assert result[1].content == "first question"
    assert result[2].role == "assistant"
    assert result[3].role == "user"
    assert result[3].content == "second question"


def test_project_messages_tool_calls_project_correctly():
    """Assistant tool calls project to provider assistant messages with tool_calls."""
    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t1", content="inspect job 328"),
        ToolCallMessage(
            message_id="tc1",
            turn_id="t1",
            call_id="call_1",
            tool_name="inspect_job_source",
            arguments='{"job_ref": "328"}',
        ),
        ToolResultMessage(
            message_id="tr1",
            turn_id="t1",
            call_id="call_1",
            tool_name="inspect_job_source",
            ok=True,
            result={"status": "current", "visible_text": "job desc"},
        ),
        AssistantMessage(
            message_id="a1", turn_id="t1", content="The source shows...", status="complete"
        ),
    ]
    result = project_messages(
        system_prompt="sys",
        context_messages=[],
        history=history,
    )

    # Expected roles: system, user, assistant (with tool_calls), tool (result), assistant (text)
    assert len(result) == 5

    # User message
    assert result[1].role == "user"
    assert result[1].content == "inspect job 328"

    # Assistant message with tool calls (from ToolCallMessage + preceding assistant or standalone)
    assert result[2].role == "assistant"
    assert result[2].tool_calls is not None
    assert len(result[2].tool_calls) == 1
    assert result[2].tool_calls[0]["id"] == "call_1"
    assert result[2].tool_calls[0]["function"]["name"] == "inspect_job_source"

    # Tool result
    assert result[3].role == "tool"
    assert result[3].tool_call_id == "call_1"

    # Final assistant
    assert result[4].role == "assistant"
    assert result[4].content == "The source shows..."


def test_project_messages_career_context_not_in_persisted():
    """Career context is in projection but never in persisted history."""
    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t1", content="hi"),
    ]
    result = project_messages(
        system_prompt="sys",
        context_messages=[ModelMessage(role="system", content="career: backend")],
        history=history,
    )
    # The context is in the projection
    assert any(m.content == "career: backend" for m in result)

    # But checking history separately: only the user message
    assert len(history) == 1
    assert history[0].content == "hi"
    assert "career" not in history[0].content.lower()


def test_project_messages_matching_call_ids():
    """Tool call and result messages share matching call_ids."""
    tc = ToolCallMessage(
        message_id="tc1", turn_id="t1", call_id="abc123", tool_name="t", arguments="{}"
    )
    tr = ToolResultMessage(
        message_id="tr1", turn_id="t1", call_id="abc123", tool_name="t", ok=True, result={}
    )
    assert tc.call_id == tr.call_id == "abc123"

    history: list[ConversationMessage] = [
        UserMessage(message_id="u1", turn_id="t1", content="go"),
        tc,
        tr,
        AssistantMessage(message_id="a1", turn_id="t1", content="done", status="complete"),
    ]
    result = project_messages(system_prompt="sys", context_messages=[], history=history)
    # The tool result must reference the same call_id
    tool_msgs = [m for m in result if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].tool_call_id == "abc123"


def test_project_messages_rejects_extra_fields():
    """All message types reject extra fields via extra='forbid'."""
    with pytest.raises(ValueError):
        UserMessage(message_id="u1", turn_id="t1", content="hi", secret="no")  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        AssistantMessage(
            message_id="a1", turn_id="t1", content="x", status="complete", secret="no"  # type: ignore[call-arg]
        )
    with pytest.raises(ValueError):
        ToolCallMessage(
            message_id="tc1", turn_id="t1", call_id="c1", tool_name="t",
            arguments="{}", secret="no"  # type: ignore[call-arg]
        )
    with pytest.raises(ValueError):
        ToolResultMessage(
            message_id="tr1", turn_id="t1", call_id="c1", tool_name="t",
            ok=True, result={}, secret="no"  # type: ignore[call-arg]
        )
