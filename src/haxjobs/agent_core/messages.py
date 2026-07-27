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
    reasoning_content: str = ""
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

class MessageProjector:
    """Projects canonical conversation history to provider-compatible ModelMessages.

    Stateful across message kinds: batches assistant text with subsequent
    tool calls into a single provider assistant message. Tool results flush
    the preceding assistant block and become standalone tool messages.
    """

    def __init__(self) -> None:
        self._result: list[ModelMessage] = []
        self._pending_text: str | None = None
        self._pending_tool_calls: list[dict[str, Any]] = []
        self._pending_reasoning_content: str = ""

    def _flush(self) -> None:
        if self._pending_text is not None or self._pending_tool_calls:
            msg = ModelMessage(
                role="assistant",
                content=self._pending_text or "",
            )
            if self._pending_tool_calls:
                msg.tool_calls = list(self._pending_tool_calls)
            if self._pending_reasoning_content:
                msg.reasoning_content = self._pending_reasoning_content
            self._result.append(msg)
        self._pending_text = None
        self._pending_tool_calls = []
        self._pending_reasoning_content = ""

    def project(
        self,
        system_prompt: str,
        context_messages: list[ModelMessage],
        history: list[ConversationMessage],
    ) -> list[ModelMessage]:
        """Project system prompt, context, and history into provider messages."""
        self._result = []
        self._pending_text = None
        self._pending_tool_calls = []

        # System prompt first
        self._result.append(ModelMessage(role="system", content=system_prompt))

        # Career context second
        self._result.extend(context_messages)

        for msg in history:
            if msg.kind == "user":
                self._flush()
                self._result.append(ModelMessage(role="user", content=msg.content))

            elif msg.kind == "assistant":
                self._flush()
                self._pending_text = msg.content
                self._pending_reasoning_content = getattr(msg, "reasoning_content", "")

            elif msg.kind == "tool_call":
                if self._pending_text is None and not self._pending_tool_calls:
                    self._pending_text = ""
                self._pending_tool_calls.append({
                    "id": msg.call_id,
                    "type": "function",
                    "function": {
                        "name": msg.tool_name,
                        "arguments": msg.arguments,
                    },
                })

            elif msg.kind == "tool_result":
                self._flush()
                self._result.append(ModelMessage(
                    role="tool",
                    content=_tool_result_content(msg),
                    tool_call_id=msg.call_id,
                ))

        self._flush()
        return list(self._result)


# Module-level convenience — creates a fresh instance per call.
_projector = MessageProjector()


def project_messages(
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
) -> list[ModelMessage]:
    """Project canonical conversation history to provider-compatible ModelMessages."""
    return _projector.project(
        system_prompt=system_prompt,
        context_messages=context_messages,
        history=history,
    )


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
