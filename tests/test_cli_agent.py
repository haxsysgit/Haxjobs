"""CLI smoke tests for native agent playground."""
from haxjobs import cli


class FakeAgent:
    calls = []

    def __init__(self, tools=None):
        self.tools = tools

    def run(self, prompt, system=None):
        self.calls.append(("run", prompt, system, None))
        return "plain-answer"

    def run_with_tools(self, prompt, system=None, max_turns=5):
        self.calls.append(("tools", prompt, system, max_turns, self.tools))
        return "tool-answer"


def test_agent_ask_plain(monkeypatch, capsys):
    FakeAgent.calls.clear()
    monkeypatch.setattr("haxjobs.agent.Agent", FakeAgent)

    cli.main(["agent", "ask", "--plain", "what", "jobs?"])

    assert capsys.readouterr().out.strip() == "plain-answer"
    assert FakeAgent.calls == [("run", "what jobs?", None, None)]


def test_agent_ask_with_tools(monkeypatch, capsys):
    FakeAgent.calls.clear()
    monkeypatch.setattr("haxjobs.agent.Agent", FakeAgent)
    monkeypatch.setattr("haxjobs.agent.load_identity", lambda: "identity")
    monkeypatch.setattr(
        "haxjobs.agent.build_system_prompt",
        lambda identity, context_files="": f"{identity}|{context_files}",
    )

    cli.main([
        "agent",
        "ask",
        "--tools",
        "web_search,fetch_page",
        "--max-turns",
        "2",
        "find",
        "jobs",
    ])

    assert capsys.readouterr().out.strip() == "tool-answer"
    assert FakeAgent.calls == [
        ("tools", "find jobs", "identity|", 2, ["web_search", "fetch_page"])
    ]
