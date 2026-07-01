"""Tests for evaluator agent selection and the evaluate/ package.

Verifies agent chain resolution, adapter imports, and base adapter behavior.
Parsing/validation tests unchanged from original.
"""
from __future__ import annotations


# ── Agent chain tests ────────────────────────────────────────

def test_chain_imports():
    """Chain module imports cleanly."""
    from haxjobs.evaluate.chain import evaluate_one_job, evaluate_batch, _resolve_order
    assert callable(evaluate_one_job)
    assert callable(evaluate_batch)
    assert callable(_resolve_order)


def test_all_adapters_import():
    """All 5 adapters import and inherit BaseAdapter."""
    from haxjobs.evaluate.agents import AGENT_LIST
    from haxjobs.evaluate.agents.base import BaseAdapter

    assert len(AGENT_LIST) == 5
    for name, adapter in AGENT_LIST.items():
        assert isinstance(adapter, BaseAdapter), f"{name} not BaseAdapter"
        assert adapter.name == name


def test_auto_discover_returns_list():
    """auto_discover returns a list of installed agent names."""
    from haxjobs.evaluate.agents import auto_discover

    discovered = auto_discover()
    assert isinstance(discovered, list)
    # Pi is always available
    assert "pi" in discovered


def test_resolve_order_respects_config():
    """_resolve_order returns the configured agent chain."""
    from haxjobs.evaluate.chain import _resolve_order
    from haxjobs.config import EVALUATION_AGENT

    order = _resolve_order()
    assert isinstance(order, list)
    if EVALUATION_AGENT:
        assert EVALUATION_AGENT in order


def test_evaluate_one_job_accepts_agent_order():
    """evaluate_one_job accepts an explicit agent_order override."""
    from haxjobs.evaluate.chain import evaluate_one_job

    # Empty order — no agents tried, returns None
    result = evaluate_one_job(
        {
            "title": "Test",
            "company": "TestCorp",
            "location": "Remote",
            "jd_text": "Python role.",
            "source_url": "http://example.com",
        },
        agent_order=[],
    )
    assert result is None


# ── Parsing / validation tests (unchanged) ──────────────────

def test_extract_json_from_backtick_fence():
    """JSON inside ```json fences is extracted."""
    from haxjobs.evaluate.common import extract_json

    text = '```json\n{"fit_score": 85, "level": 1}\n```'
    result = extract_json(text)
    assert result == {"fit_score": 85, "level": 1}


def test_extract_json_from_plain_text():
    """JSON block anywhere in text is found."""
    from haxjobs.evaluate.common import extract_json

    text = 'Some commentary here.\n{"fit_score": 72, "fit_verdict": "GOOD_FIT"}\nMore text.'
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 72


def test_extract_json_returns_none_for_garbage():
    """Garbage text returns None."""
    from haxjobs.evaluate.common import extract_json

    result = extract_json("not json at all")
    assert result is None


def test_validate_result_passes_valid():
    """A fully valid result has no issues."""
    from haxjobs.evaluate.common import validate_result

    valid = {
        "fit_score": 75,
        "fit_verdict": "GOOD_FIT",
        "level": 2,
        "level_name": "Quick Apply",
        "strongest_matches": ["Python", "FastAPI"],
        "major_gaps": ["No cloud experience"],
        "sponsorship_risk": "low",
        "summary": "Good fit for the role.",
        "decision": "completed",
        "skip_reason": "",
    }
    issues = validate_result(valid)
    assert issues == []


def test_validate_result_catches_missing_key():
    """Missing required key is reported."""
    from haxjobs.evaluate.common import validate_result

    result = {"fit_score": 75}
    issues = validate_result(result)
    assert len(issues) > 0
    assert any("Missing key" in i for i in issues)


def test_validate_result_catches_wrong_type():
    """Wrong type is reported."""
    from haxjobs.evaluate.common import validate_result

    result = {
        "fit_score": "seventy-five",
        "fit_verdict": "GOOD_FIT",
        "level": 2,
        "level_name": "Quick Apply",
        "strongest_matches": [],
        "major_gaps": [],
        "sponsorship_risk": "low",
        "summary": "ok",
        "decision": "completed",
        "skip_reason": "",
    }
    issues = validate_result(result)
    assert any("fit_score" in i for i in issues)


def test_validate_result_catches_out_of_range():
    """Out-of-range values are reported."""
    from haxjobs.evaluate.common import validate_result

    for bad_score in (-1, 101):
        result = {
            "fit_score": bad_score,
            "fit_verdict": "SKIP",
            "level": 1,
            "level_name": "Standard",
            "strongest_matches": [],
            "major_gaps": [],
            "sponsorship_risk": "medium",
            "summary": "bad",
            "decision": "completed",
            "skip_reason": "",
        }
        issues = validate_result(result)
        assert any("fit_score out of range" in i for i in issues)

    for bad_level in (0, 5):
        result = {
            "fit_score": 50,
            "fit_verdict": "GOOD_FIT",
            "level": bad_level,
            "level_name": "Standard",
            "strongest_matches": [],
            "major_gaps": [],
            "sponsorship_risk": "medium",
            "summary": "bad",
            "decision": "completed",
            "skip_reason": "",
        }
        issues = validate_result(result)
        assert any("level out of range" in i for i in issues)
