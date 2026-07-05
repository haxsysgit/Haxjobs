"""Jobs business logic.

ponytail: thin wrappers over db/ modules. Real logic in later plans.
"""
from haxjobs.db.jobs import get_all_jobs, get_job
from haxjobs.db.evaluations import get_jobs_with_evaluations


def list_jobs(status_filter: str | None = None, role_family: str | None = None, offset: int = 0, limit: int | None = None):
    return get_jobs_with_evaluations(status_filter=status_filter, role_family=role_family, offset=offset, limit=limit)


def get_job_detail(job_id: int):
    job = get_job(job_id)
    if job is None:
        return None
    from haxjobs.db.evaluations import get_evaluation
    from haxjobs.db.decisions import get_decisions as _db_decisions
    eval_data = get_evaluation(job_id)
    decisions = _db_decisions(job_id)
    job["evaluation"] = eval_data
    job["decisions"] = decisions
    return job
