from fastapi.testclient import TestClient

from haxjobs_api.database import Base, create_database_engine, create_session_factory, get_db_session
from haxjobs_api.main import create_app


def make_client(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'dashboard.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    def override_session():
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def test_root_endpoint_describes_the_api_surface(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "haxjobs-api",
        "status": "ok",
        "ui_hint": "Use the HaxJobs frontend on http://localhost:5173 for the main workflow.",
        "docs_path": "/docs",
        "health_path": "/health",
    }


def test_dashboard_bootstrap_endpoints_return_jobs_profiles_and_tasks(tmp_path):
    client = make_client(tmp_path)

    job_response = client.post(
        "/api/jobs/manual",
        json={
            "company": "ExampleCo",
            "title": "Backend Engineer",
            "source_platform": "manual",
            "next_action": "Generate pack",
        },
    )
    assert job_response.status_code == 201

    profile_response = client.post(
        "/api/profiles",
        json={"full_name": "Arinze Elenasulu", "preferred_roles": ["Backend Engineer"]},
    )
    assert profile_response.status_code == 201
    profile_id = profile_response.json()["id"]

    task_response = client.post(
        "/api/hermes-tasks",
        json={
            "task_type": "analyze_job",
            "profile_id": profile_id,
            "input_payload_json": {"source": "dashboard-test"},
        },
    )
    assert task_response.status_code == 201

    jobs = client.get("/api/jobs")
    profiles = client.get("/api/profiles")
    tasks = client.get("/api/hermes-tasks")

    assert jobs.status_code == 200
    assert profiles.status_code == 200
    assert tasks.status_code == 200

    assert jobs.json()[0]["company"] == "ExampleCo"
    assert profiles.json()[0]["full_name"] == "Arinze Elenasulu"
    assert tasks.json()[0]["task_type"] == "analyze_job"
