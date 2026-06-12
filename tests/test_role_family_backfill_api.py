import json

from db import schema
from db.jobs import get_job, insert_job
from db.decisions import record_decision
from server.routes.jobs import list_jobs


def use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    return db_path


def test_backfill_classifies_existing_unclassified_jobs(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    schema.init()
    job_id = insert_job(
        title="Data Mining Python Developer",
        company="ExampleCo",
        jd_text="Python SQL Tableau analytics and data mining.",
        source="manual",
    )

    conn = schema.get_db()
    conn.execute(
        """
        UPDATE jobs
        SET role_family='unknown', role_family_confidence=0,
            recommended_cv_variant='unknown', role_family_terms='[]', classified_at=NULL
        WHERE id=?
        """,
        (job_id,),
    )
    conn.commit()
    conn.close()

    from db.role_classification import classify_existing_jobs

    summary = classify_existing_jobs()

    job = get_job(job_id)
    assert summary["classified"] == 1
    assert job is not None
    assert job["role_family"] == "data_python"
    assert job["recommended_cv_variant"] == "data_python"
    assert job["classified_at"]


def test_list_jobs_exposes_role_family_and_cv_variant(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    schema.init()
    job_id = insert_job(
        title="Forward Deployed AI Engineer",
        company="ExampleCo",
        jd_text="LLM workflows, applied AI, and customer engineering.",
        source="lever_api",
    )

    jobs = list_jobs()

    row = next(job for job in jobs if int(job["id"]) == job_id)
    assert row["roleFamily"] == "ai_engineer_llm"
    assert row["recommendedCvVariant"] == "ai_engineer_llm"
    assert row["roleFamilyConfidence"] > 0
    assert row["packStatus"] == "none"
    assert row["outreachStatus"] == "none"
    assert row["isAutoApply"] is False


def test_list_jobs_exposes_current_auto_apply_toggle_state(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    schema.init()
    job_id = insert_job(
        title="Python Backend Engineer",
        company="ExampleCo",
        jd_text="Python FastAPI services.",
        source="manual",
    )

    record_decision(job_id, "auto_apply", "test enable")
    enabled = next(job for job in list_jobs() if int(job["id"]) == job_id)
    assert enabled["isAutoApply"] is True

    record_decision(job_id, "auto_apply_remove", "test disable")
    disabled = next(job for job in list_jobs() if int(job["id"]) == job_id)
    assert disabled["isAutoApply"] is False
