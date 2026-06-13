#!/usr/bin/env python3
"""Weekly HaxJobs summary report — token-free, runs on Archilles.

Queries pipeline.db for weekly stats and sends a formatted report to Telegram.
No LLM calls — pure SQL + templated markdown.

Usage:
  python3 cron/weekly_report.py           # Dry run (print to stdout)
  python3 cron/weekly_report.py --send    # Send to Telegram
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

DB_PATH = "/home/hermes/haxjobs/state/pipeline.db"
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = "-1003991695885"
TELEGRAM_THREAD_ID = 18  # Cron reports topic


def load_token():
    global TELEGRAM_BOT_TOKEN
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN=") and not line.startswith("#"):
                    TELEGRAM_BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return
    print("WARNING: TELEGRAM_BOT_TOKEN not found in .env")


def query():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    stats = {}

    # Total jobs this week
    r = conn.execute(
        "SELECT count(*) n FROM jobs WHERE discovered_at > ?",
        (week_ago.isoformat(),)
    ).fetchone()
    stats["new_jobs_week"] = r["n"] if r else 0

    # By source
    rows = conn.execute(
        "SELECT source, count(*) n FROM jobs WHERE discovered_at > ? GROUP BY source ORDER BY n DESC",
        (week_ago.isoformat(),)
    ).fetchall()
    stats["by_source"] = [dict(r) for r in rows]

    # Evaluated with scores
    rows = conn.execute(
        """SELECT j.title, j.company, j.location, e.fit_score, e.fit_verdict, j.source_url
           FROM jobs j JOIN evaluations e ON j.id = e.job_id
           WHERE j.discovered_at > ? AND e.fit_score >= 50
           ORDER BY e.fit_score DESC LIMIT 15""",
        (week_ago.isoformat(),)
    ).fetchall()
    stats["top_jobs"] = [dict(r) for r in rows]

    # Score distribution
    rows = conn.execute(
        """SELECT
           CASE
             WHEN e.fit_score >= 75 THEN 'Strong (75+)'
             WHEN e.fit_score >= 50 THEN 'Good (50-74)'
             WHEN e.fit_score >= 30 THEN 'Weak (30-49)'
             ELSE 'Skip (<30)'
           END as bucket,
           count(*) n
           FROM jobs j JOIN evaluations e ON j.id = e.job_id
           WHERE j.discovered_at > ?
           GROUP BY bucket ORDER BY min(e.fit_score) DESC""",
        (week_ago.isoformat(),)
    ).fetchall()
    stats["score_distribution"] = [dict(r) for r in rows]

    # Packs generated
    r = conn.execute(
        "SELECT count(*) n FROM jobs WHERE pack_status = 'generated' AND discovered_at > ?",
        (week_ago.isoformat(),)
    ).fetchone()
    stats["packs_generated"] = r["n"] if r else 0

    # Total database stats
    stats["total_jobs"] = conn.execute("SELECT count(*) n FROM jobs").fetchone()["n"]
    stats["total_evaluated"] = conn.execute(
        "SELECT count(*) n FROM jobs j JOIN evaluations e ON j.id = e.job_id"
    ).fetchone()["n"]
    stats["total_pending"] = conn.execute(
        "SELECT count(*) n FROM jobs WHERE status = 'pending'"
    ).fetchone()["n"]

    conn.close()
    return stats


def format_report(stats: dict) -> str:
    now = datetime.now(timezone.utc)
    lines = [
        f"HaxJobs Weekly Report",
        f"{now.strftime('%B %d, %Y')}",
        "",
        f"New jobs this week: {stats['new_jobs_week']}",
        f"Total in pipeline: {stats['total_jobs']} ({stats['total_evaluated']} evaluated, {stats['total_pending']} pending)",
        "",
        "Discovery sources:",
    ]

    for s in stats["by_source"]:
        lines.append(f"  {s['source']:25s} {s['n']:4d} jobs")

    lines.append("")
    lines.append("Score distribution:")
    for s in stats["score_distribution"]:
        lines.append(f"  {s['bucket']:20s} {s['n']:4d}")

    lines.append("")
    lines.append(f"Packs generated: {stats['packs_generated']}")

    if stats["top_jobs"]:
        lines.append("")
        lines.append("Top matches this week:")
        for i, j in enumerate(stats["top_jobs"][:10], 1):
            score = j["fit_score"] or 0
            lines.append(f"  {i}. {score}% | {j['title'][:50]} at {j['company']}")

    lines.append("")
    lines.append("Full dashboard: http://178.105.245.120:8800")

    return "\n".join(lines)


def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN:
        print("No token, cannot send")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "message_thread_id": TELEGRAM_THREAD_ID,
        "text": text,
        "parse_mode": "HTML",
    }).encode()

    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=10)
    result = json.loads(resp.read())
    return result.get("ok", False)


if __name__ == "__main__":
    load_token()
    stats = query()
    report = format_report(stats)
    print(report)

    if "--send" in sys.argv:
        if send_telegram(report):
            print("\nSent to Telegram")
        else:
            print("\nFailed to send")
            sys.exit(1)
