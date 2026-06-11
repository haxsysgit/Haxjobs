#!/usr/bin/env python3
"""Deduplication helper for job pipeline intake.

Reads pending intake JSON files and removes duplicates based on:
- Same company+title within 7 days
- Same source_url within 30 days
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

INTAKE_DIR = "/home/hermes/haxjobs/intake"
DEDUP_WINDOW_DAYS = 7
URL_DEDUP_WINDOW_DAYS = 30


def normalize(text: str) -> str:
    """Normalize company/title for comparison."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def get_existing_jobs() -> list[dict]:
    """Scan intake dir for all jobs (pending + completed)."""
    existing = []
    intake_path = Path(INTAKE_DIR)
    if not intake_path.exists():
        return existing

    for fpath in intake_path.glob("*.json"):
        try:
            with open(fpath) as f:
                data = json.load(f)
            existing.append(
                {
                    "path": str(fpath),
                    "company": normalize(data.get("company", "")),
                    "title": normalize(data.get("title", "")),
                    "source_url": data.get("source_url", ""),
                    "received_at": data.get("received_at", ""),
                    "status": data.get("status", "pending"),
                }
            )
        except (json.JSONDecodeError, KeyError):
            continue

    return existing


def is_duplicate(job: dict, existing: list[dict]) -> tuple[bool, str]:
    """Check if a pending job is a duplicate of any existing job."""
    now = datetime.now(timezone.utc)
    job_company = normalize(job.get("company", ""))
    job_title = normalize(job.get("title", ""))
    job_url = job.get("source_url", "")

    for ex in existing:
        # Skip if no received_at
        if not ex.get("received_at"):
            continue

        try:
            ex_date = datetime.fromisoformat(ex["received_at"])
        except (ValueError, TypeError):
            continue

        age_days = (now - ex_date).days

        # Same company+title within DEDUP_WINDOW_DAYS
        if (
            job_company == ex["company"]
            and job_title == ex["title"]
            and age_days <= DEDUP_WINDOW_DAYS
        ):
            return True, f"duplicate company+title (existing: {ex['path']})"

        # Same URL within URL_DEDUP_WINDOW_DAYS
        if job_url and job_url == ex.get("source_url") and age_days <= URL_DEDUP_WINDOW_DAYS:
            return True, f"duplicate URL (existing: {ex['path']})"

    return False, ""


def main():
    existing = get_existing_jobs()
    pending = [j for j in existing if j.get("status") == "pending"]

    removed = 0
    for job in pending:
        dup, reason = is_duplicate(
            {
                "company": job["company"],
                "title": job["title"],
                "source_url": job.get("source_url", ""),
            },
            [e for e in existing if e["path"] != job["path"]],
        )
        if dup:
            try:
                os.remove(job["path"])
                removed += 1
                print(f"REMOVED: {os.path.basename(job['path'])} — {reason}")
            except OSError as e:
                print(f"ERROR removing {job['path']}: {e}")

    print(f"\nDedup complete. Removed {removed} duplicates. {len(pending) - removed} pending, {len(existing) - len(pending)} completed/processed.")


if __name__ == "__main__":
    main()
