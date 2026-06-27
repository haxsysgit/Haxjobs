import sqlite3

from db import schema
from db.jobs import get_job, insert_job


ROLE_COLUMNS = {
    "source_quality",
    "role_family",
    "role_family_confidence",
    "recommended_cv_variant",
    "role_family_terms",
    "pack_status",
    "pack_dir",
    "outreach_status",
    "classified_at",
}


def use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    return db_path


def test_schema_creates_role_and_workflow_columns(monkeypatch, tmp_path):
    db_path = use_temp_db(monkeypatch, tmp_path)

    schema.init()

    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    conn.close()
    assert ROLE_COLUMNS.issubset(columns)


def test_schema_migrates_existing_jobs_table(monkeypatch, tmp_path):
    db_path = use_temp_db(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT '',
            jd_text TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source TEXT DEFAULT 'unknown',
            status TEXT DEFAULT 'pending',
            discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

    schema.init()

    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    conn.close()
    assert ROLE_COLUMNS.issubset(columns)


def test_insert_job_classifies_role_family_and_cv_variant(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    schema.init()

    job_id = insert_job(
        title="Python Developer",
        company="ExampleCo",
        jd_text="Build FastAPI services with PostgreSQL, SQLAlchemy and Redis.",
        source="telegram",
    )

    job = get_job(job_id)
    assert job is not None
    assert job["role_family"] == "backend_python"
    assert job["recommended_cv_variant"] == "backend_python"
    assert job["role_family_confidence"] > 0
    assert "python" in job["role_family_terms"].lower()
    assert job["pack_status"] == "none"
    assert job["pack_dir"] == ""
    assert job["outreach_status"] == "none"
