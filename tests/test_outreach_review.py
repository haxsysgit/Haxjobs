"""Outreach draft review enforcement tests."""

from haxjobs.db import schema
from haxjobs.db.outreach import insert_draft
from haxjobs.db.evaluations import save_evaluation
from haxjobs.db.jobs import insert_job, update_job_pack_status
from haxjobs.server.routes.outreach import (
    approve_draft,
    list_outreach_drafts,
    list_outreach_jobs,
    reject_draft,
    update_draft_status,
)


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "haxjobs.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def add_draft() -> int:
    """Insert a job and a draft, return the draft id."""
    job_id = insert_job(
        title="Test Job",
        company="TestCo",
        location="London",
        jd_text="Test description.",
        source="manual",
    )
    assert job_id is not None
    did = insert_draft(job_id, "Test Subject", "Test message text.")
    return did


def test_approve_existing_draft(monkeypatch, tmp_path):
    """Approving a real draft returns ok: true."""
    use_temp_db(monkeypatch, tmp_path)
    did = add_draft()

    result = approve_draft(did)

    assert result["ok"] is True
    assert result["draft_id"] == did
    assert result["status"] == "approved"


def test_reject_existing_draft(monkeypatch, tmp_path):
    """Rejecting a real draft returns ok: true."""
    use_temp_db(monkeypatch, tmp_path)
    did = add_draft()

    result = reject_draft(did, "wrong company")

    assert result["ok"] is True
    assert result["draft_id"] == did
    assert result["status"] == "rejected"
    assert result["reason"] == "wrong company"


def test_approve_missing_draft_returns_error(monkeypatch, tmp_path):
    """Approving a non-existent draft returns ok: false."""
    use_temp_db(monkeypatch, tmp_path)

    result = approve_draft(99999)

    assert result["ok"] is False
    assert "draft not found" in result["error"]


def test_reject_missing_draft_returns_error(monkeypatch, tmp_path):
    """Rejecting a non-existent draft returns ok: false."""
    use_temp_db(monkeypatch, tmp_path)

    result = reject_draft(99999, "no reason")

    assert result["ok"] is False
    assert "draft not found" in result["error"]


def test_update_draft_status_reports_rowcount(monkeypatch, tmp_path):
    """update_draft_status() returns True when a row was affected."""
    use_temp_db(monkeypatch, tmp_path)
    did = add_draft()

    updated = update_draft_status(did, "approved")
    assert updated is True

    # Now try a missing draft — should return False
    missing = update_draft_status(99999, "approved")
    assert missing is False


def test_outreach_job_and_draft_routes_expose_pack_dir(monkeypatch, tmp_path):
    """Outreach list routes include persisted pack_dir as camelCase packDir."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = insert_job(
        title="Python Backend Engineer",
        company="ExampleCo",
        location="London",
        jd_text="Python FastAPI PostgreSQL pytest role.",
        source="manual",
    )
    assert job_id is not None
    save_evaluation(
        job_id,
        {
            "fit_score": 80,
            "fit_verdict": "Strong fit",
            "level": 1,
            "level_name": "Strong fit",
            "summary": "Good backend match.",
            "decision": "completed",
        },
    )
    update_job_pack_status(job_id, "generated", pack_dir="packs/exampleco-python")
    draft_id = insert_draft(job_id, "Subject", "Message")

    outreach_job = next(row for row in list_outreach_jobs() if row["id"] == job_id)
    outreach_draft = next(row for row in list_outreach_drafts() if row["id"] == draft_id)
    filtered_draft = next(row for row in list_outreach_drafts(job_id) if row["id"] == draft_id)

    assert outreach_job["packDir"] == "packs/exampleco-python"
    assert outreach_draft["packDir"] == "packs/exampleco-python"
    assert filtered_draft["packDir"] == "packs/exampleco-python"
