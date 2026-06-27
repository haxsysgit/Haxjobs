"""LinkedIn cache importer regression tests."""

import json
import sys
from pathlib import Path

# cron/ is not a package, so add repo root and import the module by path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import schema

# Import the importer module
from cron import import_linkedin_jobs as _importer

main = _importer.main


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def test_import_preserves_company_name(monkeypatch, tmp_path):
    """Imported company should match the cache entry, not default to 'LinkedIn'."""
    use_temp_db(monkeypatch, tmp_path)

    cache = tmp_path / "test_cache.json"
    cache.write_text(json.dumps([
        {
            "title": "Python Backend Engineer",
            "company": "ExampleCo",
            "location": "London",
            "url": "https://linkedin.com/jobs/view/123",
        },
    ]))

    main(str(cache))

    conn = schema.get_db()
    rows = conn.execute(
        "SELECT id, company, title, source FROM jobs WHERE source='linkedin_local'"
    ).fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["company"] == "ExampleCo"
    assert rows[0]["title"] == "Python Backend Engineer"


def test_import_fallback_when_company_missing(monkeypatch, tmp_path):
    """If company field is missing from cache, default to 'Unknown'."""
    use_temp_db(monkeypatch, tmp_path)

    cache = tmp_path / "test_cache.json"
    cache.write_text(json.dumps([
        {
            "title": "Mystery Role",
            "location": "Remote",
            "url": "https://linkedin.com/jobs/view/456",
        },
    ]))

    main(str(cache))

    conn = schema.get_db()
    row = conn.execute(
        "SELECT company FROM jobs WHERE source='linkedin_local'"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["company"] == "Unknown"


def test_import_multiple_jobs_preserves_all_companies(monkeypatch, tmp_path):
    """Multiple jobs each keep their own company."""
    use_temp_db(monkeypatch, tmp_path)

    cache = tmp_path / "test_cache.json"
    cache.write_text(json.dumps([
        {"title": "Job A", "company": "CompanyA", "location": "London", "url": "https://example.com/a"},
        {"title": "Job B", "company": "CompanyB", "location": "Manchester", "url": "https://example.com/b"},
        {"title": "Job C", "company": "CompanyC", "location": "Remote", "url": "https://example.com/c"},
    ]))

    main(str(cache))

    conn = schema.get_db()
    rows = conn.execute(
        "SELECT company FROM jobs WHERE source='linkedin_local' ORDER BY id"
    ).fetchall()
    conn.close()

    assert len(rows) == 3
    assert [r["company"] for r in rows] == ["CompanyA", "CompanyB", "CompanyC"]
