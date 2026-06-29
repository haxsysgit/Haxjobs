"""Modular scraper adapters for job discovery.

Each scraper module scrapes one source (Greenhouse, Ashby, Lever, etc.),
normalizes output through discovery.normalize.normalize_job(), and feeds
results into db.discovered_jobs.insert_discovered_job().

Scrapers are config-driven: company lists and settings live in haxjobs.toml
under [discovery].
"""
