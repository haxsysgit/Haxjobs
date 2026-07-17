"""Small tool registry — Python equivalent of Pi's defineTool + dispatch."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

ToolHandler = Callable[..., Any]


@dataclass
class ToolDef:
    name: str
    schema: dict[str, Any]
    handler: ToolHandler
    check_fn: Callable[[], bool] | None = None

    def available(self) -> bool:
        if self.check_fn is None:
            return True
        try:
            return bool(self.check_fn())
        except Exception:
            return False


TOOLS: dict[str, ToolDef] = {}


def register(
    name: str,
    schema: dict[str, Any],
    handler: ToolHandler,
    check_fn: Callable[[], bool] | None = None,
) -> None:
    TOOLS[name] = ToolDef(name=name, schema=schema, handler=handler, check_fn=check_fn)


def get_schemas(
    names: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[dict[str, Any]]:
    allowed = set(names) if names is not None else None
    denied = set(exclude or [])
    out = []
    for name, tool in TOOLS.items():
        if allowed is not None and name not in allowed:
            continue
        if name in denied or not tool.available():
            continue
        out.append({"type": "function", "function": tool.schema})
    return out


def dispatch(name: str, args: dict[str, Any]) -> str:
    tool = TOOLS.get(name)
    if tool is None:
        return json.dumps({"ok": False, "code": "unknown_tool", "error": f"Unknown tool: {name}"})
    if not tool.available():
        return json.dumps({"ok": False, "code": "tool_unavailable", "error": f"Tool unavailable: {name}"})
    try:
        result = tool.handler(**args)
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as exc:
        return json.dumps({"ok": False, "code": "tool_failed", "error": f"Tool {name} failed: {exc}"})
