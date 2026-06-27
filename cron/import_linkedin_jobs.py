#!/usr/bin/env python3
"""Bulk import LinkedIn jobs from cache file into pipeline.db.

Usage:
  python3 cron/import_linkedin_jobs.py /tmp/linkedin_jobs_cache.json
"""

import json, sqlite3, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import schema
from db.jobs import insert_job


def main(cache_path: str):
    if not os.path.exists(cache_path):
        print(f"ERROR: {cache_path} not found")
        sys.exit(1)

    with open(cache_path) as f:
        jobs = json.load(f)

    schema.init()
    inserted = 0
    skipped = 0

    for job in jobs:
        try:
            jid = insert_job(
                title=job["title"],
                company=job.get("company") or "Unknown",
                location=job.get("location", "UK"),
                source_url=job.get("url", ""),
                source="linkedin_local",
                jd_text=f"{job['title']} — {job.get('url', '')}",
            )
            if jid:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            skipped += 1

    print(f"Inserted {inserted}, skipped {skipped} (total: {len(jobs)})")

    # Summary count — use schema's DB path, not a hardcoded relative path
    conn = schema.get_db()
    total = conn.execute(
        'SELECT count(*) FROM jobs WHERE source="linkedin_local"'
    ).fetchone()[0]
    conn.close()
    print(f"Total linkedin_local jobs in DB: {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: import_linkedin_jobs.py <cache.json>")
        sys.exit(1)
    main(sys.argv[1])
