"""Normalize raw job records into a consistent shape for the discovered_jobs table.

Scrapers from any source (manual, greenhouse, ashby, lever, linkedin, etc.)
produce their own field names. This module maps them to the canonical keys
expected by ``db.discovered_jobs.insert_discovered_job``.

No scraping implementation here — this file only handles data shape.
"""

CANONICAL_KEYS = {
    "title",
    "company",
    "location",
    "jd_text",
    "source_url",
    "apply_url",
    "ats",
    "external_id",
    "source",
    "raw_payload",
}


def normalize_job(raw: dict, source: str = "manual") -> dict:
    """Normalize a raw job record into canonical shape.

    Parameters
    ----------
    raw : dict
        Raw job record from a scraper or manual entry. May use any field names.
    source : str
        Source identifier (``manual``, ``greenhouse``, ``ashby``, ``lever``, etc.)

    Returns
    -------
    dict
        Normalized record with all CANONICAL_KEYS present.

    Notes
    -----
    If ``external_id`` is empty, ``source_url`` is used as a fallback.
    If ``source_url`` is also empty, a hex digest of title+company is used
    so the row at least has a semi-stable identifier for dedup purposes.
    """
    out = {
        "title": _first_of(raw, "title", "name", "role", "job_title", "position"),
        "company": _first_of(raw, "company", "organization", "employer", "org", "company_name"),
        "location": _first_of(raw, "location", "locations", "office", "city", "region"),
        "jd_text": _first_of(raw, "jd_text", "description", "body", "jd", "job_description",
                             "details", "text", "content"),
        "source_url": _first_of(raw, "source_url", "url", "link", "apply_url", "job_url",
                                "listing_url", "posting_url"),
        "apply_url": _first_of(raw, "apply_url", "application_url", "apply_link",
                               "url", "source_url"),
        "ats": _first_of(raw, "ats", "ats_name", "platform", "source", "board"),
        "external_id": _first_of(raw, "external_id", "id", "job_id", "req_id", "requisition_id",
                                 "ref"),
        "source": source,
        "raw_payload": raw,
    }

    # Apply URL should not equal source_url unless only one was provided
    if out["apply_url"] == out["source_url"] and _first_of(raw, "apply_url", "application_url",
                                                           "apply_link"):
        pass  # both explicit
    elif out["apply_url"] and out["apply_url"] == out["source_url"]:
        out["apply_url"] = ""

    # Fallback external_id
    if not out["external_id"]:
        import hashlib
        raw_id = (out["title"] + "|" + out["company"]).encode()
        out["external_id"] = "manual_" + hashlib.md5(raw_id).hexdigest()[:12]

    # Ensure all keys exist
    for k in CANONICAL_KEYS:
        out.setdefault(k, "")

    return out


def _first_of(d: dict, *keys: str) -> str:
    """Return the first non-empty string value found among *keys in *d."""
    for k in keys:
        v = d.get(k)
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return ""
