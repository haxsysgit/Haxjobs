"""Ashby scraper for the HaxJobs discovery pipeline."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from db.schema import init
from db.discovered_jobs import insert_discovered_job
from discovery.normalize import normalize_job
from discovery.scrapers.greenhouse import extract_jd_text
from haxjobs_config import DISCOVERY_CONFIG

ASHBY_GRAPHQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op={operation}"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "HaxJobs Ashby Scraper/1.0"

JOB_BOARD_QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
    jobPostings {
      id
      title
      locationName
      employmentType
      teamId
      secondaryLocations { locationName }
    }
  }
}
"""

JOB_POSTING_QUERY = """
query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
    id
    title
    locationName
    employmentType
    descriptionHtml
  }
}
"""


def post_graphql(company: str, operation: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """POST one Ashby non-user GraphQL request."""
    payload = json.dumps({
        "operationName": operation,
        "variables": variables,
        "query": query,
    }).encode("utf-8")
    request = urllib.request.Request(
        ASHBY_GRAPHQL_URL.format(operation=operation),
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Referer": f"https://jobs.ashbyhq.com/{company}",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch Ashby job posting summaries for one hosted board."""
    payload = post_graphql(
        company,
        "ApiJobBoardWithTeams",
        JOB_BOARD_QUERY,
        {"organizationHostedJobsPageName": company},
    )
    job_board = payload.get("data", {}).get("jobBoard")
    if not isinstance(job_board, dict):
        return []

    jobs = job_board.get("jobPostings", [])
    if not isinstance(jobs, list):
        return []
    return [job for job in jobs if isinstance(job, dict)]


def fetch_job_detail(company: str, job_id: str) -> dict[str, Any]:
    """Fetch one Ashby job posting detail, including descriptionHtml."""
    payload = post_graphql(
        company,
        "ApiJobPosting",
        JOB_POSTING_QUERY,
        {
            "organizationHostedJobsPageName": company,
            "jobPostingId": job_id,
        },
    )
    job = payload.get("data", {}).get("jobPosting")
    if isinstance(job, dict):
        return job
    return {}


def get_location_name(job: dict[str, Any]) -> str:
    """Read Ashby primary and secondary locations into one string."""
    locations: list[str] = []
    primary_location = str(job.get("locationName") or "").strip()
    if primary_location:
        locations.append(primary_location)

    secondary_locations = job.get("secondaryLocations", [])
    if isinstance(secondary_locations, list):
        for location in secondary_locations:
            if not isinstance(location, dict):
                continue
            location_name = str(location.get("locationName") or "").strip()
            if location_name and location_name not in locations:
                locations.append(location_name)

    return ", ".join(locations)


def build_raw_job(company: str, job: dict[str, Any]) -> dict[str, Any]:
    """Convert one Ashby job into normalize_job-friendly raw data."""
    job_id = str(job.get("id") or "").strip()
    detail = fetch_job_detail(company, job_id) if job_id and "descriptionHtml" not in job else job
    description_html = str(detail.get("descriptionHtml") or "")
    job_url = f"https://jobs.ashbyhq.com/{company}/{job_id}"

    return {
        "title": str(detail.get("title") or job.get("title") or "").strip(),
        "company": company,
        "location": get_location_name(detail or job),
        "source_url": job_url,
        "apply_url": job_url,
        "external_id": job_id,
        "jd_text": extract_jd_text(description_html),
        "ats": "ashby",
        "raw_payload": {"summary": job, "detail": detail},
    }


def scrape_ashby_company(company: str) -> dict[str, int]:
    """Scrape one Ashby board and insert new discovered jobs."""
    jobs = fetch_jobs(company)
    new_count = 0
    error_count = 0

    for job in jobs:
        try:
            raw_job = build_raw_job(company, job)
            normalized_job = normalize_job(raw_job, source="ashby")
            row_id = insert_discovered_job(normalized_job)
            if row_id is not None:
                new_count += 1
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            error_count += 1
        time.sleep(0.25)

    print(f"Scraped {company}: {len(jobs)} Ashby jobs found, {new_count} new, {error_count} errors")
    return {"found": len(jobs), "new": new_count, "errors": error_count}


def configured_ashby_companies() -> list[str]:
    """Read configured Ashby board slugs from haxjobs.toml."""
    companies = DISCOVERY_CONFIG.get("ashby_companies", [])
    if not isinstance(companies, list):
        return []
    return [str(company) for company in companies]


def scrape_ashby_companies(companies: list[str]) -> dict[str, dict[str, int]]:
    """Scrape multiple Ashby board slugs."""
    results: dict[str, dict[str, int]] = {}
    for company in companies:
        clean_company = company.strip()
        if not clean_company:
            continue
        try:
            results[clean_company] = scrape_ashby_company(clean_company)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Scraped {clean_company}: Ashby failed ({exc})", file=sys.stderr)
            results[clean_company] = {"found": 0, "new": 0, "errors": 1}
    return results


def scrape_ashby(companies: list[str] | None = None) -> dict[str, dict[str, int]]:
    """Scrape configured or provided Ashby companies."""
    selected_companies = companies if companies is not None else configured_ashby_companies()
    return scrape_ashby_companies(selected_companies)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Ashby scraper CLI arguments."""
    parser = argparse.ArgumentParser(prog="ashby.py")
    parser.add_argument("--company", action="append", default=[])
    parser.add_argument("--companies", nargs="*", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Ashby scraping."""
    args = parse_args(argv)
    companies = [*args.company, *args.companies]
    if not companies:
        companies = configured_ashby_companies()
    if not companies:
        print("No Ashby companies configured. Use --company or --companies.", file=sys.stderr)
        return 2
    init()
    scrape_ashby_companies(companies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
