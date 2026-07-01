"""Pagination tests — tested at each layer independently."""
import json
import sqlite3
from unittest.mock import patch


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT '',
            jd_text TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source TEXT DEFAULT 'unknown',
            source_quality TEXT DEFAULT 'unknown',
            status TEXT DEFAULT 'pending',
            role_family TEXT DEFAULT 'unknown',
            role_family_confidence REAL DEFAULT 0,
            recommended_cv_variant TEXT DEFAULT 'unknown',
            role_family_terms TEXT DEFAULT '[]',
            pack_status TEXT DEFAULT 'none',
            pack_dir TEXT DEFAULT '',
            outreach_status TEXT DEFAULT 'none',
            pack_review_status TEXT DEFAULT 'none',
            pack_review_notes TEXT DEFAULT '',
            pack_reviewed_at TEXT,
            classified_at TEXT,
            discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL UNIQUE,
            fit_score INTEGER NOT NULL,
            fit_verdict TEXT NOT NULL,
            level INTEGER NOT NULL,
            level_name TEXT NOT NULL,
            strongest_matches TEXT DEFAULT '[]',
            major_gaps TEXT DEFAULT '[]',
            sponsorship_risk TEXT DEFAULT 'medium',
            summary TEXT DEFAULT '',
            decision TEXT DEFAULT 'completed',
            skip_reason TEXT DEFAULT '',
            role_type TEXT DEFAULT '',
            evaluated_by TEXT DEFAULT 'hermes',
            evaluated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            decided_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    # Seed 25 jobs
    for i in range(25):
        status = "pending" if i < 10 else "evaluated" if i < 20 else "skipped"
        cur = conn.execute("""
            INSERT INTO jobs (title, company, location, source, status, discovered_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', ? || ' minutes'))
        """, (f"Job {i}", f"Company {i}", "London", "test", status, str(-i)))
        job_id = cur.lastrowid
        if status == "evaluated":
            conn.execute("""
                INSERT INTO evaluations (job_id, fit_score, fit_verdict, level, level_name,
                    strongest_matches, major_gaps, sponsorship_risk, summary, decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, 80 - i, "GOOD_FIT", 2, "Quick Apply",
                  json.dumps([]), json.dumps([]), "low", f"Summary {i}", "completed"))
    conn.commit()
    return conn


def test_db_pagination_returns_limited_results():
    """get_jobs_with_evaluations respects limit parameter."""
    import db.evaluations as db_evals

    def make_conn():
        return _fresh_conn()

    with patch.object(db_evals, "get_db", side_effect=make_conn):
        page = db_evals.get_jobs_with_evaluations(limit=10, offset=0)
        assert len(page) == 10
        page2 = db_evals.get_jobs_with_evaluations(limit=10, offset=10)
        assert len(page2) == 10
        ids1 = {r["id"] for r in page}
        ids2 = {r["id"] for r in page2}
        assert ids1.isdisjoint(ids2)


def test_db_pagination_with_status_filter():
    import db.evaluations as db_evals

    def make_conn():
        return _fresh_conn()

    with patch.object(db_evals, "get_db", side_effect=make_conn):
        result = db_evals.get_jobs_with_evaluations(status_filter="pending", limit=5, offset=0)
        assert len(result) <= 5
        for r in result:
            assert r["status"] == "pending"


def test_db_no_limit_returns_all():
    import db.evaluations as db_evals

    def make_conn():
        return _fresh_conn()

    with patch.object(db_evals, "get_db", side_effect=make_conn):
        result = db_evals.get_jobs_with_evaluations()
        assert len(result) == 25


def test_list_jobs_passes_params_to_db_layer():
    """list_jobs forwards status_filter, offset, limit to get_jobs_with_evaluations."""
    import db.evaluations as db_evals

    fake_raw = [{
        "id": 1, "title": "T", "company": "C", "location": "", "source": "test",
        "source_quality": "direct", "role_family": "backend_python",
        "role_family_confidence": 1.0, "recommended_cv_variant": "backend_python",
        "pack_status": "none", "pack_review_status": "none",
        "pack_review_notes": "", "pack_reviewed_at": None,
        "outreach_status": "none", "fit_score": 80, "fit_verdict": "GOOD_FIT",
        "level": 2, "level_name": "Quick Apply", "strongest_matches": [],
        "major_gaps": [], "sponsorship_risk": "low", "summary": "",
        "eval_decision": "completed", "skip_reason": "", "role_type": "backend",
        "evaluated_by": "test", "evaluated_at": "", "status": "pending",
        "discovered_at": "", "pack_dir": "",
    }]
    captured_kwargs = {}

    def fake_get_jobs(**kwargs):
        captured_kwargs.update(kwargs)
        return fake_raw

    with patch.object(db_evals, "get_jobs_with_evaluations", fake_get_jobs):
        from server.routes.jobs import list_jobs
        result = list_jobs(status_filter="pending", offset=5, limit=20)
        assert captured_kwargs == {"status_filter": "pending", "offset": 5, "limit": 20}
        assert len(result) == 1


def test_list_jobs_backward_compat_no_args():
    """list_jobs() with no args still works (backward compat)."""
    import db.evaluations as db_evals

    def fake_get_jobs(**kwargs):
        return []

    with patch.object(db_evals, "get_jobs_with_evaluations", fake_get_jobs):
        from server.routes.jobs import list_jobs
        result = list_jobs()
        assert result == []
