"""Tests for evaluate_fit in product_tools."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def seeded_job(test_db):
    from haxjobs.db.jobs import insert_job
    job_id = insert_job(
        title="Backend Engineer",
        company="TestCo",
        location="London",
        jd_text="Python, FastAPI, PostgreSQL",
        source="test",
    )
    assert job_id is not None
    return job_id


FAKE_EVAL_RESULT = {
    "fit_score": 82,
    "fit_verdict": "STRONG_FIT",
    "level": 1,
    "level_name": "Standard",
    "strongest_matches": ["Python", "FastAPI"],
    "major_gaps": ["No DevOps"],
    "sponsorship_risk": "low",
    "summary": "Good fit.",
    "decision": "completed",
    "skip_reason": "",
}


def _mock_agent_run(return_text: str = ""):
    """Return a mock that simulates Agent().run()."""
    import json

    text = return_text or json.dumps(FAKE_EVAL_RESULT)

    def _run(self, prompt, temperature=0.3, max_tokens=4096, system=None):
        return text

    return _run


def test_evaluate_missing_job_returns_job_not_found():
    from haxjobs.product_tools import evaluate_fit

    result = evaluate_fit(99999)
    assert result["ok"] is False
    assert result["code"] == "job_not_found"


def test_evaluate_valid_job_saves_result(seeded_job):
    from haxjobs.db.evaluations import get_evaluation
    from haxjobs.product_tools import evaluate_fit

    with (
        patch("haxjobs.product_tools.generate_pack") as mock_pack,
        patch.object(
            __import__("haxjobs.agent", fromlist=["Agent"]).Agent,
            "run",
            _mock_agent_run(),
        ),
    ):
        # Make pack return a neutral result
        mock_pack.return_value = {"ok": True, "job_id": seeded_job}

        result = evaluate_fit(seeded_job, auto_generate_pack=False)
        assert result["ok"] is True
        assert result["fit_score"] == 82
        assert result["level"] == 1

        evaluation = get_evaluation(seeded_job)
        assert evaluation is not None
        assert evaluation["fit_score"] == 82


def test_evaluate_l1_triggers_auto_pack(seeded_job):
    from haxjobs.product_tools import evaluate_fit

    with (
        patch.object(
            __import__("haxjobs.agent", fromlist=["Agent"]).Agent,
            "run",
            _mock_agent_run(),
        ),
        patch("haxjobs.product_tools.generate_pack") as mock_pack,
    ):
        mock_pack.return_value = {"ok": True, "job_id": seeded_job, "pack_dir": "packs/test", "files": [], "metadata": {}}

        result = evaluate_fit(seeded_job, auto_generate_pack=True)
        assert result["ok"] is True
        assert result["pack"] is not None
        assert result["pack"]["ok"] is True
        mock_pack.assert_called_once_with(seeded_job)


def test_evaluate_l3_skips_auto_pack(seeded_job):
    import json
    from haxjobs.product_tools import evaluate_fit

    l3_result = {**FAKE_EVAL_RESULT, "fit_score": 45, "level": 3, "level_name": "Lite", "fit_verdict": "WEAK_FIT"}

    with (
        patch.object(
            __import__("haxjobs.agent", fromlist=["Agent"]).Agent,
            "run",
            _mock_agent_run(json.dumps(l3_result)),
        ),
        patch("haxjobs.product_tools.generate_pack") as mock_pack,
    ):
        result = evaluate_fit(seeded_job, auto_generate_pack=True)
        assert result["ok"] is True
        assert result["level"] == 3
        mock_pack.assert_not_called()


def test_evaluate_invalid_json_returns_error(seeded_job):
    from haxjobs.product_tools import evaluate_fit

    with patch.object(
        __import__("haxjobs.agent", fromlist=["Agent"]).Agent,
        "run",
        _mock_agent_run("not json at all, just random text"),
    ):
        result = evaluate_fit(seeded_job, auto_generate_pack=False)
        assert result["ok"] is False
        assert result["code"] == "invalid_agent_json"
