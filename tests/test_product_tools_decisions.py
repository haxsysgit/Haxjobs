"""Tests for record_decision in product_tools."""
from __future__ import annotations

import pytest


@pytest.fixture
def seeded_job(test_db):
    """Insert a job row and return its id."""
    from haxjobs.db.jobs import insert_job
    job_id = insert_job(
        title="Backend Engineer",
        company="TestCo",
        location="London",
        source="test",
    )
    assert job_id is not None
    return job_id


def test_record_apply_normalizes_and_updates_status(seeded_job):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "Apply", "Good fit")
    assert result["ok"] is True
    assert result["decision"] == "apply"
    assert result["decision_id"] is not None
    assert result["decision_id"] > 0

    job = get_job(seeded_job)
    assert job["status"] == "applied"


def test_record_maybe(seeded_job):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "Maybe")
    assert result["ok"] is True
    assert result["decision"] == "maybe"

    job = get_job(seeded_job)
    assert job["status"] == "maybe"


def test_record_save(seeded_job):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "Save")
    assert result["ok"] is True
    assert result["decision"] == "save"

    job = get_job(seeded_job)
    assert job["status"] == "saved"


def test_record_skip(seeded_job):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "Skip")
    assert result["ok"] is True
    assert result["decision"] == "skip"

    job = get_job(seeded_job)
    assert job["status"] == "skipped"


def test_record_reject(seeded_job):
    from haxjobs.db.jobs import get_job
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "Reject", "Wrong stack")
    assert result["ok"] is True
    assert result["decision"] == "reject"

    job = get_job(seeded_job)
    assert job["status"] == "rejected"


def test_record_missing_job_returns_job_not_found():
    from haxjobs.product_tools import record_decision

    result = record_decision(99999, "apply")
    assert result["ok"] is False
    assert result["code"] == "job_not_found"


def test_record_unknown_decision_returns_invalid_decision(seeded_job):
    from haxjobs.product_tools import record_decision

    result = record_decision(seeded_job, "accept")
    assert result["ok"] is False
    assert result["code"] == "invalid_decision"


def test_all_five_decisions(seeded_job):
    """Verify all five canonical decision labels work and map to correct statuses."""
    from haxjobs.db.jobs import get_job, insert_job
    from haxjobs.product_tools import record_decision

    expected = [
        ("apply", "applied"),
        ("maybe", "maybe"),
        ("save", "saved"),
        ("skip", "skipped"),
        ("reject", "rejected"),
    ]

    for decision, status in expected:
        job_id = insert_job(
            title=f"Job {decision}",
            company="TestCo",
            location="London",
            source="test",
        )
        assert job_id is not None

        result = record_decision(job_id, decision)
        assert result["ok"] is True, f"Failed for {decision}: {result}"
        assert result["decision"] == decision

        job = get_job(job_id)
        assert job["status"] == status, f"Expected status {status} for {decision}, got {job['status']}"
