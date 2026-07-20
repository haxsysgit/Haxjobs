"""HaxJobs model boundary — provider adapters and normalized model responses."""

from haxjobs.model.types import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ModelFailure,
    ToolCall,
    ToolSchema,
)
from haxjobs.model.client import ModelClient
from haxjobs.model.fake import FakeModelClient

__all__ = [
    "ModelClient",
    "ModelFailure",
    "ModelMessage",
    "ModelRequest",
    "ModelResponse",
    "ModelUsage",
    "FakeModelClient",
    "ToolCall",
    "ToolSchema",
]
