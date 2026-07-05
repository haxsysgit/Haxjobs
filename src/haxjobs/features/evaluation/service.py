"""Evaluation business logic."""
from haxjobs import product_tools


def get_status():
    return {"status": "idle", "message": "Evaluation available via POST /api/jobs/{id}/evaluate"}


def evaluate_job(job_id: int, auto_generate_pack: bool = True):
    """Evaluate a single job via the shared product tool."""
    return product_tools.evaluate_fit(job_id, auto_generate_pack=auto_generate_pack)
