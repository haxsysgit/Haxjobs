#!/usr/bin/env python3
"""Graylist job discovery — parses recruitment agency sites and HR firm job boards.

Sources:
- MongooseJobs RSS: curl + XML parse (works without browser)
- Experis: browser-based (React SPA)
- BCG CareerHub: browser-based

For browser-based sources, this script is invoked via a Hermes cron job
with the agent browsing the site and saving intake JSONs.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from sharp_filter import save_intake

from haxjobs_config import INTAKE_DIR, DISCOVERY_LOG, HAXJOBS_HOME
LOG_FILE = str(DISCOVERY_LOG)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}


def log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_path = str(DISCOVERY_LOG)
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)


def scrape_mongoosejobs_rss():
    """Parse MongooseJobs RSS feed."""
    log("MongooseJobs RSS scraper starting...")

    try:
        resp = requests.get("https://www.mongoosejobs.com/jobs.rss", headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        log(f"ERROR: Failed to fetch MongooseJobs RSS: {e}")
        return 0

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        log(f"ERROR: Failed to parse MongooseJobs RSS XML: {e}")
        return 0

    queued = 0
    items = root.findall(".//item")
    log(f"Found {len(items)} items in MongooseJobs RSS")

    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        # Extract location from description
        location = "UK"
        loc_match = re.search(r"Location:\s*(.+?)(?:<|$)", desc, re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()

        # Extract company from title (format: "Job Title — Company Name")
        company = "Unknown"
        if " — " in title:
            parts = title.split(" — ")
            company = parts[-1].strip()
            title = parts[0].strip()
        elif " at " in title.lower():
            parts = title.lower().split(" at ")
            company = parts[-1].strip()
            title = title[: title.lower().rfind(" at ")].strip()

        # Clean HTML from description
        clean_desc = re.sub(r"<[^>]+>", " ", desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

        # Use sharp_filter for matching + dedup + save
        fname = save_intake(company, title, clean_desc, location, "mongoose_rss", link)
        if fname:
            queued += 1

    log(f"MongooseJobs RSS: queued {queued} jobs")
    return queued


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "all"

    if source in ("mongoose", "all"):
        scrape_mongoosejobs_rss()

    if source in ("experis", "all"):
        log("Experis requires browser-based scraping — use hermes cron with browser tools")
        log(f"See: {HAXJOBS_HOME}/discovery/experis_browser.md")

    if source in ("bcg", "all"):
        log("BCG CareerHub requires browser-based scraping — use hermes cron with browser tools")
        log(f"See: {HAXJOBS_HOME}/discovery/bcg_browser.md")


if __name__ == "__main__":
    main()
