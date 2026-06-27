"""Tests for evaluation decision default and DB writeback consistency."""

from db import schema
from db.jobs import insert_job
from db.evaluations import save_evaluation, get_evaluation


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def test_omitted_decision_defaults_to_completed(monkeypatch, tmp_path):
    """When 'decision' is not in the result dict, it defaults to 'completed'.

    Both the evaluation row and the job status should reflect this.
    """
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Test Job",
        company="TestCo",
        location="London",
        jd_text="Some description.",
        source="manual",
    )

    # Simulate an evaluator result with NO 'decision' key
    result = {
        "fit_score": 80,
        "fit_verdict": "STRONG_FIT",
        "level": 1,
        "level_name": "Standard",
        "strongest_matches": ["Python"],
        "major_gaps": [],
        "summary": "Good fit.",
    }

    save_evaluation(job_id, result)

    # Check evaluation row
    eval_row = get_evaluation(job_id)
    assert eval_row is not None
    assert eval_row["decision"] == "completed"

    # Check job status
    conn = schema.get_db()
    job_row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    assert job_row is not None
    assert job_row["status"] == "evaluated", (
        f"Expected 'evaluated' but got '{job_row['status']}' — "
        "the job was incorrectly marked as skipped"
    )


def test_explicit_skipped_decision_sets_status_correctly(monkeypatch, tmp_path):
    """When decision is 'skipped', the job status becomes 'skipped'."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Test Job",
        company="TestCo",
        location="London",
        jd_text="Some description.",
        source="manual",
    )

    result = {
        "fit_score": 20,
        "fit_verdict": "SKIP",
        "level": 4,
        "level_name": "Skip",
        "strongest_matches": [],
        "major_gaps": ["Requires PhD"],
        "sponsorship_risk": "high",
        "summary": "Not a fit.",
        "decision": "skipped",
        "skip_reason": "Needs citizenship",
    }

    save_evaluation(job_id, result)

    eval_row = get_evaluation(job_id)
    assert eval_row["decision"] == "skipped"

    conn = schema.get_db()
    job_row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    assert job_row["status"] == "skipped"
