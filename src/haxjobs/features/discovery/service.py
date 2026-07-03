"""Discovery API service."""
from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from haxjobs.db.discovered_jobs import (
    list_discovered_jobs,
    promote_discovered_job,
    update_discovery_status,
)
from haxjobs.db.schema import get_db, init
from haxjobs.discovery.hooks import should_accept_discovered_job
from haxjobs.discovery.scrapers.ashby import scrape_ashby
from haxjobs.discovery.scrapers.lever import scrape_lever
from haxjobs.discovery.scrapers.orchestrator import scrape_greenhouse

ScraperRunner = Callable[[], dict[str, dict[str, int]]]

SCRAPERS: list[tuple[str, ScraperRunner]] = [
    ("greenhouse", scrape_greenhouse),
    ("ashby", scrape_ashby),
    ("lever", scrape_lever),
]

_lock = threading.Lock()
_status = {
    "running": False,
    "run_id": "",
    "found": 0,
    "new": 0,
    "promoted": 0,
    "errors": [],
    "scrapers": [],
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
            "scrapers": [_scraper_status(name) for name, _ in SCRAPERS],
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
        for name, runner in SCRAPERS:
            _set_scraper(name, status="running")
            try:
                counts = _summarize_scraper(runner())
                _set_scraper(name, status="done", **counts)
                _add_totals(counts)
            except Exception as exc:  # ponytail: isolate one bad scraper from the run.
                message = str(exc)
                _set_scraper(name, status="error", errors=1, message=message)
                _add_error(f"{name}: {message}")
        promoted = _promote_new_jobs()
        with _lock:
            _status["promoted"] = promoted
    except Exception as exc:  # ponytail: process-wide guard, status is enough for UI.
        _add_error(str(exc))
    finally:
        with _lock:
            _status["running"] = False
            _status["finished_at"] = _now()


def _summarize_scraper(result: dict[str, dict[str, int]]) -> dict[str, int]:
    counts = {"found": 0, "matched": 0, "new": 0, "errors": 0}
    for company_result in result.values():
        for key in counts:
            counts[key] += int(company_result.get(key, 0))
    return counts


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


def _set_scraper(name: str, **updates) -> None:
    with _lock:
        scrapers = list(_status["scrapers"])
        _status["scrapers"] = [
            {**item, **updates} if item["name"] == name else item
            for item in scrapers
        ]


def _add_totals(counts: dict[str, int]) -> None:
    with _lock:
        _status["found"] = int(_status["found"]) + counts["found"]
        _status["new"] = int(_status["new"]) + counts["new"]
        if counts["errors"]:
            errors = list(_status["errors"])
            errors.append(f"scraper reported {counts['errors']} item errors")
            _status["errors"] = errors


def _add_error(message: str) -> None:
    with _lock:
        _status["errors"] = [*list(_status["errors"]), message]


def _scraper_status(name: str) -> dict:
    return {"name": name, "status": "pending", "found": 0, "matched": 0, "new": 0, "errors": 0, "message": ""}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
