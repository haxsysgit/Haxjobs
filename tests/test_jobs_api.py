"""Tests for /api/jobs routes."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI TestClient with isolated temp DB."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("HAXJOBS_DB_PATH", str(db_path))
    monkeypatch.setattr("haxjobs.db.schema.DB_PATH", str(db_path))
    # Import at test time so monkeypatch is already applied
    from haxjobs.db.schema import init
    init()

    from haxjobs.app import app
    return TestClient(app)


@pytest.fixture
def seed_job(client):
    """Insert a test job via DB directly."""
    from haxjobs.db.schema import get_db
    conn = get_db()
    conn.execute("""
        INSERT INTO jobs (title, company, location, source_url, source, status, role_family)
        VALUES ('Backend Engineer', 'TestCo', 'London', 'https://test.co/job', 'greenhouse', 'pending', 'backend_python')
    """)
    conn.commit()
    conn.close()


def test_list_jobs_returns_promoted(client, seed_job):
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    jobs = data["jobs"]
    assert any(j["title"] == "Backend Engineer" for j in jobs)


def test_list_jobs_with_status_filter(client, seed_job):
    resp = client.get("/api/jobs?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    for j in data["jobs"]:
        assert j["status"] == "pending"


def test_list_jobs_with_role_family(client, seed_job):
    resp = client.get("/api/jobs?role_family=backend_python")
    assert resp.status_code == 200
    for j in resp.json()["jobs"]:
        assert j.get("role_family") == "backend_python"


def test_list_jobs_unknown_role_family_empty(client, seed_job):
    resp = client.get("/api/jobs?role_family=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["jobs"] == []


def test_get_job_detail(client, seed_job):
    resp = client.get("/api/jobs/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Backend Engineer"
    assert "evaluation" in data
    assert "decisions" in data


def test_get_job_missing_returns_404(client):
    resp = client.get("/api/jobs/99999")
    assert resp.status_code == 404
