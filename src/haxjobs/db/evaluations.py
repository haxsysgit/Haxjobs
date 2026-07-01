"""Evaluation CRUD operations."""
import json
from .schema import get_db
from .activity import _log
from haxjobs.config import EVALUATION_AGENT


def save_evaluation(job_id, result):
    conn = get_db()

    decision = result.get("decision", "completed")
    agent = result.get("agent") or result.get("evaluated_by") or EVALUATION_AGENT
    conn.execute("""
        INSERT INTO evaluations (job_id, fit_score, fit_verdict, level, level_name,
            strongest_matches, major_gaps, sponsorship_risk, summary, decision,
            skip_reason, role_type, evaluated_by,
            agent, profile_snapshot_json, report_markdown,
            pack_dir, pack_template_id, report_cycle_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            fit_score=excluded.fit_score, fit_verdict=excluded.fit_verdict,
            level=excluded.level, level_name=excluded.level_name,
            strongest_matches=excluded.strongest_matches,
            major_gaps=excluded.major_gaps,
            sponsorship_risk=excluded.sponsorship_risk,
            summary=excluded.summary, decision=excluded.decision,
            skip_reason=excluded.skip_reason, role_type=excluded.role_type,
            evaluated_by=excluded.evaluated_by,
            agent=excluded.agent,
            profile_snapshot_json=excluded.profile_snapshot_json,
            report_markdown=excluded.report_markdown,
            pack_dir=excluded.pack_dir,
            pack_template_id=excluded.pack_template_id,
            report_cycle_id=excluded.report_cycle_id,
            evaluated_at=datetime('now')
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
        agent,
        json.dumps(result.get("profile_snapshot_json", {})),
        result.get("report_markdown", ""),
        result.get("pack_dir", ""),
        result.get("pack_template_id", ""),
        str(result.get("report_cycle_id", "")),
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


def get_jobs_with_evaluations(status_filter=None, offset=0, limit=None):
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
        query += " ORDER BY j.discovered_at DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            rows = conn.execute(query, (status_filter, limit, offset)).fetchall()
        else:
            rows = conn.execute(query, (status_filter,)).fetchall()
    else:
        query += " ORDER BY j.discovered_at DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            rows = conn.execute(query, (limit, offset)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
    conn.close()
    return [_job_with_eval(r) for r in rows]


def _job_with_eval(row):
    d = dict(row)
    for field in ("strongest_matches", "major_gaps"):
        val = d.get(field)
        d[field] = json.loads(val) if val else []
    return d
