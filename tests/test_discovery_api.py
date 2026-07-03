from fastapi.testclient import TestClient

from haxjobs.app import app


def test_discovery_run_endpoint(monkeypatch):
    from haxjobs.features.discovery import routes

    monkeypatch.setattr(routes, "run_discovery", lambda: "run123")

    res = TestClient(app).post("/api/discovery/run")

    assert res.status_code == 200
    assert res.json() == {"run_id": "run123", "running": True}


def test_discovery_status_endpoint(monkeypatch):
    from haxjobs.features.discovery import routes

    monkeypatch.setattr(routes, "get_status", lambda: {
        "running": False,
        "run_id": "run123",
        "found": 3,
        "new": 2,
        "promoted": 1,
        "errors": [],
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
    })

    res = TestClient(app).get("/api/discovery/status")

    assert res.status_code == 200
    assert res.json()["promoted"] == 1


def test_discovery_new_jobs_endpoint(monkeypatch):
    from haxjobs.features.discovery import routes

    monkeypatch.setattr(routes, "get_new_jobs", lambda since="": [{
        "id": 1,
        "title": "Backend Engineer",
        "company": "ExampleCo",
        "location": "London",
        "source_url": "https://example.com/job",
        "discovery_status": "promoted",
        "promoted_job_id": 10,
        "created_at": "2026-01-01 00:00:00",
    }])

    res = TestClient(app).get("/api/discovery/jobs/new")

    assert res.status_code == 200
    assert res.json()[0]["title"] == "Backend Engineer"
