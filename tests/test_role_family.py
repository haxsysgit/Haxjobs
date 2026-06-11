import json
from pathlib import Path

import pytest

from evaluation.role_family import classify_role_family, load_role_taxonomy


TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "profile" / "role_taxonomy.json"


def test_taxonomy_contains_target_cv_families():
    taxonomy = load_role_taxonomy(TAXONOMY_PATH)
    assert set(taxonomy) == {
        "backend_python",
        "fullstack_python_react",
        "ai_engineer_llm",
        "ai_automation_agents",
        "junior_software",
        "data_python",
        "platform_backend",
    }
    for family, config in taxonomy.items():
        assert config["cv_variant"] == family
        assert config["titles"], family
        assert config["positive_keywords"], family


@pytest.mark.parametrize(
    ("title", "description", "expected_family"),
    [
        ("Python Developer", "FastAPI PostgreSQL SQLAlchemy Redis APIs", "backend_python"),
        ("Backend Software Engineer - Infrastructure", "Python APIs databases and services", "backend_python"),
        ("Full Stack Developer AI, Automation & Tooling", "React TypeScript Python backend", "fullstack_python_react"),
        ("Web Engineer", "React TypeScript frontend with Python APIs", "fullstack_python_react"),
        ("Junior AI Engineer", "LLM RAG evaluation and applied AI products", "ai_engineer_llm"),
        ("Forward Deployed AI Engineer", "LLM workflows and applied AI with customers", "ai_engineer_llm"),
        ("Agentic Platform Engineer", "AI agents workflow orchestration internal tooling", "ai_automation_agents"),
        ("AI Automation Developer", "browser automation Playwright integrations", "ai_automation_agents"),
        ("Graduate Software Engineer", "early career software developer role", "junior_software"),
        ("Software Developer", "junior friendly Python JavaScript role", "junior_software"),
        ("Data Mining Python Developer", "Python SQL Tableau analytics", "data_python"),
        ("Data Engineer", "Python SQL ETL data pipelines", "data_python"),
        ("Platform Engineer", "Docker Kubernetes cloud CI/CD observability", "platform_backend"),
        ("Forward Deployed Infrastructure Engineer", "cloud reliability infrastructure", "platform_backend"),
    ],
)
def test_classifies_target_titles(title, description, expected_family):
    result = classify_role_family(title, description, taxonomy_path=TAXONOMY_PATH)
    assert result["role_family"] == expected_family
    assert result["cv_variant"] == expected_family
    assert result["confidence"] > 0
    assert result["matched_terms"]


def test_senior_manager_role_is_penalized_even_with_matching_keywords():
    result = classify_role_family(
        "Engineering Manager, Agentic Platform",
        "Manage teams building AI agents and platform tooling",
        taxonomy_path=TAXONOMY_PATH,
    )
    assert result["negative_matches"]
    assert result["confidence"] < 0.8


def test_unknown_non_software_role_returns_unknown():
    result = classify_role_family(
        "Government Contracts Specialist",
        "Legal contracts procurement and policy",
        taxonomy_path=TAXONOMY_PATH,
    )
    assert result["role_family"] == "unknown"
    assert result["confidence"] == 0
