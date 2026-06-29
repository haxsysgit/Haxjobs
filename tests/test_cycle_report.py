"""Tests for cycle report generation."""

from db.jobs import insert_job
from db.evaluations import save_evaluation


def test_report_renders_job_entries(test_db):
    """Cycle report markdown contains job title, company, score, and URL."""

    job_id = insert_job(
        title="Python Backend Engineer",
        company="TestCo",
        location="London",
        jd_text="FastAPI PostgreSQL.",
        source="manual",
        source_url="https://testco.com/jobs/1",
    )

    result = {
        "fit_score": 82,
        "fit_verdict": "STRONG_FIT",
        "level": 1,
        "level_name": "Standard",
        "strongest_matches": ["Python", "FastAPI"],
        "major_gaps": [],
        "summary": "Great fit.",
    }
    save_evaluation(job_id, result)

    # Generate report
    from cron.generate_cycle_report import _render_report
    l1_l2 = [{
        "id": job_id,
        "title": "Python Backend Engineer",
        "company": "TestCo",
        "fit_score": 82,
        "level": 1,
        "source_url": "https://testco.com/jobs/1",
        "summary": "Great fit.",
    }]
    body = _render_report("test-cycle", l1_l2, [], [])

    assert "## Summary" in body
    assert "Python Backend Engineer" in body
    assert "TestCo" in body
    assert "82%" in body
    assert "L1" in body
    assert "https://testco.com/jobs/1" in body


def test_report_separates_levels(test_db):
    """L3 and L4 jobs appear under their own sections."""

    l1_jobs = [{"id": 1, "title": "A", "company": "X", "fit_score": 85, "level": 1,
                 "source_url": "", "summary": ""}]
    l3_jobs = [{"id": 2, "title": "B", "company": "Y", "fit_score": 45, "level": 3,
                 "source_url": "", "summary": "Needs review."}]
    l4_jobs = [{"id": 3, "title": "C", "company": "Z", "fit_score": 15, "level": 4,
                 "source_url": "", "summary": "Skip."}]

    from cron.generate_cycle_report import _render_report
    body = _render_report("test", l1_jobs, l3_jobs, l4_jobs)

    assert "## L1/L2" in body
    assert "## L3" in body
    assert "## L4" in body

    # L1 section should mention the L1 job title
    l1_pos = body.index("## L1/L2")
    assert "A" in body[l1_pos:]


def test_report_with_pack_dir_shows_pack_link(test_db):
    """Jobs with pack paths include the pack directory in the report."""

    l1_jobs = [{
        "id": 1, "title": "Engineer", "company": "Corp",
        "fit_score": 90, "level": 1,
        "source_url": "", "summary": "",
        "pack_dir": "packs/1_corp_engineer",
    }]

    from cron.generate_cycle_report import _render_report
    body = _render_report("test", l1_jobs, [], [])

    assert "packs/1_corp_engineer" in body
    assert "**Pack**" in body
