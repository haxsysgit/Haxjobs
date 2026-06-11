"""Pipeline stats queries."""
from .schema import get_db


def get_stats():
    conn = get_db()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
    evaluated = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='evaluated'").fetchone()[0]
    skipped = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='skipped'").fetchone()[0]
    strong = conn.execute("SELECT COUNT(*) FROM evaluations WHERE fit_score >= 80").fetchone()[0]
    good = conn.execute("SELECT COUNT(*) FROM evaluations WHERE fit_score >= 60 AND fit_score < 80").fetchone()[0]
    favorites_count = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
    saved_count = conn.execute("SELECT COUNT(*) FROM saved_jobs").fetchone()[0]
    recent = conn.execute(
        "SELECT COUNT(*) FROM activity_log WHERE created_at > datetime('now', '-24 hours')"
    ).fetchone()[0]
    conn.close()
    return {
        "total_jobs": total_jobs,
        "pending": pending,
        "evaluated": evaluated,
        "skipped": skipped,
        "strong_fit": strong,
        "good_fit": good,
        "favorites": favorites_count,
        "saved": saved_count,
        "activity_24h": recent,
    }
