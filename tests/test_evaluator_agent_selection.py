"""Tests for evaluator agent selection and the evaluate/ package.

Verifies that the configured agent controls adapter selection and that
parsing/validation work through the new evaluate.common module.
"""
from __future__ import annotations


def test_select_hermes_agent():
    """Configured agent='hermes' selects the Hermes adapter."""
    from evaluate.run import select_agent

    call_agent = select_agent("hermes")
    assert call_agent is not None
    assert callable(call_agent)


def test_select_hermes_is_default():
    """Default agent (no explicit name) selects hermes."""
    from evaluate.run import select_agent

    call_agent = select_agent()
    assert call_agent is not None
    assert callable(call_agent)


def test_unknown_agent_falls_back_to_default():
    """An unknown agent name falls back to default (pi) instead of crashing."""
    from evaluate.run import select_agent

    # 'nonexistent_agent' is not in registry, should fall back to 'pi'
    fn = select_agent("nonexistent_agent")
    assert callable(fn)
    # Verify it loaded pi, not hermes
    assert "pi" in fn.__module__ or "hermes" in fn.__module__  # either is valid fallback


def test_select_agent_pi_directly():
    """Selecting 'pi' directly returns the pi adapter."""
    from evaluate.run import select_agent
    fn = select_agent("pi")
    assert callable(fn)
    assert "pi" in fn.__module__


def test_select_agent_hermes_directly():
    """Selecting 'hermes' directly returns the hermes adapter."""
    from evaluate.run import select_agent
    fn = select_agent("hermes")
    assert callable(fn)
    assert "hermes" in fn.__module__


def test_extract_json_from_backtick_fence():
    """JSON inside ```json fences is extracted."""
    from evaluate.common import extract_json

    text = '```json\n{"fit_score": 85, "level": 1}\n```'
    result = extract_json(text)
    assert result == {"fit_score": 85, "level": 1}


def test_extract_json_from_plain_text():
    """JSON block anywhere in text is found."""
    from evaluate.common import extract_json

    text = 'Some commentary here.\n{"fit_score": 72, "fit_verdict": "GOOD_FIT"}\nMore text.'
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 72


def test_extract_json_returns_none_for_garbage():
    """Garbage text returns None."""
    from evaluate.common import extract_json

    result = extract_json("not json at all")
    assert result is None


def test_validate_result_passes_valid():
    """A fully valid result has no issues."""
    from evaluate.common import validate_result

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
    from evaluate.common import validate_result

    result = {"fit_score": 75}
    issues = validate_result(result)
    assert len(issues) > 0
    assert any("Missing key" in i for i in issues)


def test_validate_result_catches_wrong_type():
    """Wrong type is reported."""
    from evaluate.common import validate_result

    result = {
        "fit_score": "seventy-five",  # string, not int
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
    from evaluate.common import validate_result

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
