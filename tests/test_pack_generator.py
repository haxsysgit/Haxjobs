import json
from pathlib import Path

import pytest

from cv_variants.registry import build_pack_cv_metadata, load_cv_variant_registry
from packs_builder.job_pack import build_job_pack


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"


def sample_job():
    return {
        "id": 42,
        "title": "Python Backend Engineer",
        "company": "ExampleCo",
        "location": "London, UK",
        "source_url": "https://example.com/jobs/python-backend",
        "apply_url": "https://example.com/apply/python-backend",
        "role_family": "backend_python",
        "recommended_cv_variant": "backend_python",
        "jd_text": "Build FastAPI services with PostgreSQL and Redis.",
    }


def sample_evaluation():
    return {
        "fit_score": 78,
        "fit_verdict": "Strong fit",
        "level": 1,
        "level_name": "Strong fit",
        "summary": "Strong backend match with Python, FastAPI, PostgreSQL and testing.",
        "strongest_matches": ["Python", "FastAPI", "PostgreSQL", "pytest"],
        "major_gaps": ["Cloud production scale is not explicit in the CV"],
        "sponsorship_risk": "medium",
    }


def sample_profile():
    return {
        "name": "Arinze Elenasulu",
        "email": "elenasuluarinze@gmail.com",
        "linkedin": "https://www.linkedin.com/in/arinze-elenasulu/",
        "headline": "Python Backend Engineer | AI & Automation",
    }


def load_backend_cv_metadata():
    registry = load_cv_variant_registry(REGISTRY_PATH)
    return build_pack_cv_metadata("backend_python", registry)


def test_build_job_pack_creates_expected_markdown_files_and_metadata(tmp_path):
    result = build_job_pack(
        job=sample_job(),
        evaluation=sample_evaluation(),
        profile=sample_profile(),
        cv_variant=load_backend_cv_metadata(),
        output_root=tmp_path,
    )

    pack_dir = Path(result["pack_dir"])
    assert pack_dir.exists()
    assert pack_dir.name == "42_exampleco_python_backend_engineer"

    expected_files = {
        "fit_report.md",
        "cover_letter.md",
        "field_answers.md",
        "interview_questions.md",
        "telegram_summary.md",
        "metadata.json",
    }
    assert {path.name for path in pack_dir.iterdir()} == expected_files
    assert {Path(path).name for path in result["files"]} == expected_files

    metadata = json.loads((pack_dir / "metadata.json").read_text())
    assert metadata["job_id"] == 42
    assert metadata["company"] == "ExampleCo"
    assert metadata["recommended_cv_variant"] == "backend_python"
    assert metadata["pack_owns_cv"] is False
    assert metadata["cv_pdf"] == "cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.pdf"


def test_build_job_pack_references_cv_variant_without_creating_cv_files(tmp_path):
    result = build_job_pack(
        job=sample_job(),
        evaluation=sample_evaluation(),
        profile=sample_profile(),
        cv_variant=load_backend_cv_metadata(),
        output_root=tmp_path,
    )

    pack_dir = Path(result["pack_dir"])
    forbidden_suffixes = {".pdf", ".html"}
    forbidden_name_parts = {"cv", "tailored"}

    for path in pack_dir.iterdir():
        assert path.suffix.lower() not in forbidden_suffixes
        assert not any(part in path.name.lower() for part in forbidden_name_parts)

    metadata = json.loads((pack_dir / "metadata.json").read_text())
    assert metadata["pack_owns_cv"] is False
    assert metadata["cv_pdf"].startswith("cv_variants/")


def test_pack_content_uses_human_voice_and_no_stale_cv_language(tmp_path):
    result = build_job_pack(
        job=sample_job(),
        evaluation=sample_evaluation(),
        profile=sample_profile(),
        cv_variant=load_backend_cv_metadata(),
        output_root=tmp_path,
    )

    pack_dir = Path(result["pack_dir"])
    combined = "\n".join(path.read_text() for path in pack_dir.glob("*.md"))

    assert "Use CV variant: backend_python" in combined
    assert "ExampleCo" in combined
    assert "Python Backend Engineer" in combined
    assert "Tailored CV" not in combined
    assert "generate a CV" not in combined.lower()
    assert "I am writing to express my interest" not in combined
    assert "—" not in combined


def test_build_job_pack_requires_reusable_cv_metadata(tmp_path):
    bad_cv_variant = {"recommended_cv_variant": "backend_python", "pack_owns_cv": True}

    with pytest.raises(ValueError, match="pack_owns_cv must be False"):
        build_job_pack(
            job=sample_job(),
            evaluation=sample_evaluation(),
            profile=sample_profile(),
            cv_variant=bad_cv_variant,
            output_root=tmp_path,
        )
