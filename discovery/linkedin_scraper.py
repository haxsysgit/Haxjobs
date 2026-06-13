#!/usr/bin/env python3
"""LinkedIn company career page scraper for HaxJobs.

Uses Playwright with cookie injection to browse LinkedIn company job pages.
No LLM/Hermes required — scrapes, filters, and queues intake directly.

Usage:
  python3 discovery/linkedin_scraper.py           # All companies
  python3 discovery/linkedin_scraper.py palantir  # Single company
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.async_api import async_playwright

HAXJOBS_DIR = "/home/hermes/haxjobs"
INTAKE_DIR = os.path.join(HAXJOBS_DIR, "intake")
COOKIES_FILE = os.path.join(HAXJOBS_DIR, "discovery", "linkedin_cookies.json")
LOG_FILE = os.path.join(HAXJOBS_DIR, "state", "discovery.log")
COMPANIES_FILE = os.path.join(HAXJOBS_DIR, "discovery", "linkedin_companies.json")

# Default companies to monitor — LinkedIn company slugs
DEFAULT_COMPANIES = [
    {"slug": "palantir-technologies", "name": "Palantir"},
    {"slug": "monzo-bank", "name": "Monzo"},
    {"slug": "spotify", "name": "Spotify"},
    {"slug": "notion", "name": "Notion"},
    {"slug": "vercel", "name": "Vercel"},
    {"slug": "linear", "name": "Linear"},
    {"slug": "stripe", "name": "Stripe"},
    {"slug": "plaid-", "name": "Plaid"},
    {"slug": "canva", "name": "Canva"},
    {"slug": "figma", "name": "Figma"},
    {"slug": "airtable", "name": "Airtable"},
    {"slug": "docker", "name": "Docker"},
    {"slug": "databricks", "name": "Databricks"},
    {"slug": "snowflake-computing", "name": "Snowflake"},
    {"slug": "confluent", "name": "Confluent"},
    {"slug": "hashicorp", "name": "HashiCorp"},
    {"slug": "elastic-co", "name": "Elastic"},
    {"slug": "grafana-labs", "name": "Grafana"},
    {"slug": "redis", "name": "Redis"},
    {"slug": "mongodb", "name": "MongoDB"},
    {"slug": "anthropic", "name": "Anthropic"},
    {"slug": "cohere", "name": "Cohere"},
    {"slug": "deepmind", "name": "DeepMind"},
    {"slug": "huggingface", "name": "Hugging Face"},
    {"slug": "stability-ai", "name": "Stability AI"},
    {"slug": "revolut", "name": "Revolut"},
    {"slug": "wise", "name": "Wise"},
    {"slug": "checkout", "name": "Checkout.com"},
    {"slug": "gocardless", "name": "GoCardless"},
    {"slug": "truelayer", "name": "TrueLayer"},
    {"slug": "sumup", "name": "SumUp"},
    {"slug": "intercom", "name": "Intercom"},
    {"slug": "atlassian", "name": "Atlassian"},
    {"slug": "gitlab", "name": "GitLab"},
    {"slug": "datadog", "name": "Datadog"},
    {"slug": "twilio", "name": "Twilio"},
    {"slug": "cloudflare", "name": "Cloudflare"},
    {"slug": "deliveroo", "name": "Deliveroo"},
    {"slug": "miro", "name": "Miro"},
    {"slug": "hubspot", "name": "HubSpot"},
    {"slug": "asana", "name": "Asana"},
    {"slug": "servicenow", "name": "ServiceNow"},
    {"slug": "thoughtworks", "name": "Thoughtworks"},
    {"slug": "endava", "name": "Endava"},
    {"slug": "freeagent", "name": "FreeAgent"},
    {"slug": "trainline", "name": "Trainline"},
]

# UK location keywords for filtering
UK_PATTERNS = [
    "london", "manchester", "leeds", "uk", "united kingdom", "england",
    "scotland", "wales", "ireland", "remote uk", "remote", "hybrid uk",
    "birmingham", "bristol", "edinburgh", "glasgow", "cambridge", "oxford",
    "reading", "brighton", "nottingham", "sheffield", "liverpool", "newcastle",
    "cardiff", "belfast", "dublin", "cork", "galway", "europe",
]

# Engineering role keywords — case-insensitive match in title
ENGINEERING_PATTERNS = [
    r"\bsoftware engineer\b", r"\bbackend\b", r"\bfrontend\b", r"\bfull.?stack\b",
    r"\bdevops\b", r"\bplatform engineer\b", r"\bsre\b", r"\breliability\b",
    r"\bdata (engineer|scientist)\b", r"\bmachine learning\b", r"\bml engineer\b",
    r"\bai engineer\b", r"\bpython\b", r"\bjava\b", r"\bgo\b", r"\bgolang\b",
    r"\brust\b", r"\btypescript\b", r"\bjavascript\b", r"\breact\b",
    r"\bapi\b", r"\bcloud engineer\b", r"\binfrastructure\b", r"\bsecurity engineer\b",
    r"\bqa engineer\b", r"\btest engineer\b", r"\bautomation engineer\b",
    r"\bdeveloper\b", r"\bprogrammer\b", r"\bcoder\b",
]


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [linkedin] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_cookies():
    if not os.path.exists(COOKIES_FILE):
        log(f"ERROR: Cookies file not found: {COOKIES_FILE}")
        return None
    with open(COOKIES_FILE) as f:
        return json.load(f)


def load_companies():
    if os.path.exists(COMPANIES_FILE):
        with open(COMPANIES_FILE) as f:
            return json.load(f)
    return DEFAULT_COMPANIES


def is_uk_location(text: str) -> bool:
    text = text.lower() if text else ""
    return any(p in text for p in UK_PATTERNS)


def is_engineering(title: str) -> bool:
    title_lower = title.lower()
    for pattern in ENGINEERING_PATTERNS:
        if re.search(pattern, title_lower):
            return True
    return False


def already_queued(title, company):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    if not os.path.isdir(INTAKE_DIR):
        return False
    for fname in os.listdir(INTAKE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(INTAKE_DIR, fname)) as f:
                d = json.load(f)
            if d.get("title") == title and d.get("company") == company:
                if d.get("received_at", "") > cutoff.isoformat():
                    return True
        except Exception:
            continue
    return False


def save_intake(company, title, location, url):
    os.makedirs(INTAKE_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_company = re.sub(r"[^a-zA-Z0-9]", "_", company)[:40]
    safe_title = re.sub(r"[^a-zA-Z0-9]", "_", title)[:60]
    fname = f"{ts}_linkedin_{safe_company}_{safe_title}.json"

    intake = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": "linkedin",
        "source_url": url,
        "company": company,
        "title": title,
        "location": location,
        "jd_text": f"{title} at {company} in {location}\n{url}",
        "status": "pending",
    }

    with open(os.path.join(INTAKE_DIR, fname), "w") as f:
        json.dump(intake, f, indent=2)

    return fname


async def scrape_company_jobs(context, company_info):
    slug = company_info["slug"]
    name = company_info["name"]
    jobs_url = f"https://www.linkedin.com/company/{slug}/jobs"

    log(f"  Visiting: {jobs_url}")
    page = await context.new_page()

    try:
        await page.goto(jobs_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Scroll to load dynamic content
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

        # Find job cards/listings
        job_elements = await page.query_selector_all(
            ".job-card-container, .jobs-search-results__list-item, "
            ".job-card-list__title, [data-job-id], li.jobs-search-results__job-card"
        )

        if not job_elements:
            # Try alternate selectors
            job_elements = await page.query_selector_all(
                "a[href*='/jobs/view/'], a[data-tracking-control-name*='job']"
            )

        queued = 0
        seen = set()

        for el in job_elements[:30]:
            try:
                # Try to find title
                title_el = await el.query_selector(
                    ".job-card-list__title, .job-card-container__title, "
                    "a[href*='/jobs/view/'], h3, strong"
                )
                title = (await title_el.inner_text()).strip() if title_el else ""
                title = title.replace("\n", " ").strip()[:120]

                if not title or len(title) < 5:
                    continue

                # Try to find location
                location_el = await el.query_selector(
                    ".job-card-container__metadata-item, "
                    ".job-card-list__location, [class*=location]"
                )
                location = (await location_el.inner_text()).strip() if location_el else "Unknown"

                # Try to find link
                link_el = await el.query_selector("a[href*='/jobs/view/']")
                if not link_el:
                    link_el = await el.query_selector("a")
                url = await link_el.get_attribute("href") if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://www.linkedin.com" + url

                # Dedup within this scrape run
                dedup_key = f"{title}@{name}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                # Filter: must be engineering role
                if not is_engineering(title):
                    continue

                # Filter: must be UK/remote location
                if location != "Unknown" and not is_uk_location(location):
                    continue

                # Filter: check sharp_filter (non-engineering, senior+)
                passes, reason = check_sharp_filter(title, location)
                if not passes:
                    continue

                # Dedup against existing intake
                if already_queued(title, name):
                    continue

                fname = save_intake(name, title, location, url)
                log(f"    QUEUED: {title[:60]} ({location})")
                queued += 1

            except Exception:
                continue

        return queued

    except Exception as e:
        log(f"    Error: {e}")
        return 0
    finally:
        await page.close()


def check_sharp_filter(title, location=""):
    """Minimal inline sharp_filter check — avoids subprocess call overhead."""
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HAXJOBS_DIR, "discovery", "sharp_filter.py"),
             "check", title, location or "", ""],
            capture_output=True, text=True, timeout=5
        )
        return "PASS" in r.stdout, ""
    except Exception:
        return True, ""


async def main(target_company=None):
    cookies = load_cookies()
    if not cookies:
        log("FATAL: No cookies loaded. Aborting.")
        return

    companies = load_companies()
    if target_company:
        companies = [c for c in companies if c["slug"] == target_company or c["name"].lower() == target_company.lower()]
        if not companies:
            log(f"Company '{target_company}' not found in list.")
            return
        log(f"Scraping single company: {companies[0]['name']}")

    log(f"Starting LinkedIn scraper — {len(companies)} companies")
    total_queued = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )

        # Inject cookies
        await context.add_cookies(cookies)

        # Verify login by checking homepage
        test_page = await context.new_page()
        try:
            await test_page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            await test_page.wait_for_timeout(3000)
            title = await test_page.title()
            if "login" in title.lower() or "sign in" in title.lower():
                log("WARNING: LinkedIn cookies may be expired — page shows login")
            else:
                log(f"LinkedIn session OK — page title: {title[:80]}")
        except Exception as e:
            log(f"WARNING: Could not verify session: {e}")
        finally:
            await test_page.close()

        # Scrape each company
        for i, company in enumerate(companies):
            log(f"[{i+1}/{len(companies)}] {company['name']} ({company['slug']})")
            try:
                queued = await scrape_company_jobs(context, company)
                total_queued += queued
            except Exception as e:
                log(f"  FAILED: {e}")
            # Rate limit: 30-60s between companies (LinkedIn bot detection from VPS)
            base_delay = 30
            await asyncio.sleep(base_delay + (i % 5) * 6)

        await browser.close()

    log(f"Complete. {total_queued} jobs queued from {len(companies)} companies.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(target))
