"""Manual pack generation trigger tests.

Slice 6 keeps pack generation gated: explicit CLI/API action only, never cron.
"""

from __future__ import annotations

from pathlib import Path

from db import schema
from db.evaluations import save_evaluation
from db.jobs import get_job, insert_job
from server.routes.jobs import generate_job_pack


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"
PROFILE_PATH = ROOT / "profile" / "arinze_profile.local.json"


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def add_evaluated_job(score: int = 82) -> int:
    """Create a job with evaluation data ready for pack generation."""
    job_id = insert_job(
        title="Python Backend Engineer",
        company="ExampleCo",
        location="London",
        jd_text="Build Python FastAPI APIs with PostgreSQL and pytest.",
        source_url="https://example.com/job",
        source="manual",
    )
    save_evaluation(
        job_id,
        {
            "fit_score": score,
            "fit_verdict": "Strong fit",
            "level": 1,
            "level_name": "Strong fit",
            "strongest_matches": ["Python", "FastAPI", "PostgreSQL"],
            "major_gaps": ["AWS depth is light"],
            "summary": "Strong backend match.",
            "decision": "completed",
        },
    )
    return job_id


def test_generate_job_pack_api_requires_job_id(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)

    status, payload = generate_job_pack({})

    assert status == 400
    assert payload["error"] == "job_id required"


def test_generate_job_pack_api_creates_one_pack_when_requested(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_evaluated_job()
    output_root = tmp_path / "packs"

    status, payload = generate_job_pack(
        {
            "job_id": job_id,
            "output_root": str(output_root),
            "registry_path": str(REGISTRY_PATH),
            "profile_path": str(PROFILE_PATH),
        }
    )

    assert status == 200
    assert payload["ok"] is True
    assert payload["generated_count"] == 1
    assert payload["job_id"] == job_id
    assert get_job(job_id)["pack_status"] == "generated"
    pack_dir = Path(payload["pack_dir"])
    assert (pack_dir / "metadata.json").exists()
    assert (pack_dir / "cover_letter.md").exists()


def test_generate_job_pack_api_is_gated_to_requested_job(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    first_id = add_evaluated_job(score=82)
    second_id = add_evaluated_job(score=83)

    status, payload = generate_job_pack(
        {
            "job_id": first_id,
            "output_root": str(tmp_path / "packs"),
            "registry_path": str(REGISTRY_PATH),
            "profile_path": str(PROFILE_PATH),
        }
    )

    assert status == 200
    assert payload["job_id"] == first_id
    assert get_job(first_id)["pack_status"] == "generated"
    assert get_job(second_id)["pack_status"] == "none"


def test_cron_still_does_not_generate_packs():
    cron = (ROOT / "cron" / "run_pipeline.sh").read_text()

    assert "generate_ready_packs.py" not in cron
    assert "generate-pack" not in cron
