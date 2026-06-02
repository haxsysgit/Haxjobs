import json

from fastapi.testclient import TestClient

from haxjobs_api.database import Base, create_database_engine, create_session_factory, get_db_session
from haxjobs_api.main import create_app
from haxjobs_api.services.profile_import import import_profile_from_json
from haxjobs_api.services.storage import DocumentStorage, UnsafeDocumentPathError


def make_client(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'storage-api.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    def override_session():
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), session_factory


def test_document_storage_writes_inside_documents_directory_and_rejects_escape(tmp_path):
    storage = DocumentStorage(tmp_path / "data" / "documents")

    stored_path = storage.write_text("packs/example_cv.md", "hello cv")

    assert stored_path.exists()
    assert stored_path.read_text() == "hello cv"
    assert stored_path.is_relative_to(tmp_path / "data" / "documents")

    try:
        storage.write_text("../outside.md", "bad")
    except UnsafeDocumentPathError as exc:
        assert "outside document storage" in str(exc)
    else:
        raise AssertionError("Expected unsafe path to be rejected")


def test_application_pack_document_registration_api_writes_file_and_record(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path)
    monkeypatch.setenv("HAXJOBS_DOCUMENT_STORAGE_DIR", str(tmp_path / "data" / "documents"))

    job_response = client.post(
        "/api/jobs/manual",
        json={"company": "ExampleCo", "title": "Python Backend Engineer", "source_platform": "manual"},
    )
    application_id = job_response.json()["application"]["id"]

    pack_response = client.post(
        "/api/application-packs",
        json={"application_id": application_id, "company": "ExampleCo", "role_title": "Python Backend Engineer"},
    )
    assert pack_response.status_code == 201
    pack_id = pack_response.json()["id"]

    document_response = client.post(
        "/api/documents/register-text",
        json={
            "application_pack_id": pack_id,
            "document_type": "tailored_cv",
            "format": "md",
            "filename": "ExampleCo/cv.md",
            "content": "# CV",
        },
    )

    assert document_response.status_code == 201
    document = document_response.json()
    assert document["document_type"] == "tailored_cv"
    assert document["path"].endswith("ExampleCo/cv.md")
    assert (tmp_path / "data" / "documents" / "ExampleCo" / "cv.md").read_text() == "# CV"


def test_private_profile_json_can_import_profile_facts_and_saved_answers(tmp_path):
    _, session_factory = make_client(tmp_path)
    profile_json = tmp_path / "profile.local.json"
    profile_json.write_text(
        json.dumps(
            {
                "user_profile": {
                    "name": "Arinze Elenasulu",
                    "email": "arinze@example.com",
                    "location": "London, UK",
                    "preferred_roles": ["Backend Engineer"],
                },
                "confirmed_profile_facts": [
                    {
                        "category": "skill",
                        "claim": "Advanced pytest knowledge is confirmed.",
                        "confidence": "confirmed",
                    }
                ],
                "saved_answers": [
                    {
                        "question_key": "availability",
                        "question_text": "When can you start?",
                        "answer": "Available immediately.",
                        "sensitivity": "review_before_use",
                    }
                ],
            }
        )
    )

    with session_factory() as session:
        result = import_profile_from_json(session, profile_json)

    assert result.profile.full_name == "Arinze Elenasulu"
    assert result.facts_imported == 1
    assert result.saved_answers_imported == 1
