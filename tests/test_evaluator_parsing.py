"""Tests for evaluator JSON parsing and validation on evaluate.common.

Tests extract_json() and validate_result() directly — no Hermes calls.
"""

from haxjobs.evaluate.common import extract_json, validate_result


# ── extract_json ──

def test_parses_raw_json_object():
    result = extract_json('{"fit_score": 82, "fit_verdict": "STRONG_FIT"}')
    assert result is not None
    assert result["fit_score"] == 82


def test_parses_fenced_json_block():
    text = '```json\n{"fit_score": 75, "level": 2}\n```'
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 75


def test_parses_fenced_block_without_json_tag():
    text = '```\n{"fit_score": 60}\n```'
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 60


def test_extracts_later_valid_json_after_invalid_json_object():
    """When an invalid JSON object appears first, the later valid one wins."""
    text = (
        'noise {"fit_score": } still broken\n'
        '{"fit_score": 50, "decision": "completed"}\n'
        'more noise'
    )
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 50


def test_returns_none_for_no_json():
    result = extract_json("just some text, no braces here")
    assert result is None


def test_returns_none_for_empty_string():
    result = extract_json("")
    assert result is None


def test_parses_hermes_box_wrapper():
    """Hermes CLI wraps output in box-drawing characters."""
    text = (
        "╭─ ⚕ Hermes ────────────────────────────────╮\n"
        '    {"fit_score": 88, "fit_verdict": "STRONG_FIT"}\n'
        "╰────────────────────────────────────────────╯"
    )
    result = extract_json(text)
    assert result is not None
    assert result["fit_score"] == 88


# ── validate_result ──

def build_valid_result(overrides=None):
    """Build a minimal valid evaluation result for testing the validator."""
    base = {
        "fit_score": 75,
        "fit_verdict": "GOOD_FIT",
        "level": 2,
        "level_name": "Quick Apply",
        "strongest_matches": ["Python", "FastAPI"],
        "major_gaps": ["No cloud experience"],
        "sponsorship_risk": "low",
        "summary": "Good match.",
        "decision": "completed",
        "skip_reason": "",
    }
    if overrides:
        base.update(overrides)
    return base


def test_validates_complete_result():
    result = build_valid_result()
    issues = validate_result(result)
    assert issues == []


def test_reports_missing_key():
    result = build_valid_result()
    del result["fit_score"]
    issues = validate_result(result)
    assert any("Missing key: fit_score" in i for i in issues)


def test_reports_wrong_type():
    result = build_valid_result({"fit_score": "eighty"})
    issues = validate_result(result)
    assert any("Wrong type for fit_score" in i for i in issues)


def test_reports_out_of_range_score():
    result = build_valid_result({"fit_score": 150})
    issues = validate_result(result)
    assert any("fit_score out of range" in i for i in issues)


def test_reports_out_of_range_level():
    result = build_valid_result({"level": 5})
    issues = validate_result(result)
    assert any("level out of range" in i for i in issues)


def test_allows_boundary_score_values():
    """0 and 100 are valid scores."""
    for score in (0, 100):
        result = build_valid_result({"fit_score": score})
        issues = validate_result(result)
        assert issues == [], f"score {score} should be valid"


def test_multiple_issues_reported():
    """When multiple fields are bad, all are reported."""
    result = build_valid_result({"fit_score": "bad", "level": 0})
    issues = validate_result(result)
    assert len(issues) >= 2
