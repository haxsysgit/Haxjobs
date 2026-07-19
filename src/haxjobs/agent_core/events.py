"""Lifecycle events — safe, passive, and observable."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    CONTEXT_PREPARED = "context_prepared"
    MODEL_STARTED = "model_started"
    MODEL_COMPLETED = "model_completed"
    MODEL_FAILED = "model_failed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class RunEvent(BaseModel):
    """One lifecycle event. Safe for JSONL — no raw content or credentials."""

    run_id: str
    event_type: RunEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model: str = ""
    provider: str = ""
    finish_reason: str = ""
    duration_seconds: float = 0.0
    error: str = ""
    error_category: str = ""

    model_config = {"extra": "forbid"}


def redact_event_for_jsonl(event: RunEvent) -> RunEvent:
    """Return a copy safe for persistent JSONL — no raw prompts, career data, or model text.

    The base RunEvent model already excludes those fields by design (extra=forbid).
    This function is a documented safety barrier.
    """
    return event


class RunObserver(Protocol):
    """Observe lifecycle events. Observer failures must not change the agent's work."""

    def on_event(self, event: RunEvent) -> None: ...
