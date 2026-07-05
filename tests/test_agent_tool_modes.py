"""Tool mode tests — verify mode resolution and Agent integration."""
import os

import pytest

from haxjobs.agent.agent import Agent
from haxjobs.agent.tool_modes import TOOL_MODES, tools_for_mode


def test_evaluation_mode_returns_evaluate_fit_not_web_search():
    tools = tools_for_mode("evaluation")
    assert "evaluate_fit" in tools
    assert "web_search" not in tools
    assert "db_query" not in tools
    assert "profile_read" in tools


def test_admin_mode_includes_db_query():
    tools = tools_for_mode("admin")
    assert "db_query" in tools
    assert "profile_read" in tools
    assert "profile_schema" in tools


def test_unknown_mode_raises_value_error():
    with pytest.raises(ValueError, match="Unknown tool mode"):
        tools_for_mode("nonexistent_mode")


def test_all_modes_in_tool_modes_table():
    """Every mode name in TOOL_MODES must resolve via tools_for_mode."""
    for mode in TOOL_MODES:
        tools = tools_for_mode(mode)
        assert isinstance(tools, list)
        assert len(tools) > 0, f"Mode {mode} has empty tool list"


def test_agent_tool_mode_sets_tools(monkeypatch):
    """Agent(tool_mode='decision') should set tools to ['record_decision']."""
    def fake_load_config(self):
        return {
            "provider": {
                "api_key": os.getenv("DEEPSEEK_API_KEY", "test-key"),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
            }
        }

    monkeypatch.setattr(Agent, "_load_config", fake_load_config)
    agent = Agent(tool_mode="decision")
    assert agent.tools == ["record_decision"]


def test_agent_explicit_tools_wins_over_tool_mode(monkeypatch):
    """When both tools and tool_mode are given, explicit tools should win."""
    def fake_load_config(self):
        return {
            "provider": {
                "api_key": os.getenv("DEEPSEEK_API_KEY", "test-key"),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
            }
        }

    monkeypatch.setattr(Agent, "_load_config", fake_load_config)
    agent = Agent(tools=["profile_read", "profile_write"], tool_mode="decision")
    assert agent.tools == ["profile_read", "profile_write"]
