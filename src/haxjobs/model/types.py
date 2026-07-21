"""Normalized model types — no provider-specific raw objects here."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    """Provider-neutral tool schema for the model."""

    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)


class ToolCall(BaseModel):
    """One tool call from the model — call_id, name, raw argument JSON."""

    call_id: str
    name: str
    arguments: str  # raw JSON string, never auto-repaired here


class ModelMessage(BaseModel):
    """One message in a model request — provider-compatible projection."""

    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class ModelRequest(BaseModel):
    """A complete model call request — internal messages only."""

    messages: list[ModelMessage]
    max_tokens: int = Field(default=4096, ge=1)
    tools: list[ToolSchema] = Field(default_factory=list)


class ModelUsage(BaseModel):
    """Provider-reported token usage."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ModelResponse(BaseModel):
    """Successful model response."""

    text: str
    finish_reason: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_calls_unsafe: bool = False  # true when response cut off mid-tool-call
    usage: ModelUsage | None = None
    model: str
    provider: str


class ModelFailure(BaseModel):
    """Model call failure — safe for logging and reporting."""

    error: str
    category: str = "provider_error"
    retryable: bool = False
    model: str = ""
    provider: str = ""

    def safe_summary(self) -> str:
        return f"Model failure [{self.category}]: {self.error}"


# ── Streaming types ──

class ModelStreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    COMPLETE_TOOL_CALL = "complete_tool_call"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_FAILED = "response_failed"


class ModelStreamEvent(BaseModel):
    """One event from a streaming model call — provider-neutral."""

    event_type: ModelStreamEventType
    delta: str = ""
    call_id: str = ""
    tool_name: str = ""
    arguments: str = ""  # accumulated raw JSON
    finish_reason: str = ""
    usage: ModelUsage | None = None
    model: str = ""
    provider: str = ""
    error: str = ""
    category: str = ""
