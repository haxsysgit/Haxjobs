"""Tests for the Ashby discovery scraper."""

from __future__ import annotations

from haxjobs.db.discovered_jobs import get_discovered_job, insert_discovered_job
from haxjobs.discovery.normalize import normalize_job


def sample_ashby_job(**overrides) -> dict:
    """Build a realistic Ashby job detail payload."""
    job = {
        "id": "ashby_123",
        "title": "Backend Engineer",
        "locationName": "London",
        "secondaryLocations": [{"locationName": "Remote UK"}],
        "employmentType": "FullTime",
        "descriptionHtml": "<h2>Role</h2><p>Build Python APIs.</p>",
    }
    job.update(overrides)
    return job


def test_normalize_ashby_job() -> None:
    """Ashby job payloads map into the canonical discovered job shape."""
    from haxjobs.discovery.scrapers.ashby import build_raw_job

    raw_job = build_raw_job("notion", sample_ashby_job())
    normalized = normalize_job(raw_job, source="ashby")

    assert normalized["title"] == "Backend Engineer"
    assert normalized["company"] == "notion"
    assert normalized["location"] == "London, Remote UK"
    assert normalized["source_url"] == "https://jobs.ashbyhq.com/notion/ashby_123"
    assert normalized["apply_url"] == "https://jobs.ashbyhq.com/notion/ashby_123"
    assert normalized["external_id"] == "ashby_123"
    assert normalized["ats"] == "ashby"
    assert normalized["source"] == "ashby"
    assert "Build Python APIs." in normalized["jd_text"]


def test_ashby_jd_cleanup() -> None:
    """Ashby HTML descriptions become clean readable text."""
    from haxjobs.discovery.scrapers.greenhouse import extract_jd_text

    jd_text = extract_jd_text("<h2>About</h2><p>Build backend systems.</p>")

    assert jd_text == "About Build backend systems."
    assert "<" not in jd_text
    assert ">" not in jd_text


def test_insert_ashby_job(test_db: str) -> None:
    """A normalized Ashby job can be inserted into discovered_jobs."""
    from haxjobs.discovery.scrapers.ashby import build_raw_job

    raw_job = build_raw_job("notion", sample_ashby_job())
    normalized = normalize_job(raw_job, source="ashby")
    row_id = insert_discovered_job(normalized)

    assert row_id is not None
    discovered_job = get_discovered_job(row_id)
    assert discovered_job is not None
    assert discovered_job["source"] == "ashby"
    assert discovered_job["ats"] == "ashby"
    assert discovered_job["company"] == "notion"
    assert discovered_job["title"] == "Backend Engineer"
    assert discovered_job["external_id"] == "ashby_123"


def test_ashby_profile_filter_skips_unmatched_titles() -> None:
    """Ashby filtering happens before detail fetches and inserts."""
    from haxjobs.discovery.scrapers.ashby import filter_profile_jobs

    jobs = [
        sample_ashby_job(title="AI Engineer"),
        sample_ashby_job(title="Customer Success Manager", id="ashby_999"),
    ]

    matched_jobs = filter_profile_jobs(jobs, ["ai engineer"])

    assert [job["title"] for job in matched_jobs] == ["AI Engineer"]
