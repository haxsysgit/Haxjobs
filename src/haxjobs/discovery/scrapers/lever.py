"""Lever scraper for the HaxJobs discovery pipeline."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from haxjobs.db.schema import init
from haxjobs.db.discovered_jobs import insert_discovered_job
from haxjobs.discovery.normalize import normalize_job
from haxjobs.discovery.profile_search import job_matches_profile, parse_cli_search_terms
from haxjobs.discovery.scrapers.greenhouse import extract_jd_text, normalize_whitespace
from haxjobs.config import DISCOVERY_CONFIG

LEVER_API_TEMPLATE = "https://api.lever.co/v0/postings/{company}?mode=json"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "HaxJobs Lever Scraper/1.0"


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch Lever postings for one company slug."""
    encoded_company = urllib.parse.quote(company)
    request = urllib.request.Request(
        LEVER_API_TEMPLATE.format(company=encoded_company),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        return []
    return [job for job in payload if isinstance(job, dict)]


def get_location_name(job: dict[str, Any]) -> str:
    """Read Lever's nested categories.location safely."""
    categories = job.get("categories")
    if isinstance(categories, dict):
        return str(categories.get("location") or "").strip()
    return ""


def get_jd_text(job: dict[str, Any]) -> str:
    """Prefer Lever plain text, then fall back to HTML cleanup."""
    description_plain = normalize_whitespace(str(job.get("descriptionPlain") or ""))
    if description_plain:
        return description_plain
    return extract_jd_text(str(job.get("description") or ""))


def build_raw_job(company: str, job: dict[str, Any]) -> dict[str, Any]:
    """Convert one Lever posting into normalize_job-friendly raw data."""
    hosted_url = str(job.get("hostedUrl") or "").strip()
    apply_url = str(job.get("applyUrl") or hosted_url).strip()
    return {
        "title": str(job.get("text") or "").strip(),
        "company": company,
        "location": get_location_name(job),
        "source_url": hosted_url,
        "apply_url": apply_url,
        "external_id": str(job.get("id") or "").strip(),
        "jd_text": get_jd_text(job),
        "ats": "lever",
        "raw_payload": job,
    }


def filter_profile_jobs(jobs: list[dict[str, Any]], search_terms: list[str]) -> list[dict[str, Any]]:
    """Keep only Lever roles that look relevant to Arinze's profile."""
    matched_jobs: list[dict[str, Any]] = []
    for job in jobs:
        title = str(job.get("text") or "")
        location = get_location_name(job)
        if job_matches_profile(title, location, search_terms):
            matched_jobs.append(job)
    return matched_jobs


def scrape_lever_company(company: str, search_terms: list[str] | None = None) -> dict[str, int]:
    """Scrape one Lever company and insert new discovered jobs."""
    jobs = fetch_jobs(company)
    matched_jobs = filter_profile_jobs(jobs, search_terms or parse_cli_search_terms([]))
    new_count = 0
    for job in matched_jobs:
        raw_job = build_raw_job(company, job)
        normalized_job = normalize_job(raw_job, source="lever")
        row_id = insert_discovered_job(normalized_job)
        if row_id is not None:
            new_count += 1

    print(f"Scraped {company}: {len(jobs)} Lever jobs found, {len(matched_jobs)} profile matches, {new_count} new")
    return {"found": len(jobs), "matched": len(matched_jobs), "new": new_count, "errors": 0}


def configured_lever_companies() -> list[str]:
    """Read configured Lever company slugs from haxjobs.toml."""
    companies = DISCOVERY_CONFIG.get("lever_companies", [])
    if not isinstance(companies, list):
        return []
    return [str(company) for company in companies]


def scrape_lever_companies(companies: list[str], search_terms: list[str] | None = None) -> dict[str, dict[str, int]]:
    """Scrape multiple Lever company slugs."""
    results: dict[str, dict[str, int]] = {}
    active_search_terms = search_terms or parse_cli_search_terms([])
    for company in companies:
        clean_company = company.strip()
        if not clean_company:
            continue
        try:
            results[clean_company] = scrape_lever_company(clean_company, active_search_terms)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Scraped {clean_company}: Lever failed ({exc})", file=sys.stderr)
            results[clean_company] = {"found": 0, "new": 0, "errors": 1}
    return results


def scrape_lever(companies: list[str] | None = None, search_terms: list[str] | None = None) -> dict[str, dict[str, int]]:
    """Scrape configured or provided Lever companies."""
    selected_companies = companies if companies is not None else configured_lever_companies()
    return scrape_lever_companies(selected_companies, search_terms)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Lever scraper CLI arguments."""
    parser = argparse.ArgumentParser(prog="lever.py")
    parser.add_argument("--company", action="append", default=[])
    parser.add_argument("--companies", nargs="*", default=[])
    parser.add_argument("--query", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Lever scraping."""
    args = parse_args(argv)
    companies = [*args.company, *args.companies]
    if not companies:
        companies = configured_lever_companies()
    if not companies:
        print("No Lever companies configured. Use --company or --companies.", file=sys.stderr)
        return 2
    init()
    scrape_lever_companies(companies, parse_cli_search_terms(args.query))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
