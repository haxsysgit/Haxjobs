"""Pack detail and safe file read tests.

Slice 7 makes generated packs reviewable from API/dashboard without unsafe path access.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.routes.pack_resources import get_pack_detail, read_pack_text_file


def make_pack(tmp_path: Path) -> Path:
    """Create a realistic generated pack directory."""
    pack_dir = tmp_path / "packs" / "job_7_exampleco_python_backend"
    pack_dir.mkdir(parents=True)
    (pack_dir / "metadata.json").write_text(json.dumps({"job_id": 7, "company": "ExampleCo"}))
    (pack_dir / "cover_letter.md").write_text("Dear ExampleCo team,\n\nThis is the letter.")
    (pack_dir / "fit_report.md").write_text("# Fit Report\n\nStrong match.")
    (pack_dir / "field_answers.md").write_text("# Field Answers\n")
    (pack_dir / "interview_questions.md").write_text("# Interview Questions\n")
    (pack_dir / "telegram_summary.md").write_text("# Telegram Summary\n")
    return pack_dir


def test_get_pack_detail_returns_known_pack_files(tmp_path):
    pack_dir = make_pack(tmp_path)

    detail = get_pack_detail(pack_dir, packs_root=tmp_path / "packs")

    assert detail["ok"] is True
    assert detail["packDir"] == str(pack_dir)
    assert detail["metadata"]["job_id"] == 7
    assert detail["files"]["cover_letter.md"].startswith("Dear ExampleCo")
    assert detail["files"]["fit_report.md"].startswith("# Fit Report")
    assert "metadata.json" not in detail["files"]


def test_get_pack_detail_handles_missing_pack(tmp_path):
    detail = get_pack_detail(tmp_path / "packs" / "missing", packs_root=tmp_path / "packs")

    assert detail["ok"] is False
    assert detail["error"] == "pack not found"


def test_get_pack_detail_does_not_read_unknown_files(tmp_path):
    pack_dir = make_pack(tmp_path)
    (pack_dir / "secret.env").write_text("TOKEN=nope")

    detail = get_pack_detail(pack_dir, packs_root=tmp_path / "packs")

    assert "secret.env" not in detail["files"]
    assert "TOKEN" not in json.dumps(detail)


def test_read_pack_text_file_rejects_path_traversal(tmp_path):
    pack_dir = make_pack(tmp_path)

    result = read_pack_text_file(pack_dir, "../secret.env")

    assert result["ok"] is False
    assert result["error"] == "invalid filename"


def test_read_pack_text_file_reads_allowed_file(tmp_path):
    pack_dir = make_pack(tmp_path)

    result = read_pack_text_file(pack_dir, "cover_letter.md")

    assert result["ok"] is True
    assert "Dear ExampleCo" in result["content"]
