"""Discovery API service."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4

from haxjobs.db.discovered_jobs import (
    list_discovered_jobs,
    promote_discovered_job,
    update_discovery_status,
)
from haxjobs.db.schema import get_db, init
from haxjobs.discovery.hooks import should_accept_discovered_job
from haxjobs.discovery.scrapers.orchestrator import is_error_result, run_all_scrapers

_lock = threading.Lock()
_status = {
    "running": False,
    "run_id": "",
    "found": 0,
    "new": 0,
    "promoted": 0,
    "errors": [],
    "started_at": "",
    "finished_at": "",
}


def run_discovery() -> str:
    """Start a discovery run in the background and return its id."""
    with _lock:
        if _status["running"]:
            return str(_status["run_id"])
        run_id = uuid4().hex[:12]
        _status.update({
            "running": True,
            "run_id": run_id,
            "found": 0,
            "new": 0,
            "promoted": 0,
            "errors": [],
            "started_at": _now(),
            "finished_at": "",
        })
    threading.Thread(target=_run_worker, daemon=True).start()
    return run_id


def get_status() -> dict:
    with _lock:
        return dict(_status)


def get_new_jobs(since: str = "") -> list[dict]:
    """Return recently discovered rows, optionally after an ISO/sqlite timestamp."""
    conn = get_db()
    if since:
        rows = conn.execute(
            "SELECT * FROM discovered_jobs WHERE created_at > ? ORDER BY created_at DESC LIMIT 100",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM discovered_jobs ORDER BY created_at DESC LIMIT 25"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _run_worker() -> None:
    try:
        init()
        results = run_all_scrapers()
        found, new, errors = _summarize(results)
        promoted = _promote_new_jobs()
        with _lock:
            _status.update({"found": found, "new": new, "promoted": promoted, "errors": errors})
    except Exception as exc:  # ponytail: one process-wide run, surface failure in status.
        with _lock:
            _status["errors"] = [str(exc)]
    finally:
        with _lock:
            _status["running"] = False
            _status["finished_at"] = _now()


def _summarize(results: dict) -> tuple[int, int, list[str]]:
    found = 0
    new = 0
    errors: list[str] = []
    for scraper_name, scraper_result in results.items():
        if is_error_result(scraper_result):
            errors.append(f"{scraper_name}: {scraper_result['error']}")
            continue
        for company, counts in scraper_result.items():
            found += int(counts.get("found", 0))
            new += int(counts.get("new", 0))
            error_count = int(counts.get("errors", 0))
            if error_count:
                errors.append(f"{scraper_name}/{company}: {error_count} errors")
    return found, new, errors


def _promote_new_jobs() -> int:
    promoted = 0
    for job in list_discovered_jobs(status="new", limit=500):
        accepted, reason = should_accept_discovered_job(job)
        if not accepted:
            update_discovery_status(job["id"], reason, reason)
            continue
        update_discovery_status(job["id"], "accepted", "accepted")
        if promote_discovered_job(job["id"]):
            promoted += 1
    return promoted


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
