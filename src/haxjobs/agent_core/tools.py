"""Explicit tool registry and active-set enforcement — no auto-discovery or plugins."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel

from haxjobs.agent_core.errors import normalize_tool_code, safe_tool_error
from haxjobs.model.types import ToolSchema

logger = logging.getLogger(__name__)

HandlerFunc = Callable[[Any, "ToolExecutionContext"], Coroutine[Any, Any, dict[str, Any]]]


class EffectKind(str, Enum):
    READ = "read"
    INTERNAL_WRITE = "internal_write"
    EXTERNAL_EFFECT = "external_effect"


@dataclass
class ToolExecutionContext:
    """Domain free context passed to every tool handler."""
    session_id: str
    turn_id: str
    call_id: str
    user_message_id: str
    cancel_event: asyncio.Event


@dataclass
class ToolDefinition:
    """One registered tool — name, schema, handler, resource limits, and policy metadata."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: HandlerFunc
    max_result_chars: int = 12_000
    effect_kind: EffectKind = EffectKind.READ
    retry_safe: bool = False


class ToolRegistry:
    """Explicit registry — no import-time discovery.

    Tools are registered by name. Duplicate registration raises ValueError.
    Dispatch receives the active set, enforces membership, and passes context.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def active_schemas(self, active_names: tuple[str, ...]) -> list[ToolSchema]:
        """Return ordered ToolSchema objects for active tools."""
        schemas: list[ToolSchema] = []
        for name in active_names:
            if name not in self._tools:
                raise ValueError(f"unknown active tool: {name}")
            tool = self._tools[name]
            schema = tool.input_model.model_json_schema()
            schemas.append(
                ToolSchema(
                    name=tool.name,
                    description=tool.description,
                    input_schema=schema,
                )
            )
        return schemas

    async def dispatch(
        self,
        name: str,
        arguments: str,
        active_names: tuple[str, ...],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Validate and execute one tool call. Returns structured result envelope.

        Envelope: {"ok": true, "data": {}} or {"ok": false, "code": "...", "error": "..."}
        """
        # Unknown tool
        if name not in self._tools:
            return {
                "ok": False,
                "code": "unknown_tool",
                "error": safe_tool_error("unknown_tool"),
            }

        # Inactive tool
        if name not in active_names:
            return {
                "ok": False,
                "code": "tool_unavailable",
                "error": safe_tool_error("tool_unavailable"),
            }

        tool = self._tools[name]

        # Parse arguments
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError as exc:
            logger.warning("malformed arguments for %s: %s", name, exc, exc_info=True)
            return {
                "ok": False,
                "code": "invalid_arguments",
                "error": safe_tool_error("invalid_arguments"),
            }

        # Pydantic validation
        try:
            input_obj = tool.input_model.model_validate(args_dict)
        except Exception as exc:
            logger.warning("invalid arguments for %s: %s", name, exc, exc_info=True)
            return {
                "ok": False,
                "code": "invalid_arguments",
                "error": safe_tool_error("invalid_arguments"),
            }

        # Execute handler with context
        try:
            result = await tool.handler(input_obj, context)
        except Exception as exc:
            logger.warning("tool handler error for %s: %s", name, exc, exc_info=True)
            return {
                "ok": False,
                "code": "tool_failed",
                "error": safe_tool_error("tool_failed"),
            }

        # Validate output against the declared output model
        try:
            tool.output_model.model_validate(result)
        except Exception as exc:
            logger.warning("tool output validation failed for %s: %s", name, exc, exc_info=True)
            return {
                "ok": False,
                "code": "invalid_output",
                "error": safe_tool_error("invalid_output"),
            }

        # A handler may return the standard failure envelope directly. This
        # keeps domain failures (notably idempotency conflicts) out of a
        # successful ``data`` object.
        if result.get("ok") is False:
            code = normalize_tool_code(result.get("code"))
            return {
                "ok": False,
                "code": code,
                "error": safe_tool_error(code),
            }

        # Truncate if needed
        result_str = json.dumps(result, default=str)
        if len(result_str) > tool.max_result_chars:
            result_str = result_str[: tool.max_result_chars]
            result = {"_truncated": True, "_raw": result_str}
            return {
                "ok": True,
                "data": result,
            }

        return {
            "ok": True,
            "data": result,
        }
