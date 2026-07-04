from __future__ import annotations


def _job(**overrides):
    data = {
        "source": "manual",
        "source_url": "https://example.com/jobs/1",
        "external_id": "job-1",
        "title": "Python Backend Engineer",
        "company": "ExampleCo",
        "location": "London, UK",
        "jd_text": "Build Python APIs with FastAPI and PostgreSQL.",
    }
    data.update(overrides)
    return data


def test_duplicate_insert_does_not_poison_original_status(test_db):
    from haxjobs.db.discovered_jobs import get_discovered_job, insert_discovered_job

    row_id = insert_discovered_job(_job())
    assert row_id is not None

    duplicate_id = insert_discovered_job(_job(title="Different title"))

    assert duplicate_id is None
    assert get_discovered_job(row_id)["discovery_status"] == "new"


def test_promote_uses_classified_job_insert_path(test_db):
    from haxjobs.db.discovered_jobs import get_discovered_job, insert_discovered_job, promote_discovered_job, update_discovery_status
    from haxjobs.db.jobs import get_job

    row_id = insert_discovered_job(_job())
    update_discovery_status(row_id, "accepted")

    job_id = promote_discovered_job(row_id)

    job = get_job(job_id)
    assert job is not None
    assert job["role_family"] != "unknown"
    assert job["recommended_cv_variant"] != "unknown"
    assert get_discovered_job(row_id)["promoted_job_id"] == job_id


def test_promote_url_collision_links_existing_job_without_stale_lastrowid(test_db):
    from haxjobs.db.discovered_jobs import get_discovered_job, insert_discovered_job, promote_discovered_job, update_discovery_status
    from haxjobs.db.jobs import insert_job

    existing_job_id = insert_job(
        "Python Backend Engineer",
        "ExampleCo",
        location="London, UK",
        jd_text="Build Python APIs.",
        source_url="https://example.com/jobs/1",
        source="manual",
    )
    row_id = insert_discovered_job(_job(external_id="different-external-id"))
    update_discovery_status(row_id, "accepted")

    promoted_id = promote_discovered_job(row_id)

    assert promoted_id == existing_job_id
    assert get_discovered_job(row_id)["promoted_job_id"] == existing_job_id
