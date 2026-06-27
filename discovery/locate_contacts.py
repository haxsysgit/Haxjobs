#!/usr/bin/env python3
"""Local LinkedIn contact finder — finds hiring managers for high-fit jobs.

Runs on Jade's laptop (not Archilles) because LinkedIn blocks VPS IPs.
Searches LinkedIn for engineering managers, tech leads, and recruiters
at target companies. Saves results to Archilles DB via SSH.

Zero LLM — pure Playwright scraping + template matching.

Usage:
  python3 discovery/locate_contacts.py           # Dry run, show results
  python3 discovery/locate_contacts.py --save    # Save to Archilles DB
  python3 discovery/locate_contacts.py --job 42  # Single job
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from haxjobs_config import HAXJOBS_HOME as REMOTE_HAXJOBS_DIR

from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent / "linkedin_cookies.json"

# Search templates for finding hiring contacts
SEARCHES = [
    ("Engineering Manager", "hiring_manager"),
    ("Head of Engineering", "hiring_manager"),
    ("VP Engineering", "hiring_manager"),
    ("Tech Lead", "hiring_manager"),
    ("Director of Engineering", "hiring_manager"),
    ("Technical Recruiter", "recruiter"),
    ("Talent Acquisition", "recruiter"),
]


def load_cookies():
    if not COOKIES_FILE.exists():
        print(f"ERROR: Cookies not found at {COOKIES_FILE}")
        return None
    return json.loads(COOKIES_FILE.read_text())


def fetch_jobs_from_archilles(min_score: int = 75) -> list[dict]:
    """Fetch high-fit unevaluated jobs from Archilles DB via SSH."""
    cmd = [
        "ssh", "archilles",
        f"cd {REMOTE_HAXJOBS_DIR} && python3 -c \""
        "import sys; sys.path.insert(0, '.'); "
        "from db.outreach import get_jobs_for_outreach; "
        "import json; "
        f"jobs = get_jobs_for_outreach({min_score}); "
        "print(json.dumps(jobs))\"",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout.strip().split("\n")[-1])
    except Exception as e:
        print(f"Failed to fetch jobs from Archilles: {e}")
    return []


async def search_linkedin_people(context, company: str, role: str) -> list[dict]:
    """Search LinkedIn for people with a specific role at a company."""
    import urllib.parse
    query = urllib.parse.quote(f"{role} at {company}")
    url = f"https://www.linkedin.com/search/results/people/?keywords={query}"

    page = await context.new_page()
    contacts = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Find profile links
        links = await page.query_selector_all("a")
        found = 0
        for a in links:
            if found >= 5:
                break
            href = (await a.get_attribute("href")) or ""
            if "/in/" not in href:
                continue

            # Try to get name and title
            text = (await a.inner_text()).strip()
            if len(text) < 5:
                continue

            # Parse name and headline from text
            lines = text.split("\n")
            name = lines[0].strip()[:80] if lines else "Unknown"
            headline = lines[1].strip()[:120] if len(lines) > 1 else ""

            # Clean LinkedIn profile URL
            profile_url = href.split("?")[0]

            contacts.append({
                "name": name,
                "title": f"{role} | {headline}"[:120],
                "company": company,
                "linkedin_url": profile_url,
                "found_via": "linkedin_people_search",
            })
            found += 1

    except Exception as e:
        pass
    finally:
        await page.close()

    return contacts


def save_contacts_to_archilles(job_id: int, contacts: list[dict]):
    """Save found contacts to Archilles DB via SSH."""
    if not contacts:
        return 0

    contacts_json = json.dumps(contacts)
    cmd = [
        "ssh", "archilles",
        f"cd {REMOTE_HAXJOBS_DIR} && python3 -c \""
        "import sys, json; sys.path.insert(0, '.'); "
        "from db import schema; schema.init(); "
        "from db.outreach import insert_contact; "
        f"contacts = json.loads('''{contacts_json}'''); "
        f"job_id = {job_id}; "
        "inserted = 0; "
        "for c in contacts: "
        "    cid = insert_contact(job_id, c['name'], c['title'], c['company'], c.get('linkedin_url', ''), c.get('github_url', ''), c.get('found_via', 'linkedin')); "
        "    if cid: inserted += 1; "
        "print(f'Inserted {inserted}/{len(contacts)} contacts for job {job_id}')\"",
    ]
    try:
        subprocess.run(cmd, check=True, timeout=30)
        return len(contacts)
    except Exception as e:
        print(f"  Failed to save contacts: {e}")
        return 0


async def main(save: bool = False, job_id: int | None = None):
    cookies = load_cookies()
    if not cookies:
        return

    # Get jobs to find contacts for
    if job_id:
        # Fetch single job via SSH
        cmd = [
            "ssh", "archilles",
            f"cd {REMOTE_HAXJOBS_DIR} && python3 -c \""
            "import sys, json; sys.path.insert(0, '.'); "
            "from db import schema; schema.init(); "
            "import sqlite3; "
            f"c = sqlite3.connect('state/pipeline.db'); c.row_factory = sqlite3.Row; "
            f"r = c.execute('SELECT * FROM jobs WHERE id={job_id}').fetchone(); "
            "c.close(); "
            "print(json.dumps(dict(r)) if r else 'null')\"",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            try:
                jobs = [json.loads(result.stdout.strip().split("\n")[-1])]
            except Exception:
                print(f"Job {job_id} not found")
                return
        else:
            print(f"Failed to fetch job {job_id}")
            return
    else:
        jobs = fetch_jobs_from_archilles(min_score=75)

    if not jobs:
        print("No jobs found for outreach (need 75%+ fit, not yet contacted)")
        return

    print(f"Finding contacts for {len(jobs)} high-fit jobs...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
        )
        await context.add_cookies(cookies)

        for i, job in enumerate(jobs):
            company = job.get("company", "Unknown")
            score = job.get("fit_score", 0)
            title = job.get("title", "")[:60]
            jid = job.get("id")

            print(f"\n[{i+1}/{len(jobs)}] {score}% | {title} at {company}")

            all_contacts = []
            for search_role, contact_type in SEARCHES[:4]:  # Limit to top 4 roles
                try:
                    contacts = await search_linkedin_people(context, company, search_role)
                    if contacts:
                        print(f"  {search_role}: {len(contacts)} found")
                        all_contacts.extend(contacts)
                except Exception as e:
                    pass
                await asyncio.sleep(5)  # Rate limit

            if save and jid:
                saved = save_contacts_to_archilles(jid, all_contacts)
                print(f"  Saved {saved} contacts to DB")
            elif all_contacts:
                for c in all_contacts[:3]:
                    print(f"    {c['name']} | {c['title'][:60]}")

            await asyncio.sleep(10)  # Between companies

        await browser.close()

    print(f"\nDone. Processed {len(jobs)} jobs.")


if __name__ == "__main__":
    save_flag = "--save" in sys.argv
    job_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--job" and i + 1 < len(sys.argv):
            job_arg = int(sys.argv[i + 1])
            break

    asyncio.run(main(save=save_flag, job_id=job_arg))
