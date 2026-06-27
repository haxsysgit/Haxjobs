"""Evaluation CRUD operations."""
import json
from .schema import get_db
from .activity import _log


def save_evaluation(job_id, result):
    conn = get_db()

    # Archive old evaluation to history before overwriting
    old = conn.execute("SELECT fit_score, fit_verdict, level, level_name, evaluated_by FROM evaluations WHERE job_id=?", (job_id,)).fetchone()
    if old:
        conn.execute("""
            INSERT INTO evaluation_history (job_id, fit_score, fit_verdict, level, level_name, evaluated_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, old["fit_score"], old["fit_verdict"], old["level"], old["level_name"], old["evaluated_by"]))

    decision = result.get("decision", "completed")
    conn.execute("""
        INSERT INTO evaluations (job_id, fit_score, fit_verdict, level, level_name,
            strongest_matches, major_gaps, sponsorship_risk, summary, decision,
            skip_reason, role_type, evaluated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            fit_score=excluded.fit_score, fit_verdict=excluded.fit_verdict,
            level=excluded.level, level_name=excluded.level_name,
            strongest_matches=excluded.strongest_matches,
            major_gaps=excluded.major_gaps,
            sponsorship_risk=excluded.sponsorship_risk,
            summary=excluded.summary, decision=excluded.decision,
            skip_reason=excluded.skip_reason, role_type=excluded.role_type,
            evaluated_by=excluded.evaluated_by, evaluated_at=datetime('now')
    """, (
        job_id,
        result["fit_score"],
        result["fit_verdict"],
        result["level"],
        result["level_name"],
        json.dumps(result.get("strongest_matches", [])),
        json.dumps(result.get("major_gaps", [])),
        result.get("sponsorship_risk", "medium"),
        result.get("summary", ""),
        decision,
        result.get("skip_reason", ""),
        result.get("role_type", ""),
        result.get("evaluated_by", "hermes"),
    ))
    # Use the same default for both DB row and job status calculation
    new_status = "evaluated" if decision == "completed" else "skipped"
    conn.execute("UPDATE jobs SET status=?, updated_at=datetime('now') WHERE id=?",
                 (new_status, job_id))
    conn.commit()
    conn.close()
    _log("job_evaluated",
         f"Score {result['fit_score']} — {result['fit_verdict']}",
         job_id=job_id)


def get_evaluation(job_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM evaluations WHERE job_id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_jobs_with_evaluations(status_filter=None):
    conn = get_db()
    query = """
        SELECT j.*, e.fit_score, e.fit_verdict, e.level, e.level_name,
               e.strongest_matches, e.major_gaps, e.sponsorship_risk,
               e.summary, e.decision as eval_decision, e.skip_reason,
               e.role_type, e.evaluated_by, e.evaluated_at
        FROM jobs j
        LEFT JOIN evaluations e ON j.id = e.job_id
    """
    if status_filter:
        query += " WHERE j.status=?"
        rows = conn.execute(query + " ORDER BY j.discovered_at DESC",
                           (status_filter,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY j.discovered_at DESC").fetchall()
    conn.close()
    return [_job_with_eval(r) for r in rows]


def _job_with_eval(row):
    d = dict(row)
    for field in ("strongest_matches", "major_gaps"):
        val = d.get(field)
        d[field] = json.loads(val) if val else []
    return d
