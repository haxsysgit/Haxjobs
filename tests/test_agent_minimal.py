"""Tests for the bare-minimum native agent (plan 039)."""
import os
from unittest.mock import MagicMock, patch

from haxjobs.agent import Agent, get_prompt, PromptTemplate, PROMPTS


# ── Prompt template tests ──────────────────────────────────────────────

def test_get_prompt_fills_variables():
    """{profile_json} and {job_json} get filled correctly."""
    system, user = get_prompt(
        "evaluate_job", profile_json='{"name":"Test"}', job_json='{"title":"Dev"}'
    )
    assert "evaluator" in system.lower()
    assert '{"name":"Test"}' in user
    assert '{"title":"Dev"}' in user


def test_get_prompt_missing_variable_raises():
    """KeyError when a template variable is not provided."""
    try:
        get_prompt("evaluate_job")
        assert False, "should have raised"
    except KeyError:
        pass


def test_prompt_registry_has_three_entries():
    """Three named templates: evaluate_job, extract_cv, wizard_question."""
    assert set(PROMPTS.keys()) == {"evaluate_job", "extract_cv", "wizard_question"}
    for t in PROMPTS.values():
        assert isinstance(t, PromptTemplate)
        assert isinstance(t.system, str) and t.system
        assert isinstance(t.user, str) and t.user


# ── Agent config loading tests ────────────────────────────────────────

def test_setup_service_integration(monkeypatch):
    """Agent._load_config() reads from haxjobs.features.setup.service.get_config()."""
    fake_cfg = {"provider": {"api_key": "sk-test", "base_url": "https://test.com", "model": "test-model"}}
    mock_get_config = MagicMock(return_value=fake_cfg)
    monkeypatch.setattr(
        "haxjobs.features.setup.service.get_config", mock_get_config
    )
    cfg = Agent._load_config()
    assert cfg == fake_cfg
    mock_get_config.assert_called_once()


def test_agent_no_config(monkeypatch):
    """Agent._load_config() raises RuntimeError when no config at all."""
    # Simulate setup service unavailable + no env vars
    monkeypatch.setattr(
        "haxjobs.features.setup.service", None, raising=True
    )
    for var in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "HAXJOBS_API_BASE", "HAXJOBS_MODEL"):
        monkeypatch.delenv(var, raising=False)
    try:
        Agent._load_config()
        assert False, "should have raised"
    except RuntimeError as e:
        assert "No provider configured" in str(e)


def test_agent_init_with_timeout(monkeypatch):
    """Agent.__init__ passes timeout=60 to OpenAI client."""
    fake_cfg = {"provider": {"api_key": "sk-x", "base_url": "https://x.com", "model": "m"}}
    monkeypatch.setattr(Agent, "_load_config", staticmethod(lambda: fake_cfg))
    mock_openai_cls = MagicMock()
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    monkeypatch.setattr("haxjobs.agent.agent.OpenAI", mock_openai_cls)

    agent = Agent()
    mock_openai_cls.assert_called_once_with(
        api_key="sk-x", base_url="https://x.com", timeout=60
    )
    assert agent.model == "m"


# ── Agent.run() tests ─────────────────────────────────────────────────

def make_mock_agent(monkeypatch, response_text="hello") -> Agent:
    """Helper: create an Agent with a mocked OpenAI client."""
    fake_cfg = {"provider": {"api_key": "k", "base_url": "https://api.test", "model": "test"}}
    monkeypatch.setattr(Agent, "_load_config", staticmethod(lambda: fake_cfg))
    mock_client = MagicMock()
    mock_create = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_create.return_value.choices = [mock_choice]
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr("haxjobs.agent.agent.OpenAI", MagicMock(return_value=mock_client))
    agent = Agent()
    agent._mock_create = mock_create  # for assertions
    agent._mock_client = mock_client
    return agent


def test_agent_run_returns_raw_text(monkeypatch):
    """run() returns the model's raw text output."""
    agent = make_mock_agent(monkeypatch, "plain response")
    result = agent.run("prompt")
    assert result == "plain response"
    assert agent._mock_create.call_count == 1


def test_agent_run_with_system_message(monkeypatch):
    """run() includes system message when provided."""
    agent = make_mock_agent(monkeypatch, "ok")
    agent.run("do it", system="Be helpful.")
    call_args = agent._mock_create.call_args[1]
    assert call_args["messages"][0] == {"role": "system", "content": "Be helpful."}
    assert call_args["messages"][1] == {"role": "user", "content": "do it"}


def test_agent_run_passes_temperature_and_max_tokens(monkeypatch):
    """run() forwards temperature and max_tokens to the API."""
    agent = make_mock_agent(monkeypatch)
    agent.run("hi", temperature=0.7, max_tokens=512)
    call_args = agent._mock_create.call_args[1]
    assert call_args["temperature"] == 0.7
    assert call_args["max_tokens"] == 512


def test_agent_run_empty_response_returns_empty_string(monkeypatch):
    """run() returns '' when model returns None/empty content."""
    agent = make_mock_agent(monkeypatch, None)
    result = agent.run("x")
    assert result == ""


# ── extract_json integration test ─────────────────────────────────────

def test_agent_run_with_extract_json(monkeypatch):
    """extract_json() from evaluate.common parses fenced JSON from run() output."""
    from haxjobs.evaluate.common import extract_json

    json_text = '```json\n{"fit_score": 85, "level": 2}\n```'
    agent = make_mock_agent(monkeypatch, json_text)
    raw = agent.run("evaluate this job")
    parsed = extract_json(raw)
    assert parsed == {"fit_score": 85, "level": 2}
