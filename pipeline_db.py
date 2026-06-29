#!/usr/bin/env python3
"""HaxJobs SQLite database — backward-compatibility wrapper.

All functionality lives in db/ submodules.
This file exists so existing imports like `import pipeline_db as db` continue to work.
"""
from db import *  # noqa: F401, F403

import sys

if __name__ == "__main__":
    from db.schema import init as _init
    _init()

    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "seed":
        from db.seed import seed_from_intake
        n = seed_from_intake()
        print(f"Seeded {n} jobs from intake/")

    elif action == "classify-roles":
        from db.role_classification import classify_existing_jobs
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        summary = classify_existing_jobs(limit=limit)
        print(f"Role classification: {summary['classified']} classified, {summary['unknown']} unknown, {summary['scanned']} scanned")

    elif action == "status":
        from db.stats import get_stats
        s = get_stats()
        print(f"Jobs: {s['total_jobs']} total ({s['pending']} pending, {s['evaluated']} evaluated, {s['skipped']} skipped)")
        print(f"Fits: {s['strong_fit']} strong, {s['good_fit']} good")
        print(f"User: {s['favorites']} favorites, {s['saved']} saved")
        print(f"Activity (24h): {s['activity_24h']}")

    elif action == "activity":
        from db.activity import get_recent_activity
        for a in get_recent_activity(20):
            print(f"[{a['created_at']}] {a['event_type']}: {a['message'][:120]}")

    elif action == "pending":
        from db.jobs import get_pending_jobs
        jobs = get_pending_jobs()
        print(f"{len(jobs)} pending jobs:")
        for j in jobs[:20]:
            print(f"  [{j['id']}] {j['title'][:60]} at {j['company']} ({j['location']})")

    elif action == "favorites":
        from db.favorites import get_favorites
        favs = get_favorites()
        print(f"{len(favs)} favorites: {favs}")

    elif action == "reset":
        from db.schema import get_db
        conn = get_db()
        conn.execute("UPDATE jobs SET status='pending'")
        conn.execute("DELETE FROM evaluations")
        conn.commit()
        conn.close()
        print("All jobs reset to pending. Evaluations cleared.")

    elif action == "discover-manual":
        """Insert a manually-discovered job through the full ingestion spine."""
        import argparse
        parser = argparse.ArgumentParser(prog="pipeline_db.py discover-manual")
        parser.add_argument("--title", required=True)
        parser.add_argument("--company", required=True)
        parser.add_argument("--location", default="")
        parser.add_argument("--url", default="")
        parser.add_argument("--apply-url", default="")
        parser.add_argument("--jd-file", type=argparse.FileType("r"), default=None)
        parser.add_argument("--source", default="manual")
        args = parser.parse_args(sys.argv[2:])

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
            sys.exit(0)

        accepted, reason = should_accept_discovered_job(normalized)
        if not accepted:
            update_discovery_status(rec_id, reason, reason)
            print(f"Job #{rec_id} rejected: {reason}")
            sys.exit(0)

        update_discovery_status(rec_id, "accepted", "accepted")
        job_id = promote_discovered_job(rec_id)
        if job_id:
            print(f"Job #{rec_id} accepted and promoted to jobs #{job_id}: {args.title} at {args.company}")
        else:
            print(f"Job #{rec_id} accepted but promotion failed (duplicate in jobs table).")

    elif action == "discover-run":
        """Process discovered_jobs with status 'new' through hooks and promote accepted."""
        from db.discovered_jobs import list_discovered_jobs, update_discovery_status, promote_discovered_job
        from discovery import should_accept_discovered_job

        new_jobs = list_discovered_jobs(status="new")
        if not new_jobs:
            print("No new discovered jobs to process.")
            sys.exit(0)

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

    elif action == "scrape-greenhouse":
        """Scrape Greenhouse boards into discovered_jobs."""
        from discovery.scrapers.greenhouse import main as greenhouse_main

        raise SystemExit(greenhouse_main(sys.argv[2:]))

    elif action == "scrape-ashby":
        """Scrape Ashby boards into discovered_jobs."""
        from discovery.scrapers.ashby import main as ashby_main

        raise SystemExit(ashby_main(sys.argv[2:]))

    elif action == "scrape-lever":
        """Scrape Lever boards into discovered_jobs."""
        from discovery.scrapers.lever import main as lever_main

        raise SystemExit(lever_main(sys.argv[2:]))

    elif action == "scrape-all":
        """Run every configured discovery scraper."""
        from discovery.scrapers.orchestrator import main as orchestrator_main

        raise SystemExit(orchestrator_main())

    else:
        print(f"Unknown action: {action}")
        print("Usage: pipeline_db.py [seed|classify-roles|status|activity|pending|favorites|reset|discover-manual|discover-run|scrape-greenhouse|scrape-ashby|scrape-lever|scrape-all]")
