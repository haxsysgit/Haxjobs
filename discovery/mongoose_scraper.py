#!/usr/bin/env python3
"""MongooseJobs Playwright scraper for CareerMaxxing.
Searches https://www.mongoosejobs.com/ for Python/backend/engineer roles in London/UK.
Filters through sharp_filter.py before queueing as intake.
"""
import asyncio, json, os, sys, subprocess
from datetime import datetime, timezone
from playwright.async_api import async_playwright

INTAKE_DIR = "/home/hermes/haxjobs/intake"
SHARP_FILTER = "/home/hermes/haxjobs/discovery/sharp_filter.py"
LOG_FILE = "/home/hermes/haxjobs/state/discovery.log"
BASE_URL = "https://www.mongoosejobs.com"

SEARCH_TERMS = [
    "python backend engineer london",
    "python developer uk",
    "backend engineer london",
    "software engineer python uk",
]

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [mongoose] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def already_queued(title, company):
    """Check if this job was already queued in the last 7 days."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    if not os.path.isdir(INTAKE_DIR):
        return False
    for fname in os.listdir(INTAKE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(INTAKE_DIR, fname)))
            if d.get("title") == title and d.get("company") == company:
                if d.get("received_at", "") > cutoff.isoformat():
                    return True
        except:
            continue
    return False

def run_sharp_filter(title, location, description=""):
    """Check if job passes sharp_filter."""
    try:
        r = subprocess.run(
            [sys.executable, SHARP_FILTER, "check", title, location or "", description[:500]],
            capture_output=True, text=True, timeout=10
        )
        return "PASS" in r.stdout or r.returncode == 0
    except:
        return False

def queue_intake(company, title, jd_text, location, url):
    """Create pending intake file."""
    os.makedirs(INTAKE_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_company = company.replace(" ", "_")[:30]
    safe_title = title.replace(" ", "_").replace("/", "_")[:50]
    fname = f"{ts}_mongoose_{safe_company}_{safe_title}.json"

    intake = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": "mongoose_jobs",
        "source_url": url,
        "company": company,
        "title": title,
        "location": location,
        "jd_text": jd_text,
        "status": "pending",
    }
    with open(os.path.join(INTAKE_DIR, fname), "w") as f:
        json.dump(intake, f, indent=2)
    return fname


async def scrape():
    log("Starting MongooseJobs scraper...")
    queued = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for term in SEARCH_TERMS:
            log(f"Searching: {term}")
            try:
                await page.goto(f"{BASE_URL}/?search={term.replace(' ', '+')}", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Extract job cards — MongooseJobs uses standard job listing HTML
                cards = await page.query_selector_all("article, .job-card, .listing-item, [class*=job]")

                for card in cards:
                    try:
                        title_el = await card.query_selector("h2, h3, .title, [class*=title]")
                        company_el = await card.query_selector(".company, [class*=company], .employer")
                        location_el = await card.query_selector(".location, [class*=location]")
                        link_el = await card.query_selector("a[href]")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                        location = (await location_el.inner_text()).strip() if location_el else "UK"
                        url = await link_el.get_attribute("href") if link_el else ""
                        if url and not url.startswith("http"):
                            url = BASE_URL + url

                        if not title:
                            continue

                        # Check sharp_filter
                        if not run_sharp_filter(title, location, title):
                            continue

                        if already_queued(title, company):
                            log(f"  SKIP (dup): {title} at {company}")
                            continue

                        # Try to get full JD
                        jd_text = title  # Default to title if can't get full JD
                        if url:
                            try:
                                jd_page = await context.new_page()
                                await jd_page.goto(url, wait_until="domcontentloaded", timeout=15000)
                                jd_text = await jd_page.inner_text("body")
                                await jd_page.close()
                            except:
                                pass

                        fname = queue_intake(company, title, jd_text, location, url)
                        log(f"  QUEUED: {title} at {company} -> {fname}")
                        queued += 1

                    except Exception as e:
                        log(f"  Card error: {e}")
                        continue

            except Exception as e:
                log(f"Search error for '{term}': {e}")
                continue

        await browser.close()

    log(f"Complete. {queued} jobs queued.")
    return queued


if __name__ == "__main__":
    asyncio.run(scrape())
