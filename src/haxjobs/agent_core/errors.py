"""Stable user-facing error messages for the runtime boundary.

Exception objects and provider/tool payloads are for local logs only.  This
module is the one mapping from internal failure categories to text that may be
returned in a TurnResult or LiveEvent.
"""

from __future__ import annotations


_MESSAGES = {
    "user_message_persistence": "user message persistence failed.",
    "host_setup": "Host/context setup failed.",
    "history_read": "Session history read failed.",
    "history_corrupt": "Session history is corrupted.",
    "tool_schema": "Active tool schema setup failed.",
    "model": "Model stream failed.",
    "assistant_persistence": "Assistant message persistence failed.",
    "tool_call_persistence": "Tool call persistence failed.",
    "tool_result_persistence": "Tool result persistence failed.",
    "tool_unavailable": "The requested tool is unavailable.",
    "tool_invalid_arguments": "The tool request was invalid.",
    "tool_failed": "The tool could not be completed.",
    "tool_invalid_output": "The tool returned an invalid result.",
    "idempotency_conflict": "Idempotency conflict.",
    "interrupted": "The turn was interrupted.",
    "limit": "The turn reached its execution limit.",
    "settlement": "Turn settlement persistence failed.",
    "measurement": "Turn measurement persistence failed.",
    "turn": "The turn could not be completed.",
}


def safe_error(category: str) -> str:
    """Return stable text for a failure category, never exception text."""
    return _MESSAGES.get(category, _MESSAGES["turn"])


def safe_tool_error(code: str) -> str:
    """Map a tool result code to text safe for events and provider projection."""
    if code in {"unknown_tool", "tool_inactive"}:
        return safe_error("tool_unavailable")
    if code in {"malformed_arguments", "invalid_arguments"}:
        return safe_error("tool_invalid_arguments")
    if code == "invalid_output":
        return safe_error("tool_invalid_output")
    if code == "idempotency_conflict":
        return safe_error("idempotency_conflict")
    return safe_error("tool_failed")


SAFE_ERROR_TEXT = frozenset(_MESSAGES.values())
"""The complete allowlist of runtime-generated public error strings."""
