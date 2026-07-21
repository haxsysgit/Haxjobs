"""Live interaction events — content-bearing events for trusted interfaces.

Plan 003 Phase 2: Live events carry assistant text and tool lifecycle data
that the terminal needs for rendering. Separate from redacted telemetry RunEvent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveEventType(str, Enum):
    SESSION_STARTED = "session_started"
    USER_MESSAGE_ACCEPTED = "user_message_accepted"
    TURN_STARTED = "turn_started"
    ASSISTANT_STARTED = "assistant_started"
    ASSISTANT_DELTA = "assistant_delta"
    ASSISTANT_COMPLETED = "assistant_completed"
    TOOL_REQUESTED = "tool_requested"
    TOOL_STARTED = "tool_started"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    TURN_INTERRUPTED = "turn_interrupted"
    TURN_FAILED = "turn_failed"
    TURN_COMPLETED = "turn_completed"
    SESSION_SETTLED = "session_settled"


class LiveEvent(BaseModel):
    """One live interaction event with content safe for the local terminal.

    Carries assistant text and tool lifecycle data. Never carries credentials,
    HTTP headers, provider request objects, or private fixture contents.
    """

    session_id: str
    turn_id: str
    event_type: LiveEventType
    timestamp: str = Field(default_factory=_utcnow)

    # Optional event-specific fields
    text: str = ""
    delta: str = ""
    call_id: str = ""
    tool_name: str = ""
    tool_status: str = ""
    tool_duration_ms: float = 0.0
    error_code: str = ""
    error: str = ""

    model_config = {"extra": "forbid"}


LiveEventEmitter = Callable[[LiveEvent], None]
"""A subscriber callback. Failures are collected or logged, never change the turn result."""
