"""Tests for the discovery ingestion spine — dedup, blacklist, filter, and promotion.

Every job enters HaxJobs through ``discovered_jobs`` before promotion to the
main ``jobs`` table. These tests verify that the full ingestion pipeline works
correctly for manual and scraped jobs alike.
"""

from __future__ import annotations

import os

# -------- helpers --------


def init_temp_db(tmp_path, monkeypatch):
    """Initialize a temporary SQLite database and patch DB_PATH.

    We monkeypatch ``db.schema.DB_PATH`` directly because
    ``haxjobs_config.DB_PATH`` is evaluated at import time and cannot
    be changed via ``setenv`` mid-session.
    """
    import db.schema as schema_mod
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(schema_mod, "DB_PATH", db_path)
    schema_mod.init()
    return db_path


def make_discovered_job(**overrides) -> dict:
    """Build a realistic discovered job record dict."""
    defaults = dict(
        source="manual",
        source_url="https://example.com/jobs/1",
        title="Software Engineer",
        company="ExampleCorp",
        location="London, UK",
        jd_text="Build and maintain web services.",
    )
    defaults.update(overrides)
    return defaults


# -------- tests --------


def test_duplicate_source_url_rejected(tmp_path, monkeypatch):
    """Duplicate source_url cannot create a second accepted discovered job."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import insert_discovered_job, find_duplicate

    r1 = insert_discovered_job(make_discovered_job(source_url="https://ex.com/job1"))
    assert r1 is not None, "First insert should succeed"

    r2 = insert_discovered_job(make_discovered_job(
        source_url="https://ex.com/job1",
        title="Different Title",
        company="Different Co",
    ))
    assert r2 is None, "Duplicate source_url should be rejected"

    assert find_duplicate({"source_url": "https://ex.com/job1"}) is not None


def test_duplicate_company_title_rejected(tmp_path, monkeypatch):
    """Same company+title (case-insensitive) is rejected even with different URL."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import insert_discovered_job

    r1 = insert_discovered_job(make_discovered_job(
        source_url="https://a.com/job",
        company="Acme Inc",
        title="Backend Engineer",
    ))
    assert r1 is not None

    r2 = insert_discovered_job(make_discovered_job(
        source_url="https://b.com/job",
        company="acme inc",
        title="backend engineer",
    ))
    assert r2 is None, "Case-insensitive company+title dup should be rejected"


def test_blacklisted_company_rejected(tmp_path, monkeypatch):
    """Blacklisted company gets discovery_status='blacklisted' and is not promoted."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import insert_discovered_job, get_discovered_job, promote_discovered_job
    from discovery.hooks import should_accept_discovered_job

    record = make_discovered_job(
        company="Robert Half",
        title="IT Consultant",
        source_url="https://roberthalf.com/job1",
    )
    accepted, reason = should_accept_discovered_job(record)
    assert accepted is False
    assert reason == "blacklisted"

    rec_id = insert_discovered_job(record)
    assert rec_id is not None

    # Simulate discover-run logic: update status and attempt promotion
    from db.discovered_jobs import update_discovery_status
    update_discovery_status(rec_id, "blacklisted", reason)
    dj = get_discovered_job(rec_id)
    assert dj["discovery_status"] == "blacklisted"

    job_id = promote_discovered_job(rec_id)
    assert job_id is None, "Blacklisted job should not promote"


def test_obvious_non_tech_role_filtered(tmp_path, monkeypatch):
    """Obvious non-tech role gets discovery_status='filtered'."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import insert_discovered_job, get_discovered_job, promote_discovered_job
    from discovery.hooks import should_accept_discovered_job

    record = make_discovered_job(
        title="Barista",
        company="Starbucks",
        source_url="https://starbucks.com/job1",
    )
    accepted, reason = should_accept_discovered_job(record)
    assert accepted is False
    assert reason == "filtered"

    rec_id = insert_discovered_job(record)
    assert rec_id is not None

    from db.discovered_jobs import update_discovery_status
    update_discovery_status(rec_id, "filtered", reason)
    dj = get_discovered_job(rec_id)
    assert dj["discovery_status"] == "filtered"

    job_id = promote_discovered_job(rec_id)
    assert job_id is None, "Filtered job should not promote"


def test_manual_and_scraped_same_normalization_path(tmp_path, monkeypatch):
    """Manual job and scraped job use the same normalization path."""
    init_temp_db(tmp_path, monkeypatch)
    from discovery.normalize import normalize_job

    # Simulate a manual entry
    manual_raw = {
        "title": "Senior SWE",
        "company": "Google",
        "location": "Mountain View",
        "source_url": "https://careers.google.com/jobs/1",
        "jd_text": "Build search.",
    }
    manual = normalize_job(manual_raw, source="manual")

    # Simulate a greenhouse scraper result
    scraper_raw = {
        "title": "Senior SWE",
        "org": "Google",
        "office": "Mountain View",
        "url": "https://careers.google.com/jobs/1",
        "body": "Build search.",
        "id": "gh_1",
    }
    scraped = normalize_job(scraper_raw, source="greenhouse")

    # Both produce the same canonical keys, even if values differ
    for key in ("title", "company", "location", "jd_text", "source_url", "external_id", "source"):
        assert key in manual, f"Manual missing {key}"
        assert key in scraped, f"Scraped missing {key}"

    assert scraped["source"] == "greenhouse"
    assert scraped["external_id"] == "gh_1"


def test_accepted_discovered_job_promotes(tmp_path, monkeypatch):
    """A discovered job that passes hooks gets promoted into the jobs table."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import (
        insert_discovered_job, get_discovered_job,
        update_discovery_status, promote_discovered_job,
    )
    from db.jobs import get_job
    from discovery.hooks import should_accept_discovered_job
    from discovery.normalize import normalize_job

    raw = make_discovered_job(
        title="ML Engineer",
        company="OpenAI",
        source_url="https://openai.com/careers/ml",
        jd_text="Train large language models.",
    )
    norm = normalize_job(raw)
    rec_id = insert_discovered_job(norm)
    assert rec_id is not None

    accepted, reason = should_accept_discovered_job(norm)
    assert accepted is True
    assert reason == "accepted"

    update_discovery_status(rec_id, "accepted")
    job_id = promote_discovered_job(rec_id)
    assert job_id is not None, "Accepted job should promote"

    # Check the promoted job
    job = get_job(job_id)
    assert job is not None
    assert job["title"] == "ML Engineer"
    assert job["company"] == "OpenAI"
    assert job["status"] == "pending"

    # Check discovered job status updated
    dj = get_discovered_job(rec_id)
    assert dj["discovery_status"] == "promoted"
    assert dj["promoted_job_id"] == job_id


def test_discover_run_processes_new_jobs(tmp_path, monkeypatch):
    """``discover-run`` (simulated) processes new jobs, accepts valid ones, rejects others."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import (
        insert_discovered_job, list_discovered_jobs,
        update_discovery_status, promote_discovered_job,
    )
    from db.jobs import get_all_jobs
    from discovery.hooks import should_accept_discovered_job

    # Insert a mix
    insert_discovered_job(make_discovered_job(
        source_url="https://good.com/1", title="SDE", company="GoodCo"))
    insert_discovered_job(make_discovered_job(
        source_url="https://bad.com/1", title="Driver", company="Uber"))
    insert_discovered_job(make_discovered_job(
        source_url="https://bad.com/2", title="Consultant", company="Robert Half"))
    insert_discovered_job(make_discovered_job(
        source_url="https://good.com/2", title="Data Analyst", company="Meta"))

    # Simulate discover-run
    new_jobs = list_discovered_jobs(status="new")
    assert len(new_jobs) == 4

    accepted_count = 0
    rejected_count = 0
    for dj in new_jobs:
        accepted, reason = should_accept_discovered_job(dj)
        if not accepted:
            update_discovery_status(dj["id"], reason, reason)
            rejected_count += 1
        else:
            update_discovery_status(dj["id"], "accepted")
            promote_discovered_job(dj["id"])
            accepted_count += 1

    assert accepted_count == 2, f"Expected 2 accepted, got {accepted_count}"
    assert rejected_count == 2, f"Expected 2 rejected, got {rejected_count}"

    all_jobs = get_all_jobs()
    assert len(all_jobs) == 2, "Only 2 jobs should be in main table"


def test_insert_discovered_job_preserves_raw_payload(tmp_path, monkeypatch):
    """raw_payload_json stores the full original record."""
    init_temp_db(tmp_path, monkeypatch)
    from db.discovered_jobs import insert_discovered_job, get_discovered_job
    from discovery.normalize import normalize_job

    raw = {
        "title": "Full Stack Dev",
        "company": "StartupXYZ",
        "source_url": "https://startupxyz.com/careers/fs",
        "jd_text": "Full stack React+Python.",
        "extra_field": "should be preserved",
        "nested": {"key": "value"},
    }
    norm = normalize_job(raw)
    rec_id = insert_discovered_job(norm)
    assert rec_id is not None

    dj = get_discovered_job(rec_id)
    import json
    stored = json.loads(dj["raw_payload_json"])
    assert stored["extra_field"] == "should be preserved"
    assert stored["nested"]["key"] == "value"


# -------- location preference filter --------


def test_location_filter_london_passes():
    """Jobs in London pass the location filter."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("London, UK") is True
    assert passes_location_filter("London, United Kingdom") is True
    assert passes_location_filter("London, England") is True


def test_location_filter_manchester_leeds_pass():
    """Jobs in Manchester or Leeds pass the location filter."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("Manchester, UK") is True
    assert passes_location_filter("Leeds, United Kingdom") is True


def test_location_filter_remote_passes():
    """Remote jobs pass only when paired with UK or preferred location."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("Remote UK") is True
    assert passes_location_filter("Remote, UK") is True
    assert passes_location_filter("London, UK (Remote)") is True
    assert passes_location_filter("Manchester, Remote") is True
    # "Remote" alone without UK → reject
    assert passes_location_filter("Remote") is False
    assert passes_location_filter("Remote, USA") is False
    assert passes_location_filter("Remote, Germany") is False


def test_location_filter_nyc_rejected():
    """Jobs in New York (no UK/remote) are rejected."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("New York, New York, USA") is False
    assert passes_location_filter("Sao Paulo, Brazil") is False
    assert passes_location_filter("Tokyo, Japan") is False
    assert passes_location_filter("Paris, France") is False


def test_location_filter_empty_passes():
    """Empty location passes — let classifier/eval handle it."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("") is True
    assert passes_location_filter("   ") is True


def test_location_filter_uk_variants_pass():
    """Various UK spelling/casing passes."""
    from discovery.hooks import passes_location_filter

    assert passes_location_filter("Edinburgh, Scotland") is True
    assert passes_location_filter("Cardiff, Wales") is True
    assert passes_location_filter("Bristol, GB") is True
    assert passes_location_filter("London, GREAT BRITAIN") is True
    assert passes_location_filter("Cambridge, uk") is True


def test_should_accept_rejects_wrong_location(tmp_path, monkeypatch):
    """should_accept_discovered_job rejects non-UK locations during discovery."""
    init_temp_db(tmp_path, monkeypatch)
    from discovery.hooks import should_accept_discovered_job
    from discovery.normalize import normalize_job

    # Good job: London
    good = normalize_job(make_discovered_job(
        title="Python Backend Engineer", company="GoodCo",
        source_url="https://good.com/1", location="London, UK"))
    accepted, reason = should_accept_discovered_job(good)
    assert accepted is True, f"Expected accepted, got {reason}"

    # Bad location: NYC
    bad = normalize_job(make_discovered_job(
        title="Python Backend Engineer", company="GoodCo",
        source_url="https://good.com/2", location="New York, USA"))
    accepted, reason = should_accept_discovered_job(bad)
    assert accepted is False
    assert "location" in reason
