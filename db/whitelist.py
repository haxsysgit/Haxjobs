"""Whitelist CRUD operations."""
from .schema import get_db
from .activity import _log
from .jobs import get_job


def add_whitelist(pattern_type, pattern_value, reason="", source_job_id=None):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM whitelist WHERE pattern_type=? AND pattern_value=?",
            (pattern_type, pattern_value)
        ).fetchone()
        if existing:
            conn.execute("UPDATE whitelist SET active=1, reason=? WHERE id=?", (reason, existing["id"]))
            conn.commit()
            conn.close()
            return existing["id"]

        cur = conn.execute("""
            INSERT INTO whitelist (pattern_type, pattern_value, reason, source_job_id)
            VALUES (?, ?, ?, ?)
        """, (pattern_type, pattern_value, reason, source_job_id))
        conn.commit()
        wl_id = cur.lastrowid
        _log("whitelist_added", f"{pattern_type}: {pattern_value}", job_id=source_job_id)
        conn.close()
        return wl_id
    except Exception:
        conn.close()
        return None


def remove_whitelist(wl_id):
    conn = get_db()
    conn.execute("UPDATE whitelist SET active=0 WHERE id=?", (wl_id,))
    conn.commit()
    conn.close()
    _log("whitelist_removed", f"ID {wl_id}")


def get_whitelist(active_only=True):
    conn = get_db()
    if active_only:
        rows = conn.execute("SELECT * FROM whitelist WHERE active=1 ORDER BY pattern_type, created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM whitelist ORDER BY active DESC, pattern_type, created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_whitelist_for_eval(company, title):
    conn = get_db()
    matches = []
    company_lower = (company or "").strip().lower()
    title_lower = (title or "").strip().lower()

    rows = conn.execute(
        "SELECT * FROM whitelist WHERE active=1 ORDER BY pattern_type"
    ).fetchall()

    for row in rows:
        row = dict(row)
        ptype = row["pattern_type"]
        pval = (row["pattern_value"] or "").strip().lower()

        if ptype == "company_name" and pval in company_lower:
            matches.append(row)
            _incr_whitelist_match(row["id"], conn)
        elif ptype == "title_keyword" and pval in title_lower:
            matches.append(row)
            _incr_whitelist_match(row["id"], conn)
        elif ptype == "company_and_title":
            parts = pval.split("||")
            if len(parts) == 2:
                if parts[0].strip() in company_lower and parts[1].strip() in title_lower:
                    matches.append(row)
                    _incr_whitelist_match(row["id"], conn)

    conn.commit()
    conn.close()
    return matches


def _incr_whitelist_match(wl_id, conn):
    conn.execute("UPDATE whitelist SET match_count = match_count + 1 WHERE id=?", (wl_id,))


def suggest_whitelist(job_id):
    job = get_job(job_id)
    if not job:
        return None

    company = job.get("company", "").strip()
    title = job.get("title", "").strip()

    existing = get_whitelist_for_eval(company, title)
    if existing:
        return None

    if company:
        return {
            "suggested_type": "company_name",
            "suggested_value": company.lower(),
            "suggested_reason": f"Manually unskipped job '{title}' at {company} — prevent future false-positive skips for this company."
        }

    return None
