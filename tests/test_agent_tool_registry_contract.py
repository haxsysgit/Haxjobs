"""Contract tests — lock the tool registry shape so plan drift is caught early."""
import haxjobs.agent.tools  # noqa: F401 - triggers all register() calls
from haxjobs.agent.registry import TOOLS


EXPECTED_TOOLS = {
    "web_search", "fetch_page", "db_query",
    "profile_read", "profile_write", "profile_schema", "profile_gaps",
    "discover_jobs", "evaluate_fit", "generate_pack", "record_decision",
    "find_contacts", "draft_message", "analyze_patterns",
}


def test_expected_tools_are_registered():
    """Every product, support, and future tool must be in the registry."""
    actual = set(TOOLS)
    missing = EXPECTED_TOOLS - actual
    assert not missing, f"Missing tools: {missing}"


def test_all_tool_schemas_have_name_description_and_parameters():
    """Every expected tool must expose a valid schema for the LLM."""
    for name in EXPECTED_TOOLS:
        tool = TOOLS[name]
        schema = tool.schema
        assert schema.get("name") == name, f"{name}: schema.name mismatch"
        assert schema.get("description"), f"{name}: missing description"
        params = schema.get("parameters", {})
        assert params.get("type") == "object", f"{name}: parameters.type must be 'object'"


def test_product_tool_stubs_respond_with_error_shape():
    """FUTURE stubs must return structured error dicts.

    BUILD tools (discover_jobs, evaluate_fit, generate_pack, record_decision)
    are now implemented via product_tools and require DB access. Only FUTURE
    stubs are checked for the error contract.
    """
    from haxjobs.agent.tools_product import (
        find_contacts, draft_message, analyze_patterns,
    )
    import json

    for name, handler in [
        ("find_contacts", find_contacts),
        ("draft_message", draft_message),
        ("analyze_patterns", analyze_patterns),
    ]:
        result = json.loads(handler())
        assert result["ok"] is False, f"{name}: FUTURE stub should return ok=False"
        assert result["code"] == "future_tool", f"{name}: FUTURE stub code mismatch"
        assert "error" in result, f"{name}: missing error key"
