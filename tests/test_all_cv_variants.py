"""Validate every reusable CV variant source and registry status.

Slice 4 TDD: the six non-backend variants should fail these tests until their
cv_source.md files exist and pass governance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"
CV_ROOT = ROOT / "cv_variants"

REQUIRED_SECTION_ORDER = [
    "Professional Summary",
    "Core Skills",
    "Education",
    "Experience",
    "Selected Projects",
    "Additional Information",
]

LOCKED_FACTS = [
    "Arinze Elenasulu",
    "elenasuluarinze@gmail.com",
    "linkedin.com/in/arinze-elenasulu",
    "Middlesex University",
    "BSc Information Technology",
    "Vigilis",
    "Aptech",
    "Pharmax",
    "Python",
    "2020",
]

FORBIDDEN_PHRASES = [
    "Claude Code",
    "Tailored",
    "spearheaded",
    "leveraged",
    "orchestrated",
    "utilized",
    "utilised",
    "cutting-edge",
    "seasoned professional",
    "Hiring Manager",
    "phone",
]

VARIANT_KEY_TERMS = {
    "backend_python": ["FastAPI", "PostgreSQL", "SQLAlchemy", "pytest"],
    "fullstack_python_react": ["React", "TypeScript", "Vite", "FastAPI"],
    "ai_engineer_llm": ["RAGAS", "HuggingFace", "PyTorch", "FRAME", "Haxaml"],
    "ai_automation_agents": ["Archilles", "Haxaml", "HaxJobs", "agent"],
    "junior_software": ["Java", "Flutter", "C++", "learning"],
    "data_python": ["SQL", "reporting", "data", "RAGAS"],
    "platform_backend": ["Docker", "Linux", "logging", "backend services"],
}


def registry() -> dict:
    """Load the CV variant registry."""
    return json.loads(REGISTRY_PATH.read_text())


def variant_ids() -> list[str]:
    """Return all registered CV variant ids."""
    return list(registry()["variants"])


def source_text(variant_id: str) -> str:
    """Read a variant cv_source.md file."""
    source_path = CV_ROOT / variant_id / "cv_source.md"
    assert source_path.exists(), f"Missing CV source for {variant_id}: {source_path}"
    return source_path.read_text()


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_has_cv_source(variant_id):
    source_path = CV_ROOT / variant_id / "cv_source.md"
    assert source_path.exists(), f"Missing cv_source.md for {variant_id}"


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_registry_points_to_generated_source(variant_id):
    variant = registry()["variants"][variant_id]

    assert variant["source_status"] == "generated"
    assert variant["source_md"] == f"cv_variants/{variant_id}/cv_source.md"
    assert (ROOT / variant["source_md"]).exists()


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_uses_required_section_order(variant_id):
    text = source_text(variant_id)
    sections = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)

    assert sections[: len(REQUIRED_SECTION_ORDER)] == REQUIRED_SECTION_ORDER


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_contains_locked_facts(variant_id):
    text = source_text(variant_id)

    for fact in LOCKED_FACTS:
        assert fact in text, f"{variant_id} missing locked fact: {fact}"


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_blocks_forbidden_phrases(variant_id):
    text = source_text(variant_id)

    assert "\u2014" not in text, f"{variant_id} contains em dash"
    text_without_hr = text.replace("---", "")
    assert "--" not in text_without_hr, f"{variant_id} contains double-hyphen dash substitute"
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.lower() not in text.lower(), (
            f"{variant_id} contains forbidden phrase: {phrase}"
        )


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_has_first_person_voice(variant_id):
    text = source_text(variant_id)

    assert re.search(r"\bI (built|designed|created|have|care|work|use|learn|like)", text), (
        f"{variant_id} has no first-person human voice"
    )


@pytest.mark.parametrize("variant_id", variant_ids())
def test_each_variant_has_role_specific_emphasis(variant_id):
    text = source_text(variant_id)
    terms = VARIANT_KEY_TERMS[variant_id]
    missing = [term for term in terms if term.lower() not in text.lower()]

    assert not missing, f"{variant_id} missing emphasis terms: {missing}"


@pytest.mark.parametrize("variant_id", variant_ids())
def test_every_variant_renders_to_html_without_em_dashes(variant_id):
    from cv_variants.renderer import render_html

    html = render_html(CV_ROOT / variant_id / "cv_source.md")

    assert "Arinze Elenasulu" in html
    assert "\u2014" not in html
    assert "#f7f3ea" in html
