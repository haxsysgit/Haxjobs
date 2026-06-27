#!/usr/bin/env python3
"""Aggressive company discovery — find UK tech companies with career pages.

For each domain/company name, auto-detects if they use Lever, Ashby, or Greenhouse.
Adds matching companies to the appropriate watchlist.

Also accepts a list of company names to check.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from haxjobs_config import DISCOVERY_DIR
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

# Additional UK tech companies to try (many known to have London offices)
SEED_COMPANIES = [
    # FinTech
    "stripe", "squareup", "adyen", "checkout", "sumup", "klarna",
    "plaid", "truelayer", "soldo", "clearbank", "tide", "starling",
    # SaaS
    "canva", "atlassian", "slack", "dropbox", "asana", "monday",
    "airtable", "miro", "hubspot", "salesforce", "zendesk",
    # E-commerce / Marketplace
    "etsy", "doordash", "deliverect", "zapp",
    # Dev Tools
    "github", "gitlab", "docker", "grafana", "hashicorp", "databricks",
    "mongodb", "elastic", "confluent", "snowflake", "redis",
    # AI/ML
    "anthropic", "cohere", "stability", "huggingface", "deepmind",
    # Gaming
    "epicgames", "riotgames", "unity", "king",
    # Transport / Travel
    "skyscanner", "trainline", "citymapper",
    # Health / Bio
    "babylonhealth", "curai",
    # UK Scale-ups
    "hopin", "depop", "transferwise", "freeagent", "pensionbee",
    "nutmeg", "boughtbymany", "kaleidoscope",
    # Enterprise
    "palantir", "splunk", "servicenow", "twilio",
    # Media / Streaming
    "netflix", "spotify", "disney", "bbc",
    # Consulting / Services
    "thoughtworks", "endava", "cognizant", "infosys",
]


def log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {msg}")


def check_lever(company: str) -> bool:
    """Check if company has a public Lever board."""
    try:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return isinstance(data, list) and len(data) > 0
    except Exception:
        pass
    return False


def check_ashby(company: str) -> bool:
    """Check if company has a public Ashby board."""
    try:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return isinstance(data, dict) and "jobs" in data
    except Exception:
        pass
    return False


def check_greenhouse(company: str) -> bool:
    """Check if company has a public Greenhouse board."""
    try:
        url = f"https://boards.greenhouse.io/{company}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return "jobs-json" in resp.text or "greenhouse" in resp.text.lower()
    except Exception:
        pass
    return False


def read_watchlist(filename: str) -> set:
    """Read existing watchlist companies."""
    path = os.path.join(DISCOVERY_DIR, filename)
    companies = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    companies.add(line)
    return companies


def add_to_watchlist(filename: str, companies: set, new_companies: list):
    """Add new companies to a watchlist file."""
    path = os.path.join(DISCOVERY_DIR, filename)
    existing = read_watchlist(filename)
    added = [c for c in new_companies if c not in existing]
    
    if not added:
        return []
    
    with open(path, "a") as f:
        for c in added:
            f.write(f"{c}\n")
    
    return added


def discover_companies(companies: list[str]) -> dict:
    """Check a list of companies against Lever, Ashby, Greenhouse."""
    results = {"lever": [], "ashby": [], "greenhouse": [], "unknown": []}
    
    for company in companies:
        company = company.strip().lower().replace(" ", "")
        if not company:
            continue
        
        log(f"Checking: {company}")
        
        if check_lever(company):
            log(f"  → Lever ✓")
            results["lever"].append(company)
        elif check_ashby(company):
            log(f"  → Ashby ✓")
            results["ashby"].append(company)
        elif check_greenhouse(company):
            log(f"  → Greenhouse ✓")
            results["greenhouse"].append(company)
        else:
            results["unknown"].append(company)
    
    return results


def main():
    log("Aggressive company discovery starting...")
    
    # Check seed companies
    log(f"Checking {len(SEED_COMPANIES)} seed companies...")
    results = discover_companies(SEED_COMPANIES)
    
    # Add to watchlists
    lever_added = add_to_watchlist("companies.txt", set(), results["lever"])
    ashby_added = add_to_watchlist("ashby_companies.txt", set(), results["ashby"])
    greenhouse_added = add_to_watchlist("greenhouse_companies.txt", set(), results["greenhouse"])
    
    log("")
    log("=== DISCOVERY RESULTS ===")
    log(f"Lever: {len(results['lever'])} found, {len(lever_added)} new added")
    for c in lever_added[:10]:
        log(f"  + {c}")
    log(f"Ashby: {len(results['ashby'])} found, {len(ashby_added)} new added")
    for c in ashby_added[:10]:
        log(f"  + {c}")
    log(f"Greenhouse: {len(results['greenhouse'])} found, {len(greenhouse_added)} new added")
    for c in greenhouse_added[:10]:
        log(f"  + {c}")
    log(f"Unknown (no public ATS): {len(results['unknown'])} companies")
    
    # Save unknown list for potential browser-based checking
    unknown_path = os.path.join(DISCOVERY_DIR, "unknown_companies.txt")
    with open(unknown_path, "w") as f:
        for c in results["unknown"]:
            f.write(f"{c}\n")
    log(f"Unknown companies saved to unknown_companies.txt")
    
    log("\nDiscovery complete.")


if __name__ == "__main__":
    main()
