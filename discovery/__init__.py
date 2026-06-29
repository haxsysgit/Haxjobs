"""Discovery ingestion spine — normalization, hooks, and CLI integration.

Every job enters HaxJobs through this package before promotion to the main
``jobs`` table. This keeps dedup, blacklist, and filter logic in one place.
"""
from .normalize import normalize_job
from .hooks import is_blacklisted_company, is_obvious_non_tech, should_accept_discovered_job

__all__ = [
    "normalize_job",
    "is_blacklisted_company",
    "is_obvious_non_tech",
    "should_accept_discovered_job",
]
