"""Tests for Plan 043 full native agent pieces."""
import json
import socket
from types import SimpleNamespace
from unittest.mock import MagicMock

from haxjobs.agent import (
    Agent,
    TOOLS,
    build_system_prompt,
    dispatch,
    get_schemas,
    load_identity,
    register,
)
from haxjobs.agent.tools_db import db_query
from haxjobs.agent.tools_web import fetch_page


# ── Registry ──────────────────────────────────────────────────────────

def test_registry_register_and_dispatch():
    register(
        "test_echo",
        {"name": "test_echo", "parameters": {"type": "object"}},
        lambda text: {"text": text},
    )
    assert json.loads(dispatch("test_echo", {"text": "hi"})) == {"text": "hi"}


def test_registry_check_fn_gates():
    register(
        "test_unavailable",
        {"name": "test_unavailable", "parameters": {"type": "object"}},
        lambda: "nope",
        check_fn=lambda: False,
    )
    assert "test_unavailable" not in [s["function"]["name"] for s in get_schemas()]
    assert "unavailable" in json.loads(dispatch("test_unavailable", {}))["error"]


def test_get_schemas_allowlist_and_exclude():
    register("test_a", {"name": "test_a", "parameters": {"type": "object"}}, lambda: "a")
    register("test_b", {"name": "test_b", "parameters": {"type": "object"}}, lambda: "b")
    names = [s["function"]["name"] for s in get_schemas(["test_a", "test_b"], ["test_b"])]
    assert names == ["test_a"]
    assert get_schemas([]) == []


def test_builtin_tool_names_registered():
    assert {"web_search", "fetch_page", "db_query"}.issubset(TOOLS)
    assert not {"read", "write", "edit", "bash", "grep", "find", "ls"} & set(TOOLS)


# ── Tools ─────────────────────────────────────────────────────────────

def test_fetch_page_blocks_local_urls():
    assert "localhost" in fetch_page("http://localhost:8241")["error"]
    assert "private/local" in fetch_page("http://127.0.0.1")["error"]


def test_fetch_page_blocks_redirect_to_local_url(monkeypatch):
    import haxjobs.agent.tools_web as tools

    def fake_getaddrinfo(host, *_args, **_kwargs):
        ip = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

    class RedirectingOpener:
        def open(self, _req, timeout=10):
            raise ValueError("blocked unsafe redirect: private/local URLs are not allowed")

    monkeypatch.setattr(tools.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(tools, "build_opener", lambda *_handlers: RedirectingOpener())

    assert "blocked unsafe redirect" in fetch_page("https://example.com/job")["error"]


def test_fetch_page_allows_public_page(monkeypatch):
    import haxjobs.agent.tools_web as tools

    class FakeResponse:
        headers = {"content-type": "text/html; charset=utf-8"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _max_bytes):
            return b"<html><body><h1>Backend job</h1></body></html>"

    class FakeOpener:
        def open(self, _req, timeout=10):
            return FakeResponse()

    monkeypatch.setattr(tools.socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))])
    monkeypatch.setattr(tools, "build_opener", lambda *_handlers: FakeOpener())

    assert fetch_page("https://example.com/job")["text"] == "Backend job"


def test_db_query_read_only(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "haxjobs.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO jobs (title) VALUES ('Engineer')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("haxjobs.config.DB_PATH", db_path, raising=False)
    monkeypatch.setattr("haxjobs.db.schema.DB_PATH", db_path, raising=False)

    ok = db_query("SELECT title FROM jobs")
    assert ok["rows"] == [{"title": "Engineer"}]

    blocked = db_query("UPDATE jobs SET title='Oops'")
    assert "only accepts" in blocked["error"]

    sneaky = db_query("WITH x AS (SELECT 1) DELETE FROM jobs")
    assert "failed" in sneaky["error"]


# ── Prompt/identity ───────────────────────────────────────────────────

def test_build_system_prompt_tiers():
    prompt = build_system_prompt(
        identity="IDENTITY",
        skills_index="SKILLS",
        context_files="CONTEXT",
        memory="MEMORY",
        user_profile="USER",
        platform="cron",
    )
    assert prompt.index("IDENTITY") < prompt.index("# Project context") < prompt.index("## Memory")
    assert "Running unattended" in prompt


def test_load_identity_default(monkeypatch, tmp_path):
    monkeypatch.setattr("haxjobs.agent.identity.HAXJOBS_HOME", tmp_path)
    assert "job search agent" in load_identity()


# ── run_with_tools ────────────────────────────────────────────────────

def _agent_with_responses(monkeypatch, responses):
    fake_cfg = {"provider": {"api_key": "k", "base_url": "https://api.test", "model": "test"}}
    monkeypatch.setattr(Agent, "_load_config", staticmethod(lambda: fake_cfg))
    mock_client = MagicMock()
    mock_create = MagicMock(side_effect=responses)
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr("haxjobs.agent.agent.OpenAI", MagicMock(return_value=mock_client))
    agent = Agent(tools=["test_echo"])
    agent._mock_create = mock_create
    return agent


def _response(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))])


def _tool_call(name="test_echo", arguments='{"text":"hi"}'):
    return SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_run_with_tools_single_turn(monkeypatch):
    agent = _agent_with_responses(monkeypatch, [_response("final", None)])
    assert agent.run_with_tools("hello") == "final"
    assert agent._mock_create.call_count == 1


def test_run_with_tools_one_tool_cycle(monkeypatch):
    register(
        "test_echo",
        {"name": "test_echo", "parameters": {"type": "object"}},
        lambda text: {"echo": text},
    )
    agent = _agent_with_responses(
        monkeypatch,
        [_response("", [_tool_call()]), _response("done", None)],
    )

    assert agent.run_with_tools("use tool") == "done"
    second_messages = agent._mock_create.call_args_list[1].kwargs["messages"]
    assert second_messages[-1]["role"] == "tool"
    assert json.loads(second_messages[-1]["content"]) == {"echo": "hi"}


def test_max_turns_exhausted(monkeypatch):
    register(
        "test_echo",
        {"name": "test_echo", "parameters": {"type": "object"}},
        lambda text: text,
    )
    agent = _agent_with_responses(monkeypatch, [_response("", [_tool_call()])])
    assert "Max tool turns" in agent.run_with_tools("loop", max_turns=1)
