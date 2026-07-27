"""HaxJobs model boundary — provider adapters and normalized model responses."""

from haxjobs.model.types import (
    ModelFailure,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
    ModelUsage,
    ToolCall,
    ToolSchema,
)
from haxjobs.model.protocol import ModelClient
from haxjobs.model.profiles import (
    DEEPSEEK_PROFILE,
    DEFAULT_PROFILE,
    OPENAI_PROFILE,
    ProviderProfile,
    detect_profile,
)
from haxjobs.model.provider import ProviderConfig, ProviderConfigError, load_provider_config
from haxjobs.model.adapter import GenericAdapter
from haxjobs.model.schemas import tool_to_openai_schema, tools_to_openai_schemas
from haxjobs.model.streaming import StreamAccumulator
from haxjobs.model.fake import FakeModelClient

__all__ = [
    "DEEPSEEK_PROFILE",
    "DEFAULT_PROFILE",
    "FakeModelClient",
    "GenericAdapter",
    "ModelClient",
    "ModelFailure",
    "ModelMessage",
    "ModelRequest",
    "ModelResponse",
    "ModelStreamEvent",
    "ModelStreamEventType",
    "ModelUsage",
    "OPENAI_PROFILE",
    "ProviderConfig",
    "ProviderConfigError",
    "ProviderProfile",
    "StreamAccumulator",
    "ToolCall",
    "ToolSchema",
    "detect_profile",
    "load_provider_config",
    "tool_to_openai_schema",
    "tools_to_openai_schemas",
]
