"""Profile-aware search helpers for discovery scrapers."""

from __future__ import annotations

from haxjobs_config import DISCOVERY_CONFIG, JOB_SEARCH_CONFIG, ROLE_PROFILES

DEFAULT_REMOTE_LOCATION_TERMS = [
    "remote",
    "remote uk",
    "uk remote",
    "uk",
    "united kingdom",
    "london",
    "emea",
    "europe",
]


def normalize_term(term: object) -> str:
    """Return a lowercase search term, or an empty string for invalid values."""
    return str(term or "").strip().lower()


def unique_terms(terms: list[str]) -> list[str]:
    """Preserve term order while removing blanks and duplicates."""
    seen_terms: set[str] = set()
    unique: list[str] = []

    for term in terms:
        normalized_term = normalize_term(term)
        if not normalized_term or normalized_term in seen_terms:
            continue
        seen_terms.add(normalized_term)
        unique.append(normalized_term)

    return unique


def configured_profile_search_terms() -> list[str]:
    """Build profile-aware title search terms from config."""
    configured_terms = DISCOVERY_CONFIG.get("profile_search_terms", [])
    if isinstance(configured_terms, list) and configured_terms:
        return unique_terms([str(term) for term in configured_terms])

    role_terms: list[str] = []
    for role_profile in ROLE_PROFILES:
        titles = role_profile.get("titles", [])
        if isinstance(titles, list):
            role_terms.extend(str(title) for title in titles)

    return unique_terms(role_terms)


def configured_excluded_terms() -> list[str]:
    """Read title/company terms that should not be scraped."""
    excluded_terms: list[str] = []

    excluded_levels = JOB_SEARCH_CONFIG.get("excluded_levels", [])
    if isinstance(excluded_levels, list):
        excluded_terms.extend(str(level) for level in excluded_levels)

    blacklisted_keywords = JOB_SEARCH_CONFIG.get("blacklisted_keywords", [])
    if isinstance(blacklisted_keywords, list):
        excluded_terms.extend(str(keyword) for keyword in blacklisted_keywords)

    discovery_excluded = DISCOVERY_CONFIG.get("profile_excluded_terms", [])
    if isinstance(discovery_excluded, list):
        excluded_terms.extend(str(term) for term in discovery_excluded)

    return unique_terms(excluded_terms)


def configured_location_terms() -> list[str]:
    """Read location terms that make a role worth scraping."""
    location_terms: list[str] = []

    preferred_locations = JOB_SEARCH_CONFIG.get("preferred_locations", [])
    if isinstance(preferred_locations, list):
        location_terms.extend(str(location) for location in preferred_locations)

    location_terms.extend(DEFAULT_REMOTE_LOCATION_TERMS)
    return unique_terms(location_terms)


def title_has_profile_match(title: str, search_terms: list[str]) -> bool:
    """Return True when a title matches at least one profile search term."""
    title_text = normalize_term(title)
    return any(search_term in title_text for search_term in search_terms)


def title_is_excluded(title: str, excluded_terms: list[str]) -> bool:
    """Return True when a title clearly points away from Arinze's target roles."""
    title_text = normalize_term(title)
    return any(excluded_term in title_text for excluded_term in excluded_terms)


def location_is_relevant(location: str, location_terms: list[str]) -> bool:
    """Keep unknown locations, but filter clearly irrelevant known locations."""
    location_text = normalize_term(location)
    if not location_text:
        return True
    return any(location_term in location_text for location_term in location_terms)


def job_matches_profile(
    title: str,
    location: str = "",
    search_terms: list[str] | None = None,
    excluded_terms: list[str] | None = None,
    location_terms: list[str] | None = None,
) -> bool:
    """Return True when a scraped job is worth inserting for this profile."""
    active_search_terms = search_terms if search_terms is not None else configured_profile_search_terms()
    active_excluded_terms = excluded_terms if excluded_terms is not None else configured_excluded_terms()
    active_location_terms = location_terms if location_terms is not None else configured_location_terms()

    if not title_has_profile_match(title, active_search_terms):
        return False
    if title_is_excluded(title, active_excluded_terms):
        return False
    return location_is_relevant(location, active_location_terms)


def parse_cli_search_terms(cli_terms: list[str]) -> list[str]:
    """Use CLI query terms when provided, otherwise use profile defaults."""
    if cli_terms:
        return unique_terms(cli_terms)
    return configured_profile_search_terms()
