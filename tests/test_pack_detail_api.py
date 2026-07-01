"""Pack detail and safe file read tests.

Slice 7 makes generated packs reviewable from API/dashboard without unsafe path access.
"""

from __future__ import annotations

import json
from pathlib import Path

from haxjobs.server.routes.pack_resources import get_pack_detail, read_pack_text_file
from haxjobs.server.routes.resources import serve_pack_file


def make_pack(tmp_path: Path) -> Path:
    """Create a realistic generated pack directory."""
    pack_dir = tmp_path / "packs" / "job_7_exampleco_python_backend"
    pack_dir.mkdir(parents=True)
    (pack_dir / "metadata.json").write_text(json.dumps({"job_id": 7, "company": "ExampleCo"}))
    (pack_dir / "cover_letter.md").write_text("Dear ExampleCo team,\n\nThis is the letter.")
    (pack_dir / "fit_report.md").write_text("# Fit Report\n\nStrong match.")
    (pack_dir / "field_answers.md").write_text("# Field Answers\n")
    (pack_dir / "interview_questions.md").write_text("# Interview Questions\n")
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


def test_serve_pack_file_returns_file_from_specified_pack_dir(tmp_path, monkeypatch):
    """serve_pack_file must only look inside the requested pack directory."""
    from haxjobs.server.routes import resources as rmod

    packs_root = tmp_path / "packs"
    job_a = packs_root / "job_A_testco"
    job_b = packs_root / "job_B_otherco"
    job_a.mkdir(parents=True)
    job_b.mkdir(parents=True)
    (job_a / "cover_letter.pdf").write_text("letter A")
    (job_b / "fit_report.pdf").write_text("report B")

    monkeypatch.setattr(rmod, "PACKS_DIR", str(packs_root))

    # File exists in job_A — should find it
    result_a = serve_pack_file("job_A_testco", "cover_letter.pdf")
    assert result_a == str(job_a / "cover_letter.pdf")

    # File does NOT exist in job_B — should return None (not fall back to job_A)
    result_b_missing = serve_pack_file("job_B_otherco", "cover_letter.pdf")
    assert result_b_missing is None

    # File exists in job_B — should find it
    result_b = serve_pack_file("job_B_otherco", "fit_report.pdf")
    assert result_b == str(job_b / "fit_report.pdf")


def test_serve_pack_file_rejects_nonexistent_directory(tmp_path, monkeypatch):
    """serve_pack_file returns None when the pack directory doesn't exist."""
    from haxjobs.server.routes import resources as rmod

    packs_root = tmp_path / "packs"
    packs_root.mkdir()
    monkeypatch.setattr(rmod, "PACKS_DIR", str(packs_root))

    result = serve_pack_file("nonexistent_pack", "file.pdf")
    assert result is None
