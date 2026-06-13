import json
from pathlib import Path

from db import schema
from db.evaluations import save_evaluation
from db.jobs import get_job, insert_job
from generate_ready_packs import generate_ready_packs


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"
PROFILE_PATH = ROOT / "profile" / "arinze_profile.local.json"


def use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def add_evaluated_job(title="Python Developer", score=72):
    job_id = insert_job(
        title=title,
        company="ExampleCo",
        location="London, UK",
        jd_text="Build Python FastAPI APIs with PostgreSQL and pytest.",
        source_url="https://example.com/job",
        source="lever",
    )
    save_evaluation(
        job_id,
        {
            "fit_score": score,
            "fit_verdict": "Good fit" if score < 75 else "Strong fit",
            "level": 2 if score < 75 else 1,
            "level_name": "Good fit" if score < 75 else "Strong fit",
            "strongest_matches": ["Python", "FastAPI", "PostgreSQL"],
            "major_gaps": ["Cloud details are light"],
            "summary": "Good backend match.",
            "decision": "completed",
        },
    )
    return job_id


def test_generate_ready_packs_builds_for_evaluated_jobs_and_marks_status(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_evaluated_job(score=72)

    result = generate_ready_packs(
        output_root=tmp_path / "packs",
        registry_path=REGISTRY_PATH,
        profile_path=PROFILE_PATH,
        threshold=50,
    )

    assert result["generated_count"] == 1
    assert result["skipped_count"] == 0
    pack_dir = Path(result["generated"][0]["pack_dir"])
    assert (pack_dir / "metadata.json").exists()

    metadata = json.loads((pack_dir / "metadata.json").read_text())
    assert metadata["job_id"] == job_id
    assert metadata["recommended_cv_variant"] == "backend_python"
    assert metadata["pack_owns_cv"] is False

    job = get_job(job_id)
    assert job["pack_status"] == "generated"


def test_generate_ready_packs_skips_low_scores_and_existing_packs(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    low_job_id = add_evaluated_job(title="Junior Python Developer", score=42)
    ready_job_id = add_evaluated_job(title="Backend Python Developer", score=80)

    first = generate_ready_packs(
        output_root=tmp_path / "packs",
        registry_path=REGISTRY_PATH,
        profile_path=PROFILE_PATH,
        threshold=50,
    )
    second = generate_ready_packs(
        output_root=tmp_path / "packs",
        registry_path=REGISTRY_PATH,
        profile_path=PROFILE_PATH,
        threshold=50,
    )

    assert first["generated_count"] == 1
    assert first["generated"][0]["metadata"]["job_id"] == ready_job_id
    assert get_job(ready_job_id)["pack_status"] == "generated"
    assert get_job(low_job_id)["pack_status"] == "none"

    assert second["generated_count"] == 0
    assert second["skipped_count"] >= 2


def test_generate_ready_packs_uses_dynamic_cover_letter_template(monkeypatch, tmp_path):
    """End-to-end generation should use the role-family cover letter template."""
    use_temp_db(monkeypatch, tmp_path)
    add_evaluated_job(title="Python Backend Engineer", score=82)

    result = generate_ready_packs(
        output_root=tmp_path / "packs",
        registry_path=REGISTRY_PATH,
        profile_path=PROFILE_PATH,
        threshold=50,
    )

    pack_dir = Path(result["generated"][0]["pack_dir"])
    cover_letter = (pack_dir / "cover_letter.md").read_text()
    metadata = json.loads((pack_dir / "metadata.json").read_text())

    assert "prayer circle" in cover_letter
    assert "vibes and hope" in cover_letter
    assert "ExampleCo" in cover_letter
    assert "Python Backend Engineer" in cover_letter
    assert "{role_title}" not in cover_letter
    assert "\u2014" not in cover_letter
    assert metadata["cover_letter_template"] == "application_templates/cover_letters/backend_python.md"


def test_generate_ready_packs_respects_limit(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    add_evaluated_job(title="Python Developer One", score=70)
    add_evaluated_job(title="Python Developer Two", score=75)

    result = generate_ready_packs(
        output_root=tmp_path / "packs",
        registry_path=REGISTRY_PATH,
        profile_path=PROFILE_PATH,
        threshold=50,
        limit=1,
    )

    assert result["generated_count"] == 1
