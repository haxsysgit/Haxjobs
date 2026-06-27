"""Manual pack generation trigger tests.

Slice 6 keeps pack generation gated: explicit CLI/API action only, never cron.
"""

from __future__ import annotations

from pathlib import Path

from db import schema
from db.evaluations import save_evaluation
from db.jobs import get_job, insert_job
from generate_ready_packs import generate_pack_for_job
from server.routes.jobs import generate_job_pack


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"
PROFILE_PATH = ROOT / "profile" / "arinze_profile.local.json"


def use_temp_db(monkeypatch, tmp_path):
    """Point the DB layer at a temporary SQLite database."""
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    # Point config at the local repo profile, not /home/hermes
    import haxjobs_config
    monkeypatch.setattr(haxjobs_config, "PROFILE_PATH", PROFILE_PATH)
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
    """HTTP API pack generation uses server-default paths (not client-supplied)."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_evaluated_job()

    status, payload = generate_job_pack({"job_id": job_id})

    assert status == 200
    assert payload["ok"] is True
    assert payload["generated_count"] == 1
    assert payload["job_id"] == job_id
    job = get_job(job_id)
    assert job is not None
    assert job["pack_status"] == "generated"
    pack_dir = Path(payload["pack_dir"])
    assert job["pack_dir"] == str(pack_dir)
    assert (pack_dir / "metadata.json").exists()
    assert (pack_dir / "cover_letter.md").exists()


def test_generate_job_pack_api_is_gated_to_requested_job(monkeypatch, tmp_path):
    """Only the requested job gets a pack — path args are server-side only."""
    use_temp_db(monkeypatch, tmp_path)
    first_id = add_evaluated_job(score=82)
    second_id = add_evaluated_job(score=83)

    status, payload = generate_job_pack({"job_id": first_id})

    assert status == 200
    assert payload["job_id"] == first_id
    assert get_job(first_id)["pack_status"] == "generated"
    assert get_job(second_id)["pack_status"] == "none"


def test_cron_still_does_not_generate_packs():
    cron = (ROOT / "cron" / "run_pipeline.sh").read_text()

    assert "generate_ready_packs.py" not in cron
    assert "generate-pack" not in cron


def test_generate_job_pack_ignores_body_path_overrides(monkeypatch, tmp_path):
    """Body path fields (output_root, registry_path) are server-side only.
    
    Even if a client sends filesystem paths, they are ignored and
    server-side defaults are used instead.
    """
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_evaluated_job()

    # Send request with suspicious paths — they should be ignored
    status, payload = generate_job_pack({
        "job_id": job_id,
        "output_root": "/tmp/evil",
        "registry_path": "/etc/passwd",
        "profile_path": "../../../secrets.env",
    })

    assert status == 200
    assert payload["ok"] is True
    assert "/tmp/evil" not in payload.get("pack_dir", "")


def test_generate_job_pack_ignores_body_threshold_override(monkeypatch, tmp_path):
    """HTTP clients cannot lower the server-side generation threshold."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = add_evaluated_job(score=40)

    status, payload = generate_job_pack({"job_id": job_id, "threshold": 10})

    assert status == 400
    assert payload["ok"] is False
    assert "fit score below 50" in payload["error"]
