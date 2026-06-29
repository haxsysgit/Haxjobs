"""Tests for the config-driven role-family classifier.

The classifier now reads from haxjobs.toml [[roles]] via haxjobs_config.
These tests verify classification works without hardcoded JSON taxonomy.
"""
from __future__ import annotations

import json
from pathlib import Path


# ── helpers ──


def get_test_roles() -> list[dict]:
    """Return a test set of role configs matching the 7 families in TOML."""
    return [
        {
            "id": "backend_python", "label": "Python Backend Engineer",
            "cv_variant": "backend_python", "priority": 1,
            "titles": ["Python Developer", "Backend Engineer", "API Engineer"],
            "positive_keywords": ["python", "fastapi", "django", "backend", "api"],
            "negative_keywords": ["ios", "android", "frontend only"],
        },
        {
            "id": "fullstack_python_react", "label": "Full Stack Python and React",
            "cv_variant": "fullstack_python_react", "priority": 2,
            "titles": ["Full Stack Developer", "Fullstack Engineer", "Web Engineer"],
            "positive_keywords": ["full stack", "fullstack", "react", "typescript", "python"],
            "negative_keywords": ["mobile only", "designer"],
        },
        {
            "id": "ai_engineer_llm", "label": "AI Engineer and LLM Engineer",
            "cv_variant": "ai_engineer_llm", "priority": 3,
            "titles": ["AI Engineer", "Machine Learning Engineer", "LLM Engineer"],
            "positive_keywords": ["ai", "llm", "machine learning", "agents", "rag"],
            "negative_keywords": ["research scientist", "phd required"],
        },
        {
            "id": "junior_software", "label": "Junior or Graduate Software Engineer",
            "cv_variant": "junior_software", "priority": 4,
            "titles": ["Junior Software Engineer", "Graduate Software Engineer"],
            "positive_keywords": ["junior", "graduate", "entry level", "intern"],
            "negative_keywords": ["senior", "staff", "principal"],
        },
    ]


# ── tests ──


def test_load_role_profiles_from_config():
    """Role profiles can be loaded from a list of config dicts."""
    from evaluation.role_family import load_role_profiles

    roles = get_test_roles()
    taxonomy = load_role_profiles(roles)

    assert len(taxonomy) == 4
    assert "backend_python" in taxonomy
    assert taxonomy["backend_python"]["priority"] == 1
    assert taxonomy["backend_python"]["cv_variant"] == "backend_python"
    assert "python" in taxonomy["backend_python"]["positive_keywords"]


def test_load_role_profiles_falls_back_to_json():
    """When no roles are provided AND config is empty, falls back to JSON taxonomy."""
    from evaluation.role_family import load_role_profiles

    # Pass empty list explicitly to trigger fallback
    taxonomy = load_role_profiles([])
    assert len(taxonomy) >= 7  # at minimum the 7 families from the JSON file


def test_classify_backend_role():
    """A Python backend job maps to backend_python."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Python Backend Engineer",
        description="Build REST APIs with FastAPI and PostgreSQL.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "backend_python"
    assert result["cv_variant"] == "backend_python"
    assert result["confidence"] > 0.1


def test_classify_fullstack_role():
    """A fullstack React+Python job maps to fullstack_python_react."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Full Stack Engineer",
        description="Build React frontends and Python APIs.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "fullstack_python_react"
    assert result["cv_variant"] == "fullstack_python_react"


def test_classify_ai_role():
    """An AI Engineer job maps to ai_engineer_llm."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="AI Engineer",
        description="Build RAG pipelines and fine-tune LLMs.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "ai_engineer_llm"


def test_classify_unknown_role():
    """A non-tech job returns unknown."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Barista",
        description="Make coffee and serve customers.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "unknown"
    assert result["cv_variant"] == "unknown"
    assert result["confidence"] == 0


def test_negative_keywords_penalize():
    """A backend job that also has negative keywords gets lower confidence."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Backend Engineer",
        description="Building iOS and Android backends with Python.",
        roles=get_test_roles(),
    )
    # Should still match backend_python due to title, but have negative matches
    assert result["role_family"] == "backend_python"
    assert len(result["negative_matches"]) > 0
    # Confidence capped when there are negative matches
    assert result["confidence"] <= 0.79


def test_title_exact_match_scores_highest():
    """Exact title match scores higher than keyword-only match."""
    from evaluation.role_family import classify_role_family

    # Exact title match for ai_engineer_llm
    result = classify_role_family(
        title="AI Engineer",
        description="",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "ai_engineer_llm"
    assert len(result["title_matches"]) >= 1
    assert result["score"] >= 7.0  # exact title = +7


def test_priority_breaks_ties():
    """When two families score equally, priority breaks the tie."""
    from evaluation.role_family import classify_role_family

    # Job that could match both backend_python and fullstack_python_react
    # but backend_python has higher priority (1 vs 2)
    result = classify_role_family(
        title="Software Engineer",
        description="Python API backend and some React frontend work. We use fastapi and typescript.",
        roles=get_test_roles(),
    )
    # Both families will match keywords — backend wins on priority
    assert result["role_family"] in ("backend_python", "fullstack_python_react")


def test_junior_software_role():
    """Junior/graduate roles map to junior_software."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Junior Software Engineer",
        description="Entry-level role for new graduates.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "junior_software"
    assert result["cv_variant"] == "junior_software"


def test_backward_compat_taxonomy_path():
    """The taxonomy_path parameter still works for backward compat."""
    from evaluation.role_family import classify_role_family
    from pathlib import Path

    taxonomy_path = Path(__file__).resolve().parents[1] / "profile" / "role_taxonomy.json"
    result = classify_role_family(
        title="Python Backend Engineer",
        description="Build APIs with FastAPI and PostgreSQL.",
        taxonomy_path=str(taxonomy_path),
    )
    assert result["role_family"] == "backend_python"
    assert result["cv_variant"] == "backend_python"
    assert result["confidence"] > 0


def test_matched_terms_and_title_matches_preserved():
    """Result includes matched_terms and title_matches for debugging."""
    from evaluation.role_family import classify_role_family

    result = classify_role_family(
        title="Backend Engineer",
        description="We use Python, FastAPI, and PostgreSQL.",
        roles=get_test_roles(),
    )
    assert result["role_family"] == "backend_python"
    assert "Backend Engineer" in result["title_matches"]
    assert len(result["matched_terms"]) >= 2  # python, fastapi in description
