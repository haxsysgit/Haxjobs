"""Tests for the Greenhouse discovery scraper."""

from __future__ import annotations

from haxjobs.db.discovered_jobs import get_discovered_job, insert_discovered_job
from haxjobs.discovery.normalize import normalize_job


def sample_greenhouse_job(**overrides) -> dict:
    """Build a realistic Greenhouse API job payload."""
    job = {
        "id": 1234567,
        "title": "Backend Software Engineer",
        "location": {"name": "London, UK"},
        "absolute_url": "https://boards.greenhouse.io/example/jobs/1234567",
        "content": "&lt;div id=&quot;content&quot;&gt;&lt;p&gt;Build Python APIs.&lt;/p&gt;&lt;/div&gt;",
        "departments": [{"name": "Engineering"}],
    }
    job.update(overrides)
    return job


def test_normalize_greenhouse_job() -> None:
    """Greenhouse job payloads map into the canonical discovered job shape."""
    from haxjobs.discovery.scrapers.greenhouse import build_raw_job

    raw_job = build_raw_job("datadog", sample_greenhouse_job())
    normalized = normalize_job(raw_job, source="greenhouse")

    assert normalized["title"] == "Backend Software Engineer"
    assert normalized["company"] == "datadog"
    assert normalized["location"] == "London, UK"
    assert normalized["source_url"] == "https://boards.greenhouse.io/example/jobs/1234567"
    assert normalized["apply_url"] == "https://boards.greenhouse.io/example/jobs/1234567"
    assert normalized["external_id"] == "1234567"
    assert normalized["ats"] == "greenhouse"
    assert normalized["source"] == "greenhouse"
    assert "Build Python APIs." in normalized["jd_text"]


def test_greenhouse_jd_parsing() -> None:
    """Greenhouse escaped HTML descriptions become clean readable text."""
    from haxjobs.discovery.scrapers.greenhouse import extract_jd_text

    html_text = """
    &lt;div id=&quot;content&quot;&gt;
        &lt;h2&gt;About the role&lt;/h2&gt;
        &lt;p&gt;Build APIs and backend services.&lt;/p&gt;
        &lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;li&gt;SQLite&lt;/li&gt;&lt;/ul&gt;
    &lt;/div&gt;
    """

    jd_text = extract_jd_text(html_text)

    assert "About the role" in jd_text
    assert "Build APIs and backend services." in jd_text
    assert "Python" in jd_text
    assert "SQLite" in jd_text
    assert "<" not in jd_text
    assert ">" not in jd_text


def test_insert_greenhouse_job(test_db: str) -> None:
    """A normalized Greenhouse job can be inserted into discovered_jobs."""
    from haxjobs.discovery.scrapers.greenhouse import build_raw_job

    raw_job = build_raw_job("datadog", sample_greenhouse_job())
    normalized = normalize_job(raw_job, source="greenhouse")
    row_id = insert_discovered_job(normalized)

    assert row_id is not None

    discovered_job = get_discovered_job(row_id)
    assert discovered_job is not None
    assert discovered_job["source"] == "greenhouse"
    assert discovered_job["ats"] == "greenhouse"
    assert discovered_job["company"] == "datadog"
    assert discovered_job["title"] == "Backend Software Engineer"
    assert discovered_job["external_id"] == "1234567"
    assert "Build Python APIs." in discovered_job["jd_text"]


def test_greenhouse_profile_filter_skips_unmatched_titles() -> None:
    """Greenhouse filtering keeps target roles and drops unrelated roles."""
    from haxjobs.discovery.scrapers.greenhouse import filter_profile_jobs

    jobs = [
        sample_greenhouse_job(title="Backend Engineer"),
        sample_greenhouse_job(title="Account Executive", id=999),
    ]

    matched_jobs = filter_profile_jobs(jobs, ["backend"])

    assert [job["title"] for job in matched_jobs] == ["Backend Engineer"]
