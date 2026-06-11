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

    else:
        print(f"Unknown action: {action}")
        print("Usage: pipeline_db.py [seed|status|activity|pending|favorites|reset]")
