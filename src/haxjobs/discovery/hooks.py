"""Pre- and post-discovery hooks for filtering and accepting jobs.

Every job that enters through the ingestion spine runs through these hooks
before promotion to the main ``jobs`` table.

Config-driven (plan 016-complete)
---------------------------------
Reads ``[job_search]`` from ``haxjobs.toml`` via ``haxjobs_config.JOB_SEARCH_CONFIG``.
The hardcoded defaults below serve as fallbacks when the config section is absent.
"""
from __future__ import annotations

from haxjobs.config import JOB_SEARCH_CONFIG

DEFAULT_BLACKLIST_COMPANIES: set[str] = {
    # Recruitment agencies / body shops
    "robert half", "randstad", "adecco", "kelly services", "manpower",
    "teksystems", "insight global", "experis", "aquent", "creative circle",
    # Staffing / consulting firms of no interest
    "cognizant", "infosys", "wipro", "tcs", "tata consultancy services",
    "hcl", "tech mahindra", "accenture", "capgemini",
    # Low-quality / scam-adjacent
    "revature", "fDM group", "mthree", "smoothstack",
}

OBVIOUSLY_NOT_TECH_KEYWORDS: set[str] = {
    "barista", "cashier", "driver", "delivery", "nurse", "teacher",
    "receptionist", "cleaner", "janitor", "security guard",
    "waiter", "waitress", "cook", "chef", "bartender",
    "hairdresser", "esthetician", "massage therapist",
    "personal trainer", "fitness instructor",
}

# Additional non-tech keywords can be configured in haxjobs.toml
# [job_search].blacklisted_keywords — merged with the defaults below.


def _build_non_tech_keywords() -> set[str]:
    """Merge config blacklisted_keywords with hardcoded defaults."""
    keywords = set(OBVIOUSLY_NOT_TECH_KEYWORDS)
    config_keywords = JOB_SEARCH_CONFIG.get("blacklisted_keywords", [])
    for kw in config_keywords:
        keywords.add((kw or "").strip().lower())
    return {k for k in keywords if k}


def _build_blacklist() -> set[str]:
    """Merge config blacklisted_companies with hardcoded defaults."""
    blacklist = set(DEFAULT_BLACKLIST_COMPANIES)
    config_companies = JOB_SEARCH_CONFIG.get("blacklisted_companies", [])
    for c in config_companies:
        blacklist.add((c or "").strip().lower())
    return {b for b in blacklist if b}


def is_blacklisted_company(company: str) -> bool:
    """Check if a company name appears in the blacklist.

    Reads from ``haxjobs.toml`` ``[job_search].blacklisted_companies``
    merged with the hardcoded default set.

    Returns
    -------
    bool
        True if the company is blacklisted.
    """
    name = (company or "").strip().lower()
    if not name:
        return False

    blacklist = _build_blacklist()
    if name in blacklist:
        return True
    for bl in blacklist:
        if bl and (bl in name or name in bl):
            return True
    return False


def is_obvious_non_tech(title: str, jd_text: str = "") -> bool:
    """Check if a role is obviously non-tech and should be filtered out.

    Uses keyword matching on title and a sample of the description.
    This is intentionally **lenient** — false negatives (passing a non-tech
    role through to classification) are preferred over false positives
    (rejecting a real tech role).

    Parameters
    ----------
    title : str
        Job title.
    jd_text : str, optional
        Full job description text.

    Returns
    -------
    bool
        True if the role is obviously non-tech.
    """
    title_lower = (title or "").strip().lower()
    text_lower = (jd_text or "").lower()[:500]

    # Check title against obvious non-tech keywords (config + defaults)
    for keyword in _build_non_tech_keywords():
        if keyword in title_lower:
            return True

    # For descriptions, only flag if title is also ambiguous AND description
    # is strongly non-tech. This avoids filtering "Engineer" roles that happen
    # to mention "delivery" or "driver" in requirements.
    if "engineer" in title_lower or "developer" in title_lower or "sde" in title_lower:
        return False
    if "tech" in title_lower or "software" in title_lower or "data" in title_lower:
        return False

    # Score description for non-tech signals
    non_tech_signals = ["barista", "cashier", "driving", "delivery route"]
    signal_count = sum(1 for s in non_tech_signals if s in text_lower)

    # Only filter on description evidence if the title is ambiguous
    return signal_count >= 2


def passes_location_filter(location: str) -> bool:
    """Check a job location against configured preferred locations.

    Reads ``[job_search].preferred_locations`` and
    ``[job_search].lenient_filtering`` from ``JOB_SEARCH_CONFIG``.
    If the location doesn't match any preferred location and doesn't
    mention remote/UK, the job is rejected early — before it wastes
    an evaluation call.

    Returns
    -------
    bool
        True if the location passes the filter.
    """
    loc = (location or "").strip().lower()
    if not loc:
        # ponytail: no location provided — let it through, classifier/eval
        # will catch obviously wrong geography.
        return True

    preferred = [
        p.strip().lower()
        for p in JOB_SEARCH_CONFIG.get("preferred_locations", [])
        if p and p.strip()
    ]
    if not preferred:
        return True  # no locations configured, don't filter

    lenient = JOB_SEARCH_CONFIG.get("lenient_filtering", True)

    # Direct match against preferred locations
    for pref in preferred:
        if pref in loc:
            return True

    # Remote/UK patterns — remote only passes if paired with a UK signal
    uk_signals = ("uk", "united kingdom", "gb", "england",
                  "scotland", "wales", "britain", "london",
                  "manchester", "leeds")

    if "remote" in loc:
        # Must be paired with UK or a preferred location
        if any(sig in loc for sig in uk_signals):
            return True
        if lenient:
            for pref in preferred:
                if pref in loc:
                    return True
        # "Remote" alone without UK/preferred → reject
        return False

    if lenient:
        if any(kw in loc for kw in uk_signals):
            return True

    return False


def should_accept_discovered_job(record: dict) -> tuple[bool, str]:
    """Determine whether a discovered job should be accepted.

    Runs blacklist check (from TOML config + hardcoded defaults),
    obvious non-tech check, location preference filter, and any
    configured filters.

    Returns
    -------
    tuple[bool, str]
        ``(accepted, reason)``.
    """
    company = (record.get("company") or "").strip()
    title = (record.get("title") or "").strip()
    jd_text = record.get("jd_text") or ""
    location = (record.get("location") or "").strip()

    if is_blacklisted_company(company):
        return False, "blacklisted"

    if is_obvious_non_tech(title, jd_text):
        return False, "filtered"

    if not passes_location_filter(location):
        return False, f"location not in preferred: {location[:60]}"

    return True, "accepted"
