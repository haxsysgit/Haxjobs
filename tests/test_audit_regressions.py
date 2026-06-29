"""Audit regression tests for issues found during the 2026-06-13 readiness audit."""

from __future__ import annotations

from pathlib import Path

from db import schema
from db.decisions import record_decision
from db.jobs import insert_job
from server.routes.jobs import toggle_auto_apply
from server.routes.pack_resources import get_pack_detail


def use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "haxjobs.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def test_auto_apply_toggle_uses_latest_decision(monkeypatch, tmp_path):
    """After removing auto-apply, the next toggle should re-enable it."""
    use_temp_db(monkeypatch, tmp_path)
    job_id = insert_job(
        title="Python Backend Engineer",
        company="ExampleCo",
        jd_text="Python FastAPI role.",
        source="audit",
    )
    record_decision(job_id, "auto_apply", "enable")
    record_decision(job_id, "auto_apply_remove", "disable")

    status, payload = toggle_auto_apply({"job_id": job_id})

    assert status == 200
    assert payload["auto_apply"] is True


def test_pack_detail_rejects_directories_outside_packs_root(tmp_path):
    """Dashboard pack detail must not read arbitrary directories."""
    outside = tmp_path / "not_packs" / "job_1"
    outside.mkdir(parents=True)
    (outside / "cover_letter.md").write_text("Should not be readable")

    detail = get_pack_detail(outside, packs_root=tmp_path / "packs")

    assert detail["ok"] is False
    assert detail["error"] == "pack outside packs root"
