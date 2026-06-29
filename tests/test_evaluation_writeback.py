"""Tests for evaluation decision default and DB writeback consistency."""

from db import schema
from db.jobs import insert_job
from db.evaluations import save_evaluation, get_evaluation


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "haxjobs.db"
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


def test_new_fields_saved(monkeypatch, tmp_path):
    """Plan 018: agent, pack_dir, report_markdown, and cycle fields are persisted."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Test Job",
        company="TestCo",
        location="London",
        jd_text="Some description.",
        source="manual",
    )

    result = {
        "fit_score": 82,
        "fit_verdict": "STRONG_FIT",
        "level": 1,
        "level_name": "Standard",
        "strongest_matches": ["Python", "FastAPI"],
        "major_gaps": [],
        "summary": "Great fit.",
        "agent": "hermes",
        "report_markdown": "# Cycle Report\nJob was great.",
        "pack_dir": "packs/TestCo_Python_Backend_Engineer",
        "pack_template_id": "backend_python",
        "report_cycle_id": "cycle-2026-06-29",
    }

    save_evaluation(job_id, result)
    eval_row = get_evaluation(job_id)

    assert eval_row["agent"] == "hermes"
    assert eval_row["report_markdown"] == "# Cycle Report\nJob was great."
    assert eval_row["pack_dir"] == "packs/TestCo_Python_Backend_Engineer"
    assert eval_row["pack_template_id"] == "backend_python"
    assert eval_row["report_cycle_id"] == "cycle-2026-06-29"


def test_old_result_dict_still_works(monkeypatch, tmp_path):
    """Plan 018: old result dict without new keys saves without errors."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Test Job",
        company="TestCo",
        location="London",
        jd_text="Some description.",
        source="manual",
    )

    # Old-style result — no agent, pack_dir, or report fields
    result = {
        "fit_score": 75,
        "fit_verdict": "GOOD_FIT",
        "level": 2,
        "level_name": "Quick Apply",
        "strongest_matches": ["Python"],
        "major_gaps": [],
        "summary": "OK fit.",
    }

    save_evaluation(job_id, result)
    eval_row = get_evaluation(job_id)

    assert eval_row is not None
    assert eval_row["fit_score"] == 75
    assert eval_row["decision"] == "completed"  # default
    # New fields should be empty defaults
    assert eval_row["agent"] == "hermes"  # falls back to EVALUATION_AGENT
    assert eval_row["report_markdown"] == ""
    assert eval_row["pack_dir"] == ""
    assert eval_row["pack_template_id"] == ""
    assert eval_row["report_cycle_id"] == ""


def test_agent_defaults_to_evaluation_agent(monkeypatch, tmp_path):
    """Plan 018: agent defaults to configured EVALUATION_AGENT when not provided."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Test Job", company="TestCo", location="London",
        jd_text="Desc.", source="manual",
    )

    # No agent field at all
    result = {
        "fit_score": 70, "fit_verdict": "GOOD_FIT",
        "level": 2, "level_name": "Quick Apply",
        "strongest_matches": [], "major_gaps": [], "summary": "ok",
    }
    save_evaluation(job_id, result)
    eval_row = get_evaluation(job_id)
    # haxjobs.toml says agent = "hermes"
    assert eval_row["agent"] == "hermes"
