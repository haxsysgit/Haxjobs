from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from haxjobs.app import app


def test_pack_creation_rejects_cross_site_post():
    res = TestClient(app).post("/api/jobs/1/pack", headers={"Origin": "https://evil.example"})
    assert res.status_code == 403


def test_pack_creation_allows_missing_browser_headers():
    res = TestClient(app).post("/api/jobs/1/pack")
    assert res.status_code == 200
    # Packs service now returns real data via product_tools, not not_implemented.
    data = res.json()
    assert "ok" in data or "pack_status" in data


def test_auto_pack_slug_cannot_escape_pack_root(tmp_path):
    from haxjobs.evaluate.run import _safe_slug

    pack_root = tmp_path / "packs"
    pack_dir = pack_root / _safe_slug("../Evil/Corp") / _safe_slug("../../backend_python")

    assert pack_dir.resolve().is_relative_to(pack_root.resolve())
    assert ".." not in pack_dir.relative_to(pack_root).as_posix()
