"""Domain-free agent-core types."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from haxjobs.model.types import ModelUsage


class RunExitReason(str, Enum):
    COMPLETED = "completed"
    MODEL_FAILED = "model_failed"
    LIMIT_REACHED = "limit_reached"
    EMPTY_MODEL_RESPONSE = "empty_model_response"


@dataclass
class RunResult:
    """The result of one agent run — domain-free."""

    run_id: str
    exit_reason: RunExitReason
    final_text: str = ""
    safe_failure: str = ""
    model: str = ""
    provider: str = ""
    duration_seconds: float = 0.0
    usage: ModelUsage | None = None
    artifact_dir: str = ""
    observer_errors: list[str] = field(default_factory=list)
    artifact_errors: list[str] = field(default_factory=list)
    receipt_complete: bool = True
    model_steps: int = 0
    tool_starts: int = 0


@dataclass
class RunRequest:
    """Frozen inputs for one agent run."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    system_message: str = ""
    user_message: str = ""
    model_kwargs: dict[str, Any] = field(default_factory=dict)
