"""Tests for /api/decisions routes."""
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


def test_record_apply(client, seed_job):
    """POST /api/decisions records apply decision."""
    resp = client.post("/api/decisions", json={
        "job_id": 1,
        "decision": "apply",
        "reason": "great fit",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("decision") == "apply"


def test_record_save(client, seed_job):
    """POST /api/decisions records save decision."""
    resp = client.post("/api/decisions", json={
        "job_id": 1,
        "decision": "save",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("decision") == "save"


def test_bad_decision_400(client, seed_job):
    """Unknown decision returns 422 (Pydantic validation) or 400."""
    resp = client.post("/api/decisions", json={
        "job_id": 1,
        "decision": "nope",
    })
    # Pydantic schema rejects it at validation (422) or backend rejects it (400)
    assert resp.status_code in {400, 422}


def test_missing_job_404(client):
    """Decision on non-existent job returns 404."""
    resp = client.post("/api/decisions", json={
        "job_id": 99999,
        "decision": "apply",
    })
    assert resp.status_code == 404


def test_cross_site_rejected(client, seed_job):
    """Cross-site POST is rejected."""
    resp = client.post(
        "/api/decisions",
        json={"job_id": 1, "decision": "apply", "reason": ""},
        headers={"origin": "https://evil.example"},
    )
    assert resp.status_code == 403


def test_list_decisions(client, seed_job):
    """GET /api/decisions returns recent decisions."""
    # Record one first
    client.post("/api/decisions", json={"job_id": 1, "decision": "apply", "reason": ""})
    resp = client.get("/api/decisions")
    assert resp.status_code == 200
    data = resp.json()
    assert "decisions" in data


def test_list_decisions_by_job(client, seed_job):
    """GET /api/decisions?job_id=X filters correctly."""
    client.post("/api/decisions", json={"job_id": 1, "decision": "maybe", "reason": ""})
    resp = client.get("/api/decisions?job_id=1")
    assert resp.status_code == 200
    for d in resp.json()["decisions"]:
        assert d.get("job_id") == 1
