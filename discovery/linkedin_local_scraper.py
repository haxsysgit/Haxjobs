#!/usr/bin/env python3
"""Local LinkedIn job scraper — runs on Jade's laptop, sends results to Archilles.

Uses Playwright with cookie injection (works because local IP isn't flagged).
Scrapes LinkedIn job search results and sends discovered jobs to Archilles via API.

Usage:
  python3 discovery/linkedin_local_scraper.py
  python3 discovery/linkedin_local_scraper.py --send   # Actually send to Archilles
"""

from __future__ import annotations

import asyncio, json, os, re, sys, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent / "linkedin_cookies.json"
ARCHILLES_API = "http://178.105.245.120:8800/api/queue"

# Search queries — pairs of (keywords, location) for LinkedIn job search
SEARCHES = [
    ("python backend", "London, United Kingdom"),
    ("python developer", "London, United Kingdom"),
    ("ai engineer", "London, United Kingdom"),
    ("machine learning engineer", "London, United Kingdom"),
    ("software engineer graduate", "London, United Kingdom"),
    ("junior backend developer", "London, United Kingdom"),
    ("junior python developer", "London, United Kingdom"),
    ("platform engineer", "London, United Kingdom"),
    ("full stack python", "London, United Kingdom"),
    ("data engineer python", "London, United Kingdom"),
    ("backend engineer api", "Manchester, United Kingdom"),
    ("python developer remote", "United Kingdom"),
]


def load_cookies():
    if not COOKIES_FILE.exists():
        print(f"ERROR: Cookies not found at {COOKIES_FILE}")
        return None
    return json.loads(COOKIES_FILE.read_text())


def send_to_archilles(job: dict) -> bool:
    """POST a job to Archilles API queue. Returns True on success."""
    try:
        import urllib.request
        data = json.dumps({
            "title": job["title"],
            "company": job["company"],
            "location": job.get("location", "London"),
            "url": job.get("url", ""),
            "source": "linkedin_local",
            "jd_text": job.get("jd_text", f"{job['title']} at {job['company']} — {job.get('url', '')}"),
        }).encode()
        req = urllib.request.Request(ARCHILLES_API, data=data, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  API error: {e}")
        return False


async def scrape_search(context, keywords: str, location: str) -> list[dict]:
    """Scrape one LinkedIn job search. Returns list of job dicts."""
    import urllib.parse
    kw_enc = urllib.parse.quote(keywords)
    loc_enc = urllib.parse.quote(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={kw_enc}&location={loc_enc}&f_E=2"

    page = await context.new_page()
    jobs = []

    try:
        print(f"  Searching: {keywords} in {location}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        title = await page.title()
        if "login" in title.lower() or "sign up" in title.lower():
            print(f"  BLOCKED — LinkedIn auth required")
            return jobs

        # Extract job count from title
        count_match = re.search(r"(\d[\d,]*)", title)
        if count_match:
            print(f"  {count_match.group(1)} results")

        # Find all job links
        links = await page.query_selector_all("a")
        seen = set()

        for a in links[:200]:
            try:
                href = (await a.get_attribute("href")) or ""
                if "/jobs/view/" not in href:
                    continue

                text = (await a.inner_text()).strip()
                if len(text) < 10:
                    continue

                # Try to find parent li for company/location context
                parent_el = await a.evaluate("el => el.closest('li')")
                company = ""
                location_str = location

                if parent_el:
                    parent_text = (await page.evaluate("el => el?.innerText || ''", parent_el)).strip()
                    lines = parent_text.split("\n")
                    # Usually: title, company, location
                    if len(lines) >= 3:
                        company = lines[-2].strip()
                    elif len(lines) >= 2:
                        company = lines[-1].strip() if len(lines[-1]) < 50 else "Unknown"

                # Dedup by job ID from URL
                job_id_match = re.search(r"/jobs/view/[^/]+-(\d+)", href)
                job_id = job_id_match.group(1) if job_id_match else href
                if job_id in seen:
                    continue
                seen.add(job_id)

                if not company or company == text:
                    company = "Unknown"

                jobs.append({
                    "title": text[:120],
                    "company": company[:80],
                    "location": location,
                    "url": href.split("?")[0] if "?" in href else href,
                    "source": "linkedin_local",
                })

            except Exception:
                continue

    except Exception as e:
        print(f"  Error: {e}")
    finally:
        await page.close()

    unique = []
    seen_titles = set()
    for j in jobs:
        key = f"{j['title']}|{j['company']}"
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(j)

    print(f"  → {len(unique)} unique jobs")
    return unique


async def main(send: bool = False):
    cookies = load_cookies()
    if not cookies:
        return

    print(f"LinkedIn Local Scraper — {len(SEARCHES)} searches")
    all_jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
        )
        await context.add_cookies(cookies)

        for i, (keywords, location) in enumerate(SEARCHES):
            try:
                jobs = await scrape_search(context, keywords, location)
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  FAILED: {e}")

            # Rate limit between searches
            await asyncio.sleep(8 + (i % 3) * 3)

        await browser.close()

    # Dedup globally
    seen = set()
    unique = []
    for j in all_jobs:
        key = f"{j['title']}|{j['company']}"
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\nTotal unique jobs: {len(unique)}")

    if send:
        sent = 0
        for job in unique:
            if send_to_archilles(job):
                sent += 1
            else:
                print(f"  Failed: {job['title'][:60]} at {job['company']}")
        print(f"Sent {sent}/{len(unique)} jobs to Archilles")
    else:
        print("\nDRY RUN — use --send to actually queue jobs on Archilles")
        for j in unique[:10]:
            print(f"  {j['title'][:70]} | {j['company'][:30]} | {j['url'][:80]}")

    # Save local cache
    cache_file = Path("/tmp/linkedin_jobs_cache.json")
    cache_file.write_text(json.dumps(unique, indent=2))
    print(f"Cached to {cache_file}")


if __name__ == "__main__":
    send_flag = "--send" in sys.argv
    asyncio.run(main(send=send_flag))
