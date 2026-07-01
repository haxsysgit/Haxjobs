"""Pagination tests — use shared test_db fixture, not inline schema."""
import json

from unittest.mock import patch


def _seed_pagination_data():
    """Seed 25 jobs (10 pending, 10 evaluated, 5 skipped)."""
    from haxjobs.db.jobs import insert_job, update_job_status
    from haxjobs.db.evaluations import save_evaluation

    for i in range(25):
        job_id = insert_job(
            title=f"Job {i}", company=f"Company {i}", location="London",
            source="test",
        )
        if i < 10:
            pass  # pending is default
        elif i < 20:
            # mark evaluated and insert evaluation
            save_evaluation(job_id, {
                "fit_score": 80 - i, "fit_verdict": "GOOD_FIT",
                "level": 2, "level_name": "Quick Apply",
                "strongest_matches": [], "major_gaps": [],
                "sponsorship_risk": "low", "summary": f"Summary {i}",
                "decision": "completed",
            })
        else:
            update_job_status(job_id, "skipped")


def _seed_simple_jobs(n=10):
    from haxjobs.db.jobs import insert_job
    for i in range(n):
        insert_job(title=f"J{i}", company=f"C{i}", location="London", source="test")


def test_db_pagination_returns_limited_results(test_db):
    """get_jobs_with_evaluations respects limit/offset."""
    _seed_pagination_data()

    import haxjobs.db.evaluations as db_evals
    page = db_evals.get_jobs_with_evaluations(limit=10, offset=0)
    assert len(page) == 10
    page2 = db_evals.get_jobs_with_evaluations(limit=10, offset=10)
    assert len(page2) == 10
    ids1 = {r["id"] for r in page}
    ids2 = {r["id"] for r in page2}
    assert ids1.isdisjoint(ids2)


def test_db_pagination_with_status_filter(test_db):
    _seed_pagination_data()

    import haxjobs.db.evaluations as db_evals
    result = db_evals.get_jobs_with_evaluations(status_filter="pending", limit=5, offset=0)
    assert len(result) <= 5
    for r in result:
        assert r["status"] == "pending"


def test_db_no_limit_returns_all(test_db):
    _seed_pagination_data()

    import haxjobs.db.evaluations as db_evals
    result = db_evals.get_jobs_with_evaluations()
    assert len(result) == 25


def test_list_jobs_passes_params_to_db_layer(test_db):
    """list_jobs forwards status_filter, offset, limit to get_jobs_with_evaluations."""
    _seed_simple_jobs(1)

    import haxjobs.db.evaluations as db_evals
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
        from haxjobs.server.routes.jobs import list_jobs
        result = list_jobs(status_filter="pending", offset=5, limit=20)
        assert captured_kwargs == {"status_filter": "pending", "offset": 5, "limit": 20}
        assert len(result) == 1


def test_list_jobs_backward_compat_no_args(test_db):
    """list_jobs() with no args still works (backward compat)."""
    import haxjobs.db.evaluations as db_evals

    def fake_get_jobs(**kwargs):
        return []

    with patch.object(db_evals, "get_jobs_with_evaluations", fake_get_jobs):
        from haxjobs.server.routes.jobs import list_jobs
        result = list_jobs()
        assert result == []
