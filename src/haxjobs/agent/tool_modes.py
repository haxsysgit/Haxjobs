"""Tool modes — group tools by workflow context.

Each mode defines which tools an agent sees when run in that context.
This keeps the LLM from wandering into irrelevant tools:
evaluation sees evaluate_fit but not web_search or db_query.
"""

TOOL_MODES: dict[str, list[str]] = {
    "profile": ["profile_read", "profile_write", "profile_schema", "profile_gaps"],
    "discovery": ["discover_jobs", "profile_read", "web_search", "fetch_page"],
    "evaluation": ["evaluate_fit", "profile_read"],
    "application": ["generate_pack", "profile_read"],
    "decision": ["record_decision"],
    "admin": ["db_query", "profile_read", "profile_schema"],
}


def tools_for_mode(mode: str) -> list[str]:
    """Return the tool name list for a named workflow mode.

    Raises ValueError for unknown modes so callers don't silently
    fall back to an empty tool list.
    """
    try:
        return list(TOOL_MODES[mode])
    except KeyError as exc:
        raise ValueError(f"Unknown tool mode: {mode}") from exc
