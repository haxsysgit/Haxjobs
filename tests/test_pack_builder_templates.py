"""Pack builder template integration tests.

These tests lock Slice 3: per-job packs must use the role-family template
files under application_templates/, not the old hardcoded generic letter.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from packs_builder.job_pack import build_job_pack


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "application_templates"


def sample_job() -> dict:
    """Return a realistic backend job payload for pack rendering."""
    return {
        "id": 777,
        "title": "Python Backend Engineer",
        "company": "Acme Health",
        "location": "London, UK",
        "source": "lever",
        "source_url": "https://jobs.example/acme-python-backend",
        "apply_url": "https://jobs.example/acme-python-backend/apply",
        "role_family": "backend_python",
        "recommended_cv_variant": "backend_python",
        "jd_text": (
            "Build FastAPI services for healthcare operations. Work with "
            "PostgreSQL, pytest, Docker, and product teams."
        ),
    }


def sample_evaluation() -> dict:
    """Return evaluation fields that should drive dynamic slots."""
    return {
        "fit_score": 82,
        "fit_verdict": "Strong fit",
        "level": 1,
        "level_name": "Strong fit",
        "strongest_matches": [
            "Python backend APIs",
            "FastAPI services",
            "PostgreSQL data workflows",
            "pytest discipline",
        ],
        "major_gaps": ["The JD mentions AWS, but the current CV proves Docker/Linux more directly"],
        "summary": "Strong backend fit for operational software.",
    }


def sample_profile() -> dict:
    """Return the profile subset the pack builder needs."""
    return {
        "name": "Arinze Elenasulu",
        "email": "elenasuluarinze@gmail.com",
        "linkedin": "https://www.linkedin.com/in/arinze-elenasulu/",
        "headline": "Python Backend Engineer | AI & Automation",
    }


def sample_cv_variant() -> dict:
    """Return reusable CV reference metadata."""
    return {
        "recommended_cv_variant": "backend_python",
        "role_family": "backend_python",
        "cv_variant_dir": "cv_variants/backend_python",
        "cv_pdf": "cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.pdf",
        "cv_html": "cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.html",
        "pack_owns_cv": False,
    }


def build_sample_pack(tmp_path: Path) -> tuple[Path, str, dict]:
    """Build one sample pack and return its dir, cover letter, metadata."""
    result = build_job_pack(
        job=sample_job(),
        evaluation=sample_evaluation(),
        profile=sample_profile(),
        cv_variant=sample_cv_variant(),
        output_root=tmp_path,
    )
    pack_dir = Path(result["pack_dir"])
    cover_letter = (pack_dir / "cover_letter.md").read_text()
    metadata = json.loads((pack_dir / "metadata.json").read_text())
    return pack_dir, cover_letter, metadata


def test_cover_letter_uses_role_family_template_language(tmp_path):
    """Cover letter must come from the backend_python template.

    The old hardcoded letter starts with "I'm interested in the". The role
    template contains stronger phrases like "prayer circle" and
    "vibes and hope". This test proves the template is actually wired.
    """
    _, cover_letter, _ = build_sample_pack(tmp_path)

    assert "prayer circle" in cover_letter
    assert "vibes and hope" in cover_letter
    assert "I'm interested in the" not in cover_letter


def test_cover_letter_fills_dynamic_slots(tmp_path):
    """All dynamic placeholders must be replaced with job-specific content."""
    _, cover_letter, _ = build_sample_pack(tmp_path)

    assert "{role_title}" not in cover_letter
    assert "{company}" not in cover_letter
    assert "{jd_match_points}" not in cover_letter
    assert "{evidence_story}" not in cover_letter
    assert "{gap_note}" not in cover_letter
    assert "{closing_availability}" not in cover_letter
    assert re.search(r"\{[a-zA-Z0-9_]+\}", cover_letter) is None

    assert "Python Backend Engineer" in cover_letter
    assert "Acme Health" in cover_letter
    assert "lever" in cover_letter
    assert "Python backend APIs" in cover_letter
    assert "Vigilis" in cover_letter
    assert "Pharmax" in cover_letter


def test_cover_letter_keeps_personality_and_truth_guardrails(tmp_path):
    """The generated letter should be confident, specific, and truthful."""
    _, cover_letter, _ = build_sample_pack(tmp_path)

    assert "copy-paste letter" in cover_letter
    assert "absolute monsters" in cover_letter
    assert "I have not had deep production time" in cover_letter
    assert "The JD mentions AWS" in cover_letter
    assert "honestly is The JD" not in cover_letter
    assert "Claude Code" not in cover_letter
    assert "spearheaded" not in cover_letter.lower()
    assert "leveraged" not in cover_letter.lower()
    assert "\u2014" not in cover_letter


def test_pack_metadata_records_template_used(tmp_path):
    """Metadata should make template provenance visible for review/debugging."""
    _, _, metadata = build_sample_pack(tmp_path)

    assert metadata["role_family"] == "backend_python"
    assert metadata["cover_letter_template"] == "application_templates/cover_letters/backend_python.md"
    assert metadata["application_template_id"] == "backend_python"
    assert metadata["pack_owns_cv"] is False


def test_unknown_role_family_falls_back_to_cv_variant_template(tmp_path):
    """If the job lacks role_family, the CV metadata role_family should route it."""
    job = sample_job()
    job.pop("role_family")

    result = build_job_pack(
        job=job,
        evaluation=sample_evaluation(),
        profile=sample_profile(),
        cv_variant=sample_cv_variant(),
        output_root=tmp_path,
    )
    cover_letter = (Path(result["pack_dir"]) / "cover_letter.md").read_text()

    assert "prayer circle" in cover_letter
    assert "Acme Health" in cover_letter
