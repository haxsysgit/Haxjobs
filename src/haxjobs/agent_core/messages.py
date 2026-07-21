"""Canonical conversation messages — provider-neutral, persistable, replayable.

Plan 003 Phase 1: messages a session can persist and project to provider format.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from haxjobs.model.types import ModelMessage


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Message types ──

class UserMessage(BaseModel):
    """A user-submitted message — the canonical durable record."""

    kind: Literal["user"] = "user"
    message_id: str
    turn_id: str
    content: str
    created_at: str = Field(default_factory=_utcnow)

    model_config = {"extra": "forbid"}


class AssistantMessage(BaseModel):
    """A model-produced assistant message — may be complete, interrupted, or failed."""

    kind: Literal["assistant"] = "assistant"
    message_id: str
    turn_id: str
    content: str
    status: Literal["complete", "interrupted", "failed"]
    created_at: str = Field(default_factory=_utcnow)

    model_config = {"extra": "forbid"}


class ToolCallMessage(BaseModel):
    """A tool call requested by the model."""

    kind: Literal["tool_call"] = "tool_call"
    message_id: str
    turn_id: str
    call_id: str
    tool_name: str
    arguments: str  # raw JSON string
    created_at: str = Field(default_factory=_utcnow)

    model_config = {"extra": "forbid"}


class ToolResultMessage(BaseModel):
    """The result of a tool execution — success or failure."""

    kind: Literal["tool_result"] = "tool_result"
    message_id: str
    turn_id: str
    call_id: str
    tool_name: str
    ok: bool
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=_utcnow)

    model_config = {"extra": "forbid"}


ConversationMessage = UserMessage | AssistantMessage | ToolCallMessage | ToolResultMessage


# ── Projection ──

def project_messages(
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
) -> list[ModelMessage]:
    """Project canonical conversation history to provider-compatible ModelMessages.

    Rules:
    - System prompt is always first.
    - Career context (context_messages) follows system prompt.
    - Canonical session history comes after context.
    - Assistant tool calls project to provider assistant messages with tool_calls.
    - Tool results project to provider tool messages with matching call IDs.
    - Career context is never part of persisted history (caller ensures this).
    """
    result: list[ModelMessage] = []

    # System prompt first
    result.append(ModelMessage(role="system", content=system_prompt))

    # Career context second
    result.extend(context_messages)

    # Canonical history — project with tool-call batching
    pending_assistant_text: str | None = None
    pending_tool_calls: list[dict[str, Any]] = []

    def _flush_pending() -> None:
        nonlocal pending_assistant_text, pending_tool_calls
        if pending_assistant_text is not None or pending_tool_calls:
            msg = ModelMessage(
                role="assistant",
                content=pending_assistant_text or "",
            )
            if pending_tool_calls:
                msg.tool_calls = list(pending_tool_calls)
            result.append(msg)
        pending_assistant_text = None
        pending_tool_calls = []

    for msg in history:
        if msg.kind == "user":
            _flush_pending()
            result.append(ModelMessage(role="user", content=msg.content))

        elif msg.kind == "assistant":
            _flush_pending()
            pending_assistant_text = msg.content
            # If this is the last message in a sequence (no following tool calls),
            # it will be flushed by the next message kind or at loop end.

        elif msg.kind == "tool_call":
            # If no pending assistant text yet, start with empty content
            if pending_assistant_text is None and not pending_tool_calls:
                pending_assistant_text = ""
            pending_tool_calls.append({
                "id": msg.call_id,
                "type": "function",
                "function": {
                    "name": msg.tool_name,
                    "arguments": msg.arguments,
                },
            })

        elif msg.kind == "tool_result":
            # Flush the preceding assistant message (with its tool calls) before the tool result
            _flush_pending()
            result.append(ModelMessage(
                role="tool",
                content=_tool_result_content(msg),
                tool_call_id=msg.call_id,
            ))

    # Flush any trailing assistant message
    _flush_pending()

    return result


def _tool_result_content(msg: ToolResultMessage) -> str:
    """Serialize a tool result to string for provider projection."""
    import json

    return json.dumps({
        "call_id": msg.call_id,
        "tool_name": msg.tool_name,
        "ok": msg.ok,
        "result": msg.result,
        "error_code": msg.error_code,
        "error": msg.error,
    }, default=str)
