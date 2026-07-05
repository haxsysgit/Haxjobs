"""Tests for /api/jobs/{id}/evaluate route."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI TestClient with isolated temp DB."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("HAXJOBS_DB_PATH", str(db_path))
    monkeypatch.setattr("haxjobs.db.schema.DB_PATH", str(db_path))
    from haxjobs.db.schema import init
    init()
    from haxjobs.app import app
    return TestClient(app)


@pytest.fixture
def seed_job(client):
    """Insert a test job."""
    from haxjobs.db.schema import get_db
    conn = get_db()
    conn.execute("""
        INSERT INTO jobs (title, company, location, source_url, source, status, role_family)
        VALUES ('Backend Engineer', 'TestCo', 'London', 'https://test.co/job', 'greenhouse', 'pending', 'backend_python')
    """)
    conn.commit()
    conn.close()


def test_evaluate_success(client, seed_job, monkeypatch):
    """POST /api/jobs/1/evaluate returns result (no real LLM)."""
    from haxjobs import product_tools

    def fake_evaluate(job_id, auto_generate_pack=True):
        return {
            "ok": True,
            "job_id": job_id,
            "fit_score": 85,
            "level": 1,
            "level_name": "Standard",
            "fit_verdict": "STRONG_FIT",
            "strongest_matches": ["Python"],
            "major_gaps": [],
            "sponsorship_risk": "low",
            "summary": "Great fit",
            "pack": None,
        }

    monkeypatch.setattr(product_tools, "evaluate_fit", fake_evaluate)

    resp = client.post("/api/jobs/1/evaluate", json={"auto_generate_pack": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["fit_score"] == 85


def test_evaluate_missing_job_404(client, monkeypatch):
    """Missing job returns 404."""
    resp = client.post("/api/jobs/99999/evaluate", json={"auto_generate_pack": False})
    assert resp.status_code == 404


def test_evaluate_cross_site_rejected(client, seed_job, monkeypatch):
    """Cross-site POST is rejected."""
    resp = client.post(
        "/api/jobs/1/evaluate",
        json={"auto_generate_pack": False},
        headers={"origin": "https://evil.example"},
    )
    assert resp.status_code == 403


def test_evaluate_with_auto_pack(client, seed_job, monkeypatch):
    """POST with auto_generate_pack=True passes the flag."""
    from haxjobs import product_tools
    captured: dict = {}

    def fake_evaluate(job_id, auto_generate_pack=True):
        captured["auto_generate_pack"] = auto_generate_pack
        return {
            "ok": True,
            "job_id": job_id,
            "fit_score": 85,
            "level": 1,
            "level_name": "Standard",
            "fit_verdict": "STRONG_FIT",
            "strongest_matches": [],
            "major_gaps": [],
            "sponsorship_risk": "low",
            "summary": "ok",
            "pack": None,
        }

    monkeypatch.setattr(product_tools, "evaluate_fit", fake_evaluate)
    resp = client.post("/api/jobs/1/evaluate", json={"auto_generate_pack": True})
    assert resp.status_code == 200
    assert captured.get("auto_generate_pack") is True
