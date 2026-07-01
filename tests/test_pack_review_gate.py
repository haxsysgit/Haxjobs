"""Pack review gate tests.

Slice 5 locks the review lifecycle for generated application packs.
"""

from __future__ import annotations

from haxjobs.db import schema
from haxjobs.db.decisions import get_decisions
from haxjobs.db.jobs import get_job, insert_job, update_job_pack_status
from haxjobs.db.pack_review import get_pack_review, review_pack
from haxjobs.server.routes.jobs import list_jobs, review_job_pack


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "haxjobs.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def add_generated_job() -> int:
    """Create a job that already has a generated pack."""
    job_id = insert_job(
        title="Python Backend Engineer",
        company="ExampleCo",
        location="London",
        jd_text="Python FastAPI PostgreSQL pytest role.",
        source="manual",
    )
    update_job_pack_status(job_id, "generated")
    return job_id


def test_review_pack_approves_generated_pack(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()

    result = review_pack(job_id, "approve", "Looks good after manual review")

    assert result["ok"] is True
    assert result["pack_status"] == "reviewed_approved"
    assert get_job(job_id)["pack_status"] == "reviewed_approved"
    assert get_pack_review(job_id)["review_notes"] == "Looks good after manual review"
    assert get_pack_review(job_id)["reviewed_at"]
    assert get_decisions(job_id)[0]["decision"] == "pack_review_approved"


def test_review_pack_rejects_generated_pack(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()

    result = review_pack(job_id, "reject", "Cover letter is too stiff")

    assert result["ok"] is True
    assert result["pack_status"] == "reviewed_rejected"
    assert get_job(job_id)["pack_status"] == "reviewed_rejected"
    assert get_pack_review(job_id)["review_notes"] == "Cover letter is too stiff"
    assert get_decisions(job_id)[0]["decision"] == "pack_review_rejected"


def test_review_pack_can_request_changes(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()

    result = review_pack(job_id, "changes", "Mention FastAPI earlier")

    assert result["ok"] is True
    assert result["pack_status"] == "review_changes_requested"
    assert get_job(job_id)["pack_status"] == "review_changes_requested"
    assert get_decisions(job_id)[0]["decision"] == "pack_review_changes_requested"


def test_review_pack_rejects_invalid_action(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()

    result = review_pack(job_id, "ship-it", "Nope")

    assert result["ok"] is False
    assert "Invalid review action" in result["error"]
    assert get_job(job_id)["pack_status"] == "generated"


def test_list_jobs_exposes_pack_review_fields(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()
    review_pack(job_id, "approve", "Ready")

    row = next(job for job in list_jobs() if int(job["id"]) == job_id)

    assert row["packStatus"] == "reviewed_approved"
    assert row["packReviewStatus"] == "approved"
    assert row["packReviewNotes"] == "Ready"
    assert row["packReviewedAt"]


def test_review_job_pack_api_validates_job_id(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)

    status, payload = review_job_pack({"action": "approve"})

    assert status == 400
    assert payload["error"] == "job_id required"


def test_review_job_pack_api_returns_review_result(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()

    status, payload = review_job_pack({"job_id": job_id, "action": "approve", "notes": "Ready"})

    assert status == 200
    assert payload["ok"] is True
    assert payload["pack_status"] == "reviewed_approved"


def test_review_pack_rejects_job_with_no_pack(monkeypatch, tmp_path):
    """A job with pack_status='none' cannot be reviewed."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = insert_job(
        title="No Pack Job",
        company="TestCo",
        location="London",
        jd_text="No pack generated yet.",
        source="manual",
    )

    result = review_pack(job_id, "approve", "Trying to approve with no pack")

    assert result["ok"] is False
    assert "no pack to review" in result["error"]


def test_review_pack_allows_changes_requested_review(monkeypatch, tmp_path):
    """A pack in 'review_changes_requested' state can be reviewed again."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()
    review_pack(job_id, "changes", "Fix the cover letter")

    # Now approve the revised pack
    result = review_pack(job_id, "approve", "Fixed version looks good")

    assert result["ok"] is True
    assert result["pack_status"] == "reviewed_approved"


def test_review_pack_rejects_already_approved_pack(monkeypatch, tmp_path):
    """Once approved, a pack cannot be re-approved."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_generated_job()
    review_pack(job_id, "approve", "First approval")

    result = review_pack(job_id, "approve", "Second approval attempt")

    assert result["ok"] is False
    assert "no pack to review" in result["error"]
