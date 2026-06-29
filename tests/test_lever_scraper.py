"""Tests for the Lever discovery scraper."""

from __future__ import annotations

from db.discovered_jobs import get_discovered_job, insert_discovered_job
from discovery.normalize import normalize_job


def sample_lever_job(**overrides) -> dict:
    """Build a realistic Lever posting payload."""
    job = {
        "id": "lever_123",
        "text": "Backend Engineer",
        "categories": {"location": "London", "team": "Engineering"},
        "hostedUrl": "https://jobs.lever.co/example/lever_123",
        "applyUrl": "https://jobs.lever.co/example/lever_123/apply",
        "descriptionPlain": "Build Python APIs and backend services.",
        "description": "<p>Build Python APIs and backend services.</p>",
    }
    job.update(overrides)
    return job


def test_normalize_lever_job() -> None:
    """Lever posting payloads map into the canonical discovered job shape."""
    from discovery.scrapers.lever import build_raw_job

    raw_job = build_raw_job("spotify", sample_lever_job())
    normalized = normalize_job(raw_job, source="lever")

    assert normalized["title"] == "Backend Engineer"
    assert normalized["company"] == "spotify"
    assert normalized["location"] == "London"
    assert normalized["source_url"] == "https://jobs.lever.co/example/lever_123"
    assert normalized["apply_url"] == "https://jobs.lever.co/example/lever_123/apply"
    assert normalized["external_id"] == "lever_123"
    assert normalized["ats"] == "lever"
    assert normalized["source"] == "lever"
    assert normalized["jd_text"] == "Build Python APIs and backend services."


def test_lever_jd_cleanup_prefers_plain_text() -> None:
    """Lever descriptionPlain is used before HTML description."""
    from discovery.scrapers.lever import get_jd_text

    jd_text = get_jd_text(sample_lever_job(descriptionPlain=" Plain text JD. "))

    assert jd_text == "Plain text JD."


def test_insert_lever_job(test_db: str) -> None:
    """A normalized Lever job can be inserted into discovered_jobs."""
    from discovery.scrapers.lever import build_raw_job

    raw_job = build_raw_job("spotify", sample_lever_job())
    normalized = normalize_job(raw_job, source="lever")
    row_id = insert_discovered_job(normalized)

    assert row_id is not None
    discovered_job = get_discovered_job(row_id)
    assert discovered_job is not None
    assert discovered_job["source"] == "lever"
    assert discovered_job["ats"] == "lever"
    assert discovered_job["company"] == "spotify"
    assert discovered_job["title"] == "Backend Engineer"
    assert discovered_job["external_id"] == "lever_123"
