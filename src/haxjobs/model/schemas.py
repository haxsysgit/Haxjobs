"""Tool schema conversion — HaxJobs ToolSchema to OpenAI JSON schema."""

from __future__ import annotations

from haxjobs.model.types import ToolSchema


def tool_to_openai_schema(tool: ToolSchema) -> dict:
    """Convert a HaxJobs ToolSchema to OpenAI JSON schema dict."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def tools_to_openai_schemas(tools: list[ToolSchema]) -> list[dict]:
    """Convert all tools to OpenAI JSON schema dicts."""
    return [tool_to_openai_schema(t) for t in tools]
