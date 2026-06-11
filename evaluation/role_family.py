"""Role-family classification for HaxJobs.

This module maps noisy job titles into the small set of CV families Arinze
wants to maintain. It is intentionally deterministic and lightweight: the LLM
can still reason about fit later, but CV-family selection should be stable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "profile" / "role_taxonomy.json"


_ROLE_TIEBREAK_ORDER = [
    "backend_python",
    "fullstack_python_react",
    "ai_engineer_llm",
    "ai_automation_agents",
    "junior_software",
    "data_python",
    "platform_backend",
]


def load_role_taxonomy(path: str | Path = DEFAULT_TAXONOMY_PATH) -> dict[str, dict[str, Any]]:
    """Load the role taxonomy JSON file."""
    taxonomy_path = Path(path)
    with taxonomy_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def classify_role_family(
    title: str,
    description: str = "",
    *,
    taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
) -> dict[str, Any]:
    """Classify a job into one role family and recommended CV variant.

    Args:
        title: Job title from the source.
        description: Job description or short summary.
        taxonomy_path: Optional path for tests or alternate taxonomies.

    Returns:
        A deterministic classification dict with confidence and evidence.
    """
    taxonomy = load_role_taxonomy(taxonomy_path)
    title_norm = _normalize(title)
    description_norm = _normalize(description)
    combined_norm = f"{title_norm} {description_norm}".strip()

    best_family = "unknown"
    best_score = 0.0
    best_evidence: dict[str, Any] = {
        "matched_terms": [],
        "negative_matches": [],
        "title_matches": [],
    }

    for family, config in taxonomy.items():
        score, evidence = _score_family(family, config, title_norm, description_norm, combined_norm)
        if score > best_score or (score == best_score and _beats_tiebreak(family, best_family)):
            best_family = family
            best_score = score
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
    family: str,
    config: dict[str, Any],
    title_norm: str,
    description_norm: str,
    combined_norm: str,
) -> tuple[float, dict[str, list[str]]]:
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

    # Small product-specific nudges. These prevent broad terms from stealing
    # obvious cases without turning the classifier into a giant rules engine.
    if family == "fullstack_python_react" and _contains_any(title_norm, ["full stack", "fullstack", "web engineer"]):
        score += 8.0
    if family == "ai_engineer_llm" and _contains_any(title_norm, ["ai engineer", "machine learning", "ml engineer", "llm"]):
        score += 3.0
    if family == "ai_automation_agents" and _contains_any(title_norm, ["automation", "agentic", "agent designer", "tooling"]):
        score += 3.0
    if family == "junior_software" and _contains_any(title_norm, ["junior", "graduate", "apprenticeship"]):
        score += 3.0
    if family == "data_python" and _contains_any(title_norm, ["data", "analytics", "tableau"]):
        score += 3.0
    if family == "platform_backend" and _contains_any(title_norm, ["platform", "infrastructure", "reliability", "production engineer"]):
        score += 3.0

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


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(_contains_phrase(text, _normalize(phrase)) for phrase in phrases)


def _beats_tiebreak(candidate: str, current: str) -> bool:
    if current == "unknown":
        return True
    return _ROLE_TIEBREAK_ORDER.index(candidate) < _ROLE_TIEBREAK_ORDER.index(current)


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
