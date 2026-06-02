from fastapi.testclient import TestClient

from haxjobs_api.database import Base, create_database_engine, create_session_factory, get_db_session
from haxjobs_api.main import create_app


def make_client(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    def override_session():
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def test_manual_job_save_creates_job_application_snapshot_and_status_event(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/jobs/manual",
        json={
            "company": "ExampleCo",
            "title": "Python Backend Engineer",
            "location": "London, UK",
            "source_platform": "manual",
            "source_url": "https://example.com/jobs/backend",
            "job_description": "Build backend APIs with Python and SQLAlchemy.",
            "next_action": "Generate application pack",
            "notes": "Looks relevant for Hermes analysis.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["company"] == "ExampleCo"
    assert payload["application"]["status"] == "Saved"
    assert payload["application"]["next_action"] == "Generate application pack"
    assert payload["snapshot"]["source_platform"] == "manual"
    assert payload["status_event"]["event_type"] == "job_saved"

    list_response = client.get("/api/jobs")
    assert list_response.status_code == 200
    assert list_response.json()[0]["company"] == "ExampleCo"


def test_profile_facts_saved_answers_and_hermes_tasks_can_be_created(tmp_path):
    client = make_client(tmp_path)

    profile_response = client.post(
        "/api/profiles",
        json={
            "full_name": "Arinze Elenasulu",
            "email": "arinze@example.com",
            "preferred_roles": ["Backend Engineer", "AI Engineer"],
        },
    )
    assert profile_response.status_code == 201
    profile_id = profile_response.json()["id"]

    fact_response = client.post(
        f"/api/profiles/{profile_id}/facts",
        json={
            "category": "skill",
            "claim": "Advanced pytest knowledge is confirmed.",
            "confidence": "confirmed",
        },
    )
    assert fact_response.status_code == 201
    assert fact_response.json()["claim"].startswith("Advanced pytest")

    answer_response = client.post(
        f"/api/profiles/{profile_id}/answers",
        json={
            "question_key": "availability",
            "question_text": "When can you start?",
            "answer": "Available immediately.",
            "sensitivity": "review_before_use",
        },
    )
    assert answer_response.status_code == 201
    assert answer_response.json()["question_key"] == "availability"

    task_response = client.post(
        "/api/hermes-tasks",
        json={
            "task_type": "analyze_job",
            "profile_id": profile_id,
            "input_payload_json": {"source": "test"},
        },
    )
    assert task_response.status_code == 201
    assert task_response.json()["status"] == "pending"
