#!/usr/bin/env python3
"""HaxJobs pipeline CLI — unified entry point for all pipeline operations.

`import pipeline_db as db` provides access to all db/ and discovery/ modules.
"""
from db import *  # noqa: F401, F403

import argparse
import sys


# ═══════════════════════════════════════════════════════════════════
#  Actions — one named function per CLI action
# ═══════════════════════════════════════════════════════════════════

def action_seed():
    """Seed sample jobs from intake/ directory."""
    from db.seed import seed_from_intake
    n = seed_from_intake()
    print(f"Seeded {n} jobs from intake/")


def action_classify_roles(argv: list[str] | None = None):
    """Run role classification on pending jobs."""
    from db.role_classification import classify_existing_jobs
    limit = None
    if argv and len(argv) > 0:
        try:
            limit = int(argv[0])
        except ValueError:
            pass
    summary = classify_existing_jobs(limit=limit)
    print(f"Role classification: {summary['classified']} classified, "
          f"{summary['unknown']} unknown, {summary['scanned']} scanned")


def action_status():
    """Print DB stats."""
    from db.stats import get_stats
    s = get_stats()
    print(f"Jobs: {s['total_jobs']} total ({s['pending']} pending, "
          f"{s['evaluated']} evaluated, {s['skipped']} skipped)")
    print(f"Fits: {s['strong_fit']} strong, {s['good_fit']} good")
    print(f"User: {s['favorites']} favorites, {s['saved']} saved")
    print(f"Activity (24h): {s['activity_24h']}")


def action_activity():
    """Print recent activity log."""
    from db.activity import get_recent_activity
    for a in get_recent_activity(20):
        print(f"[{a['created_at']}] {a['event_type']}: {a['message'][:120]}")


def action_pending():
    """List pending jobs."""
    from db.jobs import get_pending_jobs
    jobs = get_pending_jobs()
    print(f"{len(jobs)} pending jobs:")
    for j in jobs[:20]:
        print(f"  [{j['id']}] {j['title'][:60]} at {j['company']} ({j['location']})")


def action_favorites():
    """List favorited jobs."""
    from db.favorites import get_favorites
    favs = get_favorites()
    print(f"{len(favs)} favorites: {favs}")


def action_reset():
    """Reset all jobs to pending, clear evaluations."""
    from db.schema import get_db
    conn = get_db()
    conn.execute("UPDATE jobs SET status='pending'")
    conn.execute("DELETE FROM evaluations")
    conn.commit()
    conn.close()
    print("All jobs reset to pending. Evaluations cleared.")


def action_discover_manual(argv: list[str]):
    """Insert a manually-discovered job through the full ingestion spine."""
    parser = argparse.ArgumentParser(prog="pipeline_db.py discover-manual")
    parser.add_argument("--title", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--location", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--apply-url", default="")
    parser.add_argument("--jd-file", type=argparse.FileType("r"), default=None)
    parser.add_argument("--source", default="manual")
    args = parser.parse_args(argv)

    jd_text = args.jd_file.read() if args.jd_file else ""
    raw = {
        "title": args.title,
        "company": args.company,
        "location": args.location,
        "source_url": args.url,
        "apply_url": args.apply_url,
        "jd_text": jd_text,
    }

    from discovery import normalize_job, should_accept_discovered_job
    from db.discovered_jobs import insert_discovered_job, update_discovery_status, promote_discovered_job

    normalized = normalize_job(raw, source=args.source)
    rec_id = insert_discovered_job(normalized)
    if rec_id is None:
        print("Duplicate — job already discovered (not inserted).")
        return

    accepted, reason = should_accept_discovered_job(normalized)
    if not accepted:
        update_discovery_status(rec_id, reason, reason)
        print(f"Job #{rec_id} rejected: {reason}")
        return

    update_discovery_status(rec_id, "accepted", "accepted")
    job_id = promote_discovered_job(rec_id)
    if job_id:
        print(f"Job #{rec_id} accepted and promoted to jobs #{job_id}: {args.title} at {args.company}")
    else:
        print(f"Job #{rec_id} accepted but promotion failed (duplicate in jobs table).")


def action_discover_run():
    """Process discovered_jobs with status 'new' through hooks, promote accepted."""
    from db.discovered_jobs import list_discovered_jobs, update_discovery_status, promote_discovered_job
    from discovery import should_accept_discovered_job

    new_jobs = list_discovered_jobs(status="new")
    if not new_jobs:
        print("No new discovered jobs to process.")
        return

    accepted_count = 0
    rejected_count = 0
    for dj in new_jobs:
        accepted, reason = should_accept_discovered_job(dj)
        if not accepted:
            update_discovery_status(dj["id"], reason, reason)
            print(f"  [{dj['id']}] {dj['title'][:60]} at {dj['company']}: {reason}")
            rejected_count += 1
            continue
        update_discovery_status(dj["id"], "accepted", "accepted")
        job_id = promote_discovered_job(dj["id"])
        if job_id:
            print(f"  [{dj['id']}] -> jobs #{job_id} {dj['title'][:60]} at {dj['company']}: accepted")
            accepted_count += 1
        else:
            print(f"  [{dj['id']}] {dj['title'][:60]} at {dj['company']}: promoted to existing job")
            accepted_count += 1

    print(f"Discover run complete: {accepted_count} accepted, {rejected_count} rejected")


def action_scrape_greenhouse(argv: list[str]):
    from discovery.scrapers.greenhouse import main as greenhouse_main
    raise SystemExit(greenhouse_main(argv))


def action_scrape_ashby(argv: list[str]):
    from discovery.scrapers.ashby import main as ashby_main
    raise SystemExit(ashby_main(argv))


def action_scrape_lever(argv: list[str]):
    from discovery.scrapers.lever import main as lever_main
    raise SystemExit(lever_main(argv))


def action_scrape_all():
    """Run every configured discovery scraper."""
    from discovery.scrapers.orchestrator import run_all_scrapers, summarize_results
    from db.schema import init as _init
    _init()
    results = run_all_scrapers()
    summarize_results(results)
    return results


# ═══════════════════════════════════════════════════════════════════
#  Composite pipeline actions (plan 026)
# ═══════════════════════════════════════════════════════════════════

def action_discover_full():
    """Full discovery cycle: scrape all sources → filter → promote → classify."""
    print("\n▸ Stage 1/3: Scraping all job sources…")
    action_scrape_all()

    print("\n▸ Stage 2/3: Filtering and promoting discovered jobs…")
    action_discover_run()

    print("\n▸ Stage 3/3: Classifying role families…")
    action_classify_roles()


def action_run_full():
    """Full pipeline end-to-end: discover → classify → evaluate → report."""
    print("=" * 60)
    print("  HaxJobs Full Pipeline Run")
    print("=" * 60)

    print("\n─ Discovery ─")
    action_discover_full()  # scrape + filter + promote + classify

    print("\n─ Evaluation ─")
    from evaluate.run import evaluate_from_db
    count = 0
    while True:
        ok = evaluate_from_db()
        if not ok:
            break
        count += 1
    print(f"Evaluated {count} jobs")

    print("\n─ Report ─")
    from cron.generate_cycle_report import main as report_main
    report_main([])

    print("\n" + "=" * 60)
    print("  Pipeline run complete.")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
#  Dispatch
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from db.schema import init as _init
    _init()

    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    rest = sys.argv[2:]

    if action == "seed":
        action_seed()
    elif action == "classify-roles":
        action_classify_roles(rest)
    elif action == "status":
        action_status()
    elif action == "activity":
        action_activity()
    elif action == "pending":
        action_pending()
    elif action == "favorites":
        action_favorites()
    elif action == "reset":
        action_reset()
    elif action == "discover-manual":
        action_discover_manual(rest)
    elif action == "discover-run":
        action_discover_run()
    elif action == "scrape-greenhouse":
        action_scrape_greenhouse(rest)
    elif action == "scrape-ashby":
        action_scrape_ashby(rest)
    elif action == "scrape-lever":
        action_scrape_lever(rest)
    elif action == "scrape-all":
        action_scrape_all()
    elif action == "discover-full":
        action_discover_full()
    elif action == "run-full":
        action_run_full()
    else:
        print(f"Unknown action: {action}")
        print("Usage: pipeline_db.py [seed|classify-roles|status|activity|pending|favorites|reset|")
        print("       discover-manual|discover-run|scrape-greenhouse|scrape-ashby|scrape-lever|")
        print("       scrape-all|discover-full|run-full]")
