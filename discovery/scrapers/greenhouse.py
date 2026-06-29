"""Greenhouse scraper for the HaxJobs discovery pipeline."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from db.discovered_jobs import insert_discovered_job
from discovery.normalize import normalize_job
from haxjobs_config import DISCOVERY_CONFIG

GREENHOUSE_API_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
LEGACY_EMBED_TEMPLATE = "https://boards.greenhouse.io/embed/job_board?for={company}"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "HaxJobs Greenhouse Scraper/1.0"


class JobDescriptionParser(HTMLParser):
    """Extract readable text from Greenhouse job description HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._text_parts.append(text)

    def text(self) -> str:
        return normalize_whitespace(" ".join(self._text_parts))


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace into a single readable space."""
    return re.sub(r"\s+", " ", text or "").strip()


def decode_html_text(html_text: str) -> str:
    """Decode Greenhouse escaped HTML until tags become real markup."""
    decoded_text = html_text or ""
    for _ in range(3):
        next_text = html.unescape(decoded_text)
        if next_text == decoded_text:
            break
        decoded_text = next_text
    return decoded_text


def extract_jd_text(html_text: str) -> str:
    """Turn a Greenhouse HTML description into clean plain text."""
    decoded_text = decode_html_text(html_text)
    selected_html = select_description_html(decoded_text)

    parser = JobDescriptionParser()
    parser.feed(selected_html)
    return parser.text()


def select_description_html(html_text: str) -> str:
    """Pick the likely job description container when a full page is provided."""
    for pattern in (
        r'<div[^>]+id=["\']content["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*job__description[^"\']*["\'][^>]*>(.*?)</div>',
    ):
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return html_text


def fetch_json(url: str) -> dict[str, Any]:
    """Fetch a JSON URL using urllib only."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body)


def fetch_text(url: str) -> str:
    """Fetch a text page using urllib only."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch Greenhouse jobs for one board slug.

    Greenhouse's older embed endpoint now serves HTML for some companies. The
    public boards API still returns JSON and supports ``content=true``, which
    gives us the full JD without extra page scraping for most boards.
    """
    encoded_company = urllib.parse.quote(company)
    api_url = GREENHOUSE_API_TEMPLATE.format(company=encoded_company)
    try:
        payload = fetch_json(api_url)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        legacy_url = LEGACY_EMBED_TEMPLATE.format(company=encoded_company)
        payload = fetch_json(legacy_url)

    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return []
    return [job for job in jobs if isinstance(job, dict)]


def get_location_name(job: dict[str, Any]) -> str:
    """Read Greenhouse's nested location object safely."""
    location = job.get("location")
    if isinstance(location, dict):
        return str(location.get("name") or "").strip()
    if isinstance(location, str):
        return location.strip()
    return ""


def fetch_detail_description(job_url: str) -> str:
    """Fetch and parse a detail page when the API payload lacks content."""
    if not job_url:
        return ""

    try:
        page_html = fetch_text(job_url)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return ""

    return extract_jd_text(page_html)


def build_raw_job(company: str, job: dict[str, Any]) -> dict[str, Any]:
    """Convert one Greenhouse API job into normalize_job-friendly raw data."""
    job_url = str(job.get("absolute_url") or "").strip()
    content_html = str(job.get("content") or "")
    jd_text = extract_jd_text(content_html) if content_html else ""
    if not jd_text:
        # ponytail: only hit detail pages when content=true is missing; most
        # boards already return the full JD in API payloads.
        jd_text = fetch_detail_description(job_url)
        time.sleep(1)

    external_id = job.get("id") or job.get("internal_job_id") or ""
    return {
        "title": str(job.get("title") or "").strip(),
        "company": company,
        "location": get_location_name(job),
        "source_url": job_url,
        "apply_url": job_url,
        "external_id": str(external_id),
        "jd_text": jd_text,
        "ats": "greenhouse",
        "raw_payload": job,
    }


def scrape_greenhouse_company(company: str) -> dict[str, int]:
    """Scrape one Greenhouse board and insert new discovered jobs."""
    jobs = fetch_jobs(company)
    new_count = 0

    for job in jobs:
        raw_job = build_raw_job(company, job)
        normalized_job = normalize_job(raw_job, source="greenhouse")
        row_id = insert_discovered_job(normalized_job)
        if row_id is not None:
            new_count += 1

    print(f"Scraped {company}: {len(jobs)} jobs found, {new_count} new")
    return {"found": len(jobs), "new": new_count}


def scrape_greenhouse_companies(companies: list[str]) -> dict[str, dict[str, int]]:
    """Scrape multiple Greenhouse board slugs."""
    results: dict[str, dict[str, int]] = {}
    for company in companies:
        clean_company = company.strip()
        if not clean_company:
            continue
        try:
            results[clean_company] = scrape_greenhouse_company(clean_company)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Scraped {clean_company}: failed ({exc})", file=sys.stderr)
            results[clean_company] = {"found": 0, "new": 0}
    return results


def configured_greenhouse_companies() -> list[str]:
    """Read configured Greenhouse board slugs from haxjobs.toml."""
    companies = DISCOVERY_CONFIG.get("greenhouse_companies", [])
    if not isinstance(companies, list):
        return []
    return [str(company) for company in companies]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the Greenhouse scraper CLI arguments."""
    parser = argparse.ArgumentParser(prog="greenhouse.py")
    parser.add_argument("--company", action="append", default=[], help="Greenhouse board slug to scrape")
    parser.add_argument("--companies", nargs="*", default=[], help="One or more Greenhouse board slugs to scrape")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Greenhouse scraping."""
    args = parse_args(argv)
    companies = [*args.company, *args.companies]
    if not companies:
        companies = configured_greenhouse_companies()
    if not companies:
        print("No Greenhouse companies configured. Use --company or --companies.", file=sys.stderr)
        return 2

    scrape_greenhouse_companies(companies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
