from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def fixture_path(path: str) -> Path:
    primary = Path(path)
    if primary.exists():
        return primary
    return Path("lab") / Path(path).relative_to("tests")


def make_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def make_profile_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv(
        "HAXJOBS_PROFILE_STORE_PATH",
        str(tmp_path / "outputs" / "profile" / "profile.json"),
    )
    return make_client()


def test_health_reports_llm_configured_from_env_state(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "present")
    client = make_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "llm_configured": True}


def test_analyze_endpoint_accepts_pdf_fixture() -> None:
    client = make_client()
    pdf_bytes = fixture_path("tests/cv/Arinze_Agent_engineer_cv.pdf").read_bytes()
    jd_text = fixture_path("tests/jd/60x.txt").read_text(encoding="utf-8")
    response = client.post(
        "/api/analyze",
        files={"cv_file": ("Arinze_Agent_engineer_cv.pdf", pdf_bytes, "application/pdf")},
        data={"jd_text": jd_text, "mode": "stretch"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["metadata"] == {
        "mode": "stretch",
        "source": "upload",
        "cv_label": "Arinze_Agent_engineer_cv.pdf",
        "jd_label": "Pasted Job Description",
    }
    assert payload["fit_summary"]["score"] >= 0
    assert payload["evidence_map"]
    assert payload["analysis_engine"] == "ai"
    assert payload["recruiter_assessment"]["shortlist_summary"]
    assert payload["evaluator_assessment"]["summary"]
    assert payload["verification_questions"]
    assert payload["aspirational_pack"]["non_submittable"] is True
    assert payload["markdown_report"]


def test_analyze_endpoint_accepts_txt_upload(tmp_path) -> None:
    client = make_client()
    cv_path = tmp_path / "sample_cv.txt"
    cv_path.write_text(
        "PROFESSIONAL SUMMARY\nPython engineer with FastAPI, Vue, and testing experience.\n",
        encoding="utf-8",
    )
    response = client.post(
        "/api/analyze",
        files={"cv_file": ("sample_cv.txt", cv_path.read_bytes(), "text/plain")},
        data={"jd_text": "Backend Engineer\nStrong Python and API fundamentals.", "mode": "stretch"},
    )
    assert response.status_code == 200
    assert response.json()["candidate_evidence"]


def test_demo_options_returns_expected_fixture_whitelist() -> None:
    client = make_client()
    response = client.get("/api/demo-options")
    assert response.status_code == 200
    assert response.json() == {
        "cv_fixtures": [
            {"id": "Arinze_Agent_engineer_cv.pdf", "label": "Agent Engineer CV"},
            {"id": "Arinze_Resume_010426.pdf", "label": "General Resume CV"},
            {"id": "Arinze_intern_cv.pdf", "label": "Intern CV"},
        ],
        "jd_fixtures": [
            {"id": "60x.txt", "label": "60x Agent Engineer JD"},
            {"id": "cobaltsky.txt", "label": "Cobalt Sky JD"},
            {"id": "endava.txt", "label": "Endava JD"},
        ],
        "default_cv_fixture": "Arinze_Agent_engineer_cv.pdf",
        "default_jd_fixture": "60x.txt",
        "modes": ["safe", "stretch", "interview", "ideal"],
    }


def test_analyze_demo_endpoint_returns_valid_report() -> None:
    client = make_client()
    response = client.post(
        "/api/analyze-demo",
        json={
            "cv_fixture": "Arinze_Agent_engineer_cv.pdf",
            "jd_fixture": "60x.txt",
            "mode": "safe",
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["metadata"] == {
        "mode": "safe",
        "source": "demo",
        "cv_label": "Agent Engineer CV",
        "jd_label": "60x Agent Engineer JD",
    }
    assert payload["fit_summary"]["score"] >= 0
    assert payload["analysis_engine"] == "ai"
    assert payload["aspirational_pack"]["tailored_cv_markdown"]
    assert payload["warnings"]


def test_generate_application_pack_endpoint_returns_expected_artifacts() -> None:
    client = make_client()
    analysis_payload = client.post(
        "/api/analyze-demo",
        json={
            "cv_fixture": "Arinze_Agent_engineer_cv.pdf",
            "jd_fixture": "60x.txt",
            "mode": "stretch",
        },
    ).json()
    response = client.post(
        "/api/generate-application-pack",
        json={
            "analysis": analysis_payload,
            "follow_up_answers": [
                {
                    "requirement_id": analysis_payload["follow_up_questions"][0]["requirement_id"],
                    "answer": "Built a production FastAPI service and can explain the rollout details.",
                }
            ],
            "user_claim_confirmations": [
                {
                    "requirement_id": analysis_payload["evidence_map"][0]["requirement_id"],
                    "status": "confirmed",
                    "notes": "Confirmed from production project notes.",
                }
            ],
            "user_notes": "Keep the tone direct and defensible.",
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["metadata"]["generated_documents"] == [
        "tailored_cv_markdown",
        "cover_letter_markdown",
        "interview_notes_markdown",
        "application_pack_json",
    ]
    assert payload["tailored_cv_markdown"]
    assert payload["cover_letter_markdown"]
    assert payload["interview_notes_markdown"]
    assert payload["evidence_map_json"]
    assert payload["application_pack_json"]["internal_guardrails"]["evidence_map"]
    assert payload["application_pack_json"]["documents"]["tailored_cv_markdown"]
    assert payload["application_pack_json"]["user_claim_confirmations"][0]["status"] == "confirmed"


def test_profile_endpoint_returns_empty_local_profile(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)

    response = client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["cv_documents"] == []
    assert response.json()["survey_responses"] == []
    assert "Upload CVs to build a reusable local profile." in response.json()["summary"]


def test_profile_upload_persists_cv_text_for_saved_analysis(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)
    cv_bytes = (
        "PROFESSIONAL SUMMARY\n"
        "Python engineer with FastAPI, Vue, and testing experience.\n"
        "SKILLS\nPython\nFastAPI\nVue\n"
    ).encode("utf-8")

    upload_response = client.post(
        "/api/profile/upload-cvs",
        files=[("cv_files", ("main_cv.txt", cv_bytes, "text/plain"))],
    )

    assert upload_response.status_code == 200
    profile = upload_response.json()
    assert profile["cv_documents"][0]["label"] == "main_cv.txt"
    assert "text" not in profile["cv_documents"][0]

    analyze_response = client.post(
        "/api/analyze-saved-cv",
        json={
            "cv_document_id": profile["cv_documents"][0]["id"],
            "jd_text": "Backend Engineer\nStrong Python and API fundamentals.",
            "mode": "stretch",
        },
    )

    assert analyze_response.status_code == 200
    assert analyze_response.json()["metadata"]["cv_label"] == "main_cv.txt"
    assert (tmp_path / "outputs" / "profile" / "documents").exists()


def test_profile_export_includes_sidecar_documents(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)
    cv_bytes = b"PROFESSIONAL SUMMARY\nPython engineer with FastAPI experience.\n"
    client.post(
        "/api/profile/upload-cvs",
        files=[("cv_files", ("main_cv.txt", cv_bytes, "text/plain"))],
    )

    response = client.get("/api/profile/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["cv_documents"][0]["label"] == "main_cv.txt"
    assert payload["documents"][payload["profile"]["cv_documents"][0]["id"]].startswith(
        "PROFESSIONAL SUMMARY"
    )


def test_profile_import_restores_documents_for_saved_analysis(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)
    bundle = {
        "profile": {
            "version": "0.3.0",
            "created_at": "2026-05-18T00:00:00Z",
            "updated_at": "2026-05-18T00:00:00Z",
            "summary": "Imported profile",
            "top_skills": ["Python"],
            "cv_documents": [
                {
                    "id": "cv-main",
                    "label": "Imported CV.txt",
                    "kind": "cv",
                    "added_at": "2026-05-18T00:00:00Z",
                    "summary": "Imported profile CV",
                    "skills": ["Python"],
                }
            ],
            "jd_history": [],
            "evidence_library": [],
            "survey_responses": [],
        },
        "documents": {
            "cv-main": "PROFESSIONAL SUMMARY\nPython backend engineer.\n"
        },
    }

    import_response = client.post("/api/profile/import", json=bundle)

    assert import_response.status_code == 200
    analyze_response = client.post(
        "/api/analyze-saved-cv",
        json={
            "cv_document_id": "cv-main",
            "jd_text": "Backend Engineer\nStrong Python and API fundamentals.",
            "mode": "stretch",
        },
    )

    assert analyze_response.status_code == 200
    assert analyze_response.json()["metadata"]["cv_label"] == "Imported CV.txt"


def test_profile_survey_response_is_saved_locally(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/profile/survey-response",
        json={
            "job_id": "Backend Engineer:Pasted Job Description",
            "requirement_id": "req-2",
            "requirement_text": "Production Vue experience",
            "choice_id": "direct-example",
            "choice_label": "I did this directly",
            "notes": "Built one internal admin panel.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["survey_responses"][0]["choice_id"] == "direct-example"
    assert payload["survey_responses"][0]["notes"] == "Built one internal admin panel."


def test_analyze_saved_cv_returns_404_for_missing_document(tmp_path, monkeypatch) -> None:
    client = make_profile_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/analyze-saved-cv",
        json={
            "cv_document_id": "missing-cv",
            "jd_text": "Backend Engineer\nStrong Python and API fundamentals.",
            "mode": "stretch",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Saved CV was not found in the local profile."
