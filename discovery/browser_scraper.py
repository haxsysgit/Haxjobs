#!/usr/bin/env python3
"""Generic Playwright job scraper for CareerMaxxing / HaxJobs.
Handles Reed, CWJobs, Experis, BCG CareerHub.
Searches for Python/backend/engineer roles in London/UK.
Filters through sharp_filter.py before queueing as intake.
"""
import asyncio, json, os, sys, subprocess, re
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

HAXJOBS_DIR = "/home/hermes/haxjobs"
INTAKE_DIR = os.path.join(HAXJOBS_DIR, "intake")
SHARP_FILTER = os.path.join(HAXJOBS_DIR, "discovery", "sharp_filter.py")
LOG_FILE = os.path.join(HAXJOBS_DIR, "state", "discovery.log")

# Site-specific configs
SITES = {
    "reed": {
        "name": "Reed.co.uk",
        "base": "https://www.reed.co.uk",
        "search_url": "https://www.reed.co.uk/jobs/python-developer-jobs-in-london?pageno={page}",
        "selectors": {
            "cards": ".job-card, article.job-result, [data-qa=job-result]",
            "title": ".job-title, [data-qa=job-title], h3 a",
            "company": ".company-name, [data-qa=employer-name]",
            "location": ".location, [data-qa=job-location]",
            "link": ".job-title a, [data-qa=job-title] a, h3 a",
        },
        "max_pages": 3,
    },
    "cwjobs": {
        "name": "CWJobs",
        "base": "https://www.cwjobs.co.uk",
        "search_url": "https://www.cwjobs.co.uk/jobs/python-backend/in-london?page={page}",
        "selectors": {
            "cards": ".job, article.job, .job-result, [data-test=job-card]",
            "title": ".job-title, [data-test=job-title], h2 a",
            "company": ".company, [data-test=company-name]",
            "location": ".location, [data-test=job-location]",
            "link": ".job-title a, h2 a",
        },
        "max_pages": 3,
    },
    "experis": {
        "name": "Experis",
        "base": "https://www.experis.co.uk",
        "search_url": "https://www.experis.co.uk/jobs/?q=python+backend+engineer&location=london&page={page}",
        "selectors": {
            "cards": ".job-listing, .search-result, article",
            "title": ".job-title, h3, h4 a, [class*=title]",
            "company": ".company, [class*=company]",
            "location": ".location, [class*=location]",
            "link": "a[href*=job], .job-title a, h3 a",
        },
        "max_pages": 2,
    },
    "reed_ai": {
        "name": "Reed.co.uk (AI Engineer)",
        "base": "https://www.reed.co.uk",
        "search_url": "https://www.reed.co.uk/jobs/ai-engineer-jobs-in-london?pageno={page}",
        "selectors": {
            "cards": ".job-card, article.job-result, [data-qa=job-result]",
            "title": ".job-title, [data-qa=job-title], h3 a",
            "company": ".company-name, [data-qa=employer-name]",
            "location": ".location, [data-qa=job-location]",
            "link": ".job-title a, [data-qa=job-title] a, h3 a",
        },
        "max_pages": 3,
    },
    "reed_ml": {
        "name": "Reed.co.uk (ML Engineer)",
        "base": "https://www.reed.co.uk",
        "search_url": "https://www.reed.co.uk/jobs/machine-learning-engineer-jobs-in-london?pageno={page}",
        "selectors": {
            "cards": ".job-card, article.job-result, [data-qa=job-result]",
            "title": ".job-title, [data-qa=job-title], h3 a",
            "company": ".company-name, [data-qa=employer-name]",
            "location": ".location, [data-qa=job-location]",
            "link": ".job-title a, [data-qa=job-title] a, h3 a",
        },
        "max_pages": 3,
    },
    "cwjobs_ai": {
        "name": "CWJobs (AI Engineer)",
        "base": "https://www.cwjobs.co.uk",
        "search_url": "https://www.cwjobs.co.uk/jobs/ai-engineer/in-london?page={page}",
        "selectors": {
            "cards": ".job, article.job, .job-result, [data-test=job-card]",
            "title": ".job-title, [data-test=job-title], h2 a",
            "company": ".company, [data-test=company-name]",
            "location": ".location, [data-test=job-location]",
            "link": ".job-title a, h2 a",
        },
        "max_pages": 3,
    },
    "cwjobs_ml": {
        "name": "CWJobs (ML Engineer)",
        "base": "https://www.cwjobs.co.uk",
        "search_url": "https://www.cwjobs.co.uk/jobs/machine-learning/in-london?page={page}",
        "selectors": {
            "cards": ".job, article.job, .job-result, [data-test=job-card]",
            "title": ".job-title, [data-test=job-title], h2 a",
            "company": ".company, [data-test=company-name]",
            "location": ".location, [data-test=job-location]",
            "link": ".job-title a, h2 a",
        },
        "max_pages": 3,
    },
    "experis_ai": {
        "name": "Experis (AI Engineer)",
        "base": "https://www.experis.co.uk",
        "search_url": "https://www.experis.co.uk/jobs/?q=ai+engineer&location=london&page={page}",
        "selectors": {
            "cards": ".job-listing, .search-result, article",
            "title": ".job-title, h3, h4 a, [class*=title]",
            "company": ".company, [class*=company]",
            "location": ".location, [class*=location]",
            "link": "a[href*=job], .job-title a, h3 a",
        },
        "max_pages": 2,
    },
    "bcg": {
        "name": "BCG CareerHub",
        "base": "https://experiencedtalent.bcg.com",
        "search_url": "https://experiencedtalent.bcg.com/careerhub",
        "selectors": {
            "cards": ".job-listing, .position, [class*=job]",
            "title": "h3, h4, [class*=title]",
            "company": ".department, [class*=dept]",
            "location": ".location, [class*=location]",
            "link": "a[href*=job], a[href*=position]",
        },
        "max_pages": 1,
        "needs_login": True,
    },
}

CURRENT_SITE_KEY = None


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [{CURRENT_SITE_KEY}] {msg}" if CURRENT_SITE_KEY else f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def already_queued(title, company):
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
    try:
        r = subprocess.run(
            [sys.executable, SHARP_FILTER, "check", title, location or "", description[:500]],
            capture_output=True, text=True, timeout=10
        )
        return "PASS" in r.stdout or r.returncode == 0
    except:
        return False

def queue_intake(company, title, jd_text, location, url, source):
    os.makedirs(INTAKE_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_company = company.replace(" ", "_")[:30]
    safe_title = title.replace(" ", "_").replace("/", "_")[:50]
    fname = f"{ts}_{source}_{safe_company}_{safe_title}.json"

    intake = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
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


async def scrape(site_key):
    global CURRENT_SITE_KEY
    CURRENT_SITE_KEY = site_key
    cfg = SITES[site_key]
    log(f"Starting {cfg['name']} scraper...")
    queued = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for pg in range(1, cfg["max_pages"] + 1):
            url = cfg["search_url"].format(page=pg)
            log(f"  Page {pg}: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Click through cookie walls if present
                try:
                    cookie_btn = await page.query_selector("button:has-text('Accept'), button:has-text('Accept All'), button:has-text('OK')")
                    if cookie_btn:
                        await cookie_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass

                sel = cfg["selectors"]
                cards = await page.query_selector_all(sel["cards"])
                if not cards:
                    # Fallback: grab all links that look like job URLs
                    cards = await page.query_selector_all("a[href*=job], a[href*=vacancy], a[href*=position]")

                for card in cards[:20]:
                    try:
                        title_el = await card.query_selector(sel["title"])
                        company_el = await card.query_selector(sel["company"])
                        location_el = await card.query_selector(sel["location"])
                        link_el = await card.query_selector(sel["link"])

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                        location = (await location_el.inner_text()).strip() if location_el else "UK"
                        url = await link_el.get_attribute("href") if link_el else ""
                        if url and not url.startswith("http"):
                            url = cfg["base"] + url

                        if not title or len(title) < 5:
                            continue
                        if not run_sharp_filter(title, location, title):
                            continue
                        if already_queued(title, company):
                            continue

                        fname = queue_intake(company, title, title, location, url, site_key)
                        log(f"  QUEUED: {title[:60]} at {company}")
                        queued += 1

                    except Exception as e:
                        continue

            except Exception as e:
                log(f"  Error page {pg}: {e}")
                continue

        await browser.close()

    log(f"Complete. {queued} jobs queued.")
    return queued


if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "reed"
    if site not in SITES:
        print(f"Unknown site: {site}. Options: {list(SITES.keys())}")
        sys.exit(1)
    asyncio.run(scrape(site))
