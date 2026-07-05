"""Packs business logic."""
from haxjobs import product_tools


def get_pack_status(job_id: int):
    """Read pack status from the jobs table."""
    from haxjobs.db.jobs import get_job
    from haxjobs.db.evaluations import get_evaluation
    job = get_job(job_id)
    if not job:
        return {"ok": False, "code": "job_not_found", "error": f"Job {job_id} not found"}

    evaluation = get_evaluation(job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "pack_status": job.get("pack_status") or "not_generated",
        "pack_dir": job.get("pack_dir"),
        "evaluation": {
            "fit_score": evaluation.get("fit_score") if evaluation else None,
            "level": evaluation.get("level") if evaluation else None,
        } if evaluation else None,
    }


def generate_pack(job_id: int):
    """Generate an application pack via the shared product tool."""
    return product_tools.generate_pack(job_id)
