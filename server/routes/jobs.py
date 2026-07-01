"""Job-related API routes."""
import json
from generate_ready_packs import generate_pack_for_job
from db import jobs as db_jobs, evaluations as db_evals, decisions as db_decs, whitelist as db_wl
from db.pack_review import review_pack


def list_jobs(status_filter=None, offset=0, limit=None):
    """Return jobs with evaluations, hydrated with auto-apply state.

    Accepts optional status_filter, offset, and limit for pagination.
    When limit is None (default), returns all jobs (backward compat).
    """
    raw = db_evals.get_jobs_with_evaluations(
        status_filter=status_filter, offset=offset, limit=limit
    )

    # Batch: gather all job IDs once
    job_ids = [r["id"] for r in raw]
    auto_apply_states = db_decs.get_latest_auto_apply_states(job_ids)

    result = []
    for r in raw:
        jid = r["id"]
        result.append({
            "id": str(jid),
            "company": r["company"],
            "title": r["title"],
            "location": r.get("location", ""),
            "source": r.get("source", "unknown"),
            "sourceQuality": r.get("source_quality", "unknown"),
            "roleFamily": r.get("role_family", "unknown"),
            "roleFamilyConfidence": r.get("role_family_confidence", 0),
            "recommendedCvVariant": r.get("recommended_cv_variant", "unknown"),
            "packStatus": r.get("pack_status", "none"),
            "packReviewStatus": r.get("pack_review_status", "none"),
            "packReviewNotes": r.get("pack_review_notes", ""),
            "packReviewedAt": r.get("pack_reviewed_at", ""),
            "outreachStatus": r.get("outreach_status", "none"),
            "fitScore": r.get("fit_score") if r.get("fit_score") is not None else 0,
            "status": r.get("status", "pending"),
            "isApproved": r.get("status", "") == "approved",
            "isUnskipped": r.get("status", "") == "pending" and r.get("fit_score") is not None,
            "level": r.get("level", 1),
            "levelName": r.get("level_name", "Standard"),
            "strongestMatches": r.get("strongest_matches", []),
            "majorGaps": r.get("major_gaps", []),
            "sponsorshipRisk": r.get("sponsorship_risk", "unknown"),
            "summary": r.get("summary", ""),
            "applicationUrl": r.get("source_url", ""),
            "packDir": r.get("pack_dir", ""),
            "skipReason": r.get("skip_reason", ""),
            "receivedAt": r.get("discovered_at", ""),
            "processedAt": r.get("evaluated_at", ""),
            "isAutoApply": auto_apply_states.get(jid, False),
        })
    return result


def unskip_job(body):
    job_id = body.get("job_id")
    if not job_id:
        return 400, {"error": "job_id required"}
    db_jobs.update_job_status(int(job_id), "pending")
    db_decs.record_decision(int(job_id), "unskipped", body.get("reason", "User unskipped from dashboard"))
    suggestion = db_wl.suggest_whitelist(int(job_id))
    wl_result = None
    if body.get("add_to_whitelist") and suggestion:
        wl_id = db_wl.add_whitelist(
            pattern_type=suggestion["suggested_type"],
            pattern_value=suggestion["suggested_value"],
            reason=suggestion["suggested_reason"],
            source_job_id=int(job_id)
        )
        wl_result = {"id": wl_id, "type": suggestion["suggested_type"], "value": suggestion["suggested_value"]}
    return 200, {
        "ok": True,
        "message": f"Job {job_id} reset to pending for re-evaluation",
        "whitelist_suggestion": suggestion,
        "whitelist_created": wl_result,
    }


def approve_job(body):
    job_id = body.get("job_id")
    if not job_id:
        return 400, {"error": "job_id required"}
    db_jobs.update_job_status(int(job_id), "approved")
    db_decs.record_decision(int(job_id), "approved", body.get("reason", "User manually approved from dashboard"))
    suggestion = db_wl.suggest_whitelist(int(job_id))
    if body.get("add_to_whitelist") and suggestion:
        db_wl.add_whitelist(
            pattern_type=suggestion["suggested_type"],
            pattern_value=suggestion["suggested_value"],
            reason=suggestion["suggested_reason"],
            source_job_id=int(job_id)
        )
    return 200, {
        "ok": True,
        "message": f"Job {job_id} manually approved — ready for pack generation",
        "whitelist_suggestion": suggestion,
    }


def generate_job_pack(body):
    """Generate one pack for one explicitly requested job via HTTP API.

    Only job_id is accepted from the request body. Filesystem paths and
    generation policy stay server-side.
    """
    job_id = body.get("job_id")
    if not job_id:
        return 400, {"error": "job_id required"}
    result = generate_pack_for_job(int(job_id))
    return (200 if result.get("ok") else 400), result


def review_job_pack(body):
    """Record a manual pack review action from API/dashboard."""
    job_id = body.get("job_id")
    if not job_id:
        return 400, {"error": "job_id required"}
    action = body.get("action", "")
    notes = body.get("notes", body.get("reason", ""))
    result = review_pack(int(job_id), action, notes)
    return (200 if result.get("ok") else 400), result


def toggle_auto_apply(body):
    job_id = body.get("job_id")
    if not job_id:
        return 400, {"error": "job_id required"}
    existing = db_decs.get_decisions(int(job_id))
    latest = existing[0]["decision"] if existing else ""
    has_auto = latest == "auto_apply"
    if has_auto:
        db_decs.record_decision(int(job_id), "auto_apply_remove", body.get("reason", ""))
        return 200, {"ok": True, "auto_apply": False}
    else:
        db_decs.record_decision(int(job_id), "auto_apply", body.get("reason", ""))
        return 200, {"ok": True, "auto_apply": True}


def queue_intake(body):
    job_id = db_jobs.insert_job(
        title=body.get("title", "Manual Intake"),
        company=body.get("company", "Unknown"),
        jd_text=body.get("jd_text", ""),
        source_url=body.get("url", ""),
        source=body.get("source", "dashboard"),
    )
    if job_id:
        return 200, {"ok": True, "job_id": job_id}
    return 500, {"ok": False, "message": "Failed to queue"}
