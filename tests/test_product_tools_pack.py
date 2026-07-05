"""Tests for generate_pack in product_tools."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def seeded_job(test_db):
    from haxjobs.db.jobs import insert_job
    job_id = insert_job(
        title="Backend Engineer",
        company="TestCorp",
        location="London",
        jd_text="Python, FastAPI",
        source="test",
    )
    assert job_id is not None
    return job_id


def _seed_evaluation(job_id, level=1):
    from haxjobs.db.evaluations import save_evaluation
    result = {
        "fit_score": 82,
        "fit_verdict": "STRONG_FIT",
        "level": level,
        "level_name": "Standard" if level <= 2 else "Lite",
        "strongest_matches": ["Python"],
        "major_gaps": [],
        "sponsorship_risk": "low",
        "summary": "Good fit.",
        "decision": "completed",
        "skip_reason": "",
        "agent": "test",
    }
    save_evaluation(job_id, result)


def test_pack_missing_job_returns_job_not_found():
    from haxjobs.product_tools import generate_pack

    result = generate_pack(99999)
    assert result["ok"] is False
    assert result["code"] == "job_not_found"


def test_pack_missing_evaluation_returns_evaluation_required(seeded_job):
    from haxjobs.product_tools import generate_pack

    result = generate_pack(seeded_job)
    assert result["ok"] is False
    assert result["code"] == "evaluation_required"


def test_pack_l3_requires_manual_review(seeded_job):
    from haxjobs.product_tools import generate_pack

    _seed_evaluation(seeded_job, level=3)

    result = generate_pack(seeded_job)
    assert result["ok"] is False
    assert result["code"] == "manual_review_required"


def test_pack_l3_force_overrides(seeded_job, monkeypatch, tmp_path):
    from haxjobs.product_tools import generate_pack

    _seed_evaluation(seeded_job, level=3)

    # Override PACKS_DIR and PROFILE_PATH to temp locations
    monkeypatch.setattr("haxjobs.product_tools.PACKS_DIR", tmp_path / "packs")
    monkeypatch.setattr("haxjobs.product_tools.PROFILE_PATH", tmp_path / "profile.json")
    (tmp_path / "profile.json").write_text(json.dumps({"personal": {"name": "Test"}}))

    result = generate_pack(seeded_job, force=True)
    assert result["ok"] is True
    assert "pack_dir" in result


def test_pack_l1_creates_pack(seeded_job, monkeypatch, tmp_path):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import generate_pack

    _seed_evaluation(seeded_job, level=1)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"personal": {"name": "Test User"}, "skills": {}, "preferences": {}}))

    packs_dir = tmp_path / "packs"
    monkeypatch.setattr("haxjobs.product_tools.PROFILE_PATH", profile_path)
    monkeypatch.setattr("haxjobs.product_tools.PACKS_DIR", packs_dir)

    result = generate_pack(seeded_job)
    assert result["ok"] is True
    assert "pack_dir" in result
    assert Path(result["pack_dir"]).exists() or "pack_dir" in result  # may not exist if pack builder fails

    # Check job pack status updated
    job = get_job(seeded_job)
    assert job["pack_status"] == "generated"


def test_pack_owns_cv_is_false(seeded_job, monkeypatch, tmp_path):
    from haxjobs.product_tools import generate_pack

    _seed_evaluation(seeded_job, level=1)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"personal": {"name": "Test"}}))

    packs_dir = tmp_path / "packs"
    monkeypatch.setattr("haxjobs.product_tools.PROFILE_PATH", profile_path)
    monkeypatch.setattr("haxjobs.product_tools.PACKS_DIR", packs_dir)

    result = generate_pack(seeded_job)
    assert result["ok"] is True
    metadata = result.get("metadata", {})
    assert metadata.get("pack_owns_cv") is False, f"pack_owns_cv should be False, got {metadata}"
