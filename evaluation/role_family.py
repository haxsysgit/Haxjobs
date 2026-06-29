"""Role-family classification for HaxJobs.

This module maps noisy job titles into the small set of CV families Arinze
wants to maintain. It is intentionally deterministic and lightweight: the LLM
can still reason about fit later, but CV-family selection should be stable.

Classification reads role profiles from ``haxjobs.toml`` ``[[roles]]`` via
``haxjobs_config.ROLE_PROFILES``.
"""
from __future__ import annotations

import re
from typing import Any



def load_role_profiles(roles: list[dict] | None = None) -> dict[str, dict[str, Any]]:
    """Build a role-family lookup dict from a list of role configs.

    Each role dict must have ``id``, ``cv_variant``, and optional ``priority``,
    ``titles``, ``positive_keywords``, ``negative_keywords``.

    If *roles* is None, reads from ``haxjobs_config.ROLE_PROFILES``.
    """
    if roles is None:
        from haxjobs_config import ROLE_PROFILES as _cfg_roles
        roles = _cfg_roles

    taxonomy: dict[str, dict[str, Any]] = {}
    for role in roles:
        family_id = role.get("id", "")
        if not family_id:
            continue
        taxonomy[family_id] = {
            "label": role.get("label", family_id),
            "cv_variant": role.get("cv_variant", family_id),
            "priority": role.get("priority", 99),
            "titles": role.get("titles", []),
            "positive_keywords": role.get("positive_keywords", []),
            "negative_keywords": role.get("negative_keywords", []),
        }
    return taxonomy


def classify_role_family(
    title: str,
    description: str = "",
    *,
    roles: list[dict] | None = None,
) -> dict[str, Any]:
    """Classify a job into one role family and recommended CV variant.

    Args:
        title: Job title from the source.
        description: Job description or short summary.
        roles: Optional list of role config dicts (from TOML [[roles]]).
               If None, reads from ``haxjobs_config.ROLE_PROFILES``.

    Returns:
        A deterministic classification dict with confidence and evidence.
    """
    taxonomy = load_role_profiles(roles)

    title_norm = _normalize(title)
    description_norm = _normalize(description)
    combined_norm = f"{title_norm} {description_norm}".strip()

    best_family = "unknown"
    best_score = 0.0
    best_priority = 999
    best_evidence: dict[str, Any] = {
        "matched_terms": [],
        "negative_matches": [],
        "title_matches": [],
    }

    for family_id, config in taxonomy.items():
        score, evidence = _score_family(config, title_norm, description_norm, combined_norm)
        family_priority = config.get("priority", 99)

        if score > best_score or (score == best_score and family_priority < best_priority):
            best_family = family_id
            best_score = score
            best_priority = family_priority
            best_evidence = evidence

    if best_score < 2.0:
        return {
            "role_family": "unknown",
            "cv_variant": "unknown",
            "confidence": 0,
            "matched_terms": [],
            "negative_matches": best_evidence.get("negative_matches", []),
            "title_matches": [],
            "score": round(best_score, 2),
        }

    confidence = min(0.99, max(0.1, best_score / 10.0))
    if best_evidence.get("negative_matches"):
        confidence = min(confidence, 0.79)
    return {
        "role_family": best_family,
        "cv_variant": taxonomy[best_family]["cv_variant"],
        "confidence": round(confidence, 2),
        "matched_terms": best_evidence["matched_terms"],
        "negative_matches": best_evidence["negative_matches"],
        "title_matches": best_evidence["title_matches"],
        "score": round(best_score, 2),
    }


def _score_family(
    config: dict[str, Any],
    title_norm: str,
    description_norm: str,
    combined_norm: str,
) -> tuple[float, dict[str, list[str]]]:
    """Score a single role family against the job title and description.

    No hardcoded nudges — all scoring comes from the role config's titles,
    positive_keywords, and negative_keywords.
    """
    score = 0.0
    matched_terms: list[str] = []
    title_matches: list[str] = []
    negative_matches: list[str] = []

    for candidate_title in config.get("titles", []):
        term = _normalize(candidate_title)
        if not term:
            continue
        if term == title_norm:
            score += 7.0
            title_matches.append(candidate_title)
        elif _contains_phrase(title_norm, term):
            score += 5.0
            title_matches.append(candidate_title)

    for keyword in config.get("positive_keywords", []):
        term = _normalize(keyword)
        if not term:
            continue
        if _contains_phrase(title_norm, term):
            score += 2.0
            matched_terms.append(keyword)
        elif _contains_phrase(description_norm, term):
            score += 1.0
            matched_terms.append(keyword)

    for keyword in config.get("negative_keywords", []):
        term = _normalize(keyword)
        if not term:
            continue
        if _contains_phrase(combined_norm, term):
            score -= 2.5
            negative_matches.append(keyword)

    return score, {
        "matched_terms": _unique_preserve_order(matched_terms),
        "negative_matches": _unique_preserve_order(negative_matches),
        "title_matches": _unique_preserve_order(title_matches),
    }


def _normalize(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9+#.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    if not text or not phrase:
        return False
    pattern = r"(?<![a-z0-9+#.])" + re.escape(phrase) + r"(?![a-z0-9+#.])"
    return re.search(pattern, text) is not None


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
