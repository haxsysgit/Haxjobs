"""Explicit tool registry and active-set enforcement — no auto-discovery or plugins."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from pydantic import BaseModel

from haxjobs.model.types import ToolSchema

logger = logging.getLogger(__name__)

HandlerFunc = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


@dataclass
class ToolDefinition:
    """One registered tool — name, schema, handler, and resource limits."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: HandlerFunc
    max_result_chars: int = 12_000


class ToolRegistry:
    """Explicit registry — no import-time discovery.

    Tools are registered by name. Duplicate registration raises ValueError.
    Dispatch receives the active set and enforces membership.
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
    ) -> dict[str, Any]:
        """Validate and execute one tool call. Returns structured result envelope.

        Envelope: {"ok": true, "data": {}} or {"ok": false, "code": "...", "error": "..."}
        """
        # Unknown tool
        if name not in self._tools:
            return {
                "ok": False,
                "code": "unknown_tool",
                "error": f"unknown tool: {name}",
            }

        # Inactive tool
        if name not in active_names:
            return {
                "ok": False,
                "code": "tool_inactive",
                "error": f"tool {name} is not in the active set",
            }

        tool = self._tools[name]

        # Parse arguments
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "code": "malformed_arguments",
                "error": f"invalid JSON arguments: {exc}",
            }

        # Pydantic validation
        try:
            input_obj = tool.input_model.model_validate(args_dict)
        except Exception as exc:
            return {
                "ok": False,
                "code": "invalid_arguments",
                "error": f"argument validation failed: {exc}",
            }

        # Execute handler
        try:
            result = await tool.handler(input_obj)
        except Exception as exc:
            logger.warning("tool handler error for %s: %s", name, exc)
            return {
                "ok": False,
                "code": "handler_error",
                "error": "tool execution failed",
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
