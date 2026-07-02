"""Tests for onboarding backend — two-phase wizard with mocked Agent."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ── file extraction ──


def test_extract_plain_text():
    from haxjobs.features.onboarding.service import extract_text_from_upload

    text = extract_text_from_upload(b"Hello world\nI am a CV\n", "cv.txt")
    assert "Hello world" in text


def test_extract_binary_non_pdf_raises():
    from haxjobs.features.onboarding.service import extract_text_from_upload

    with pytest.raises(ValueError, match="Cannot read"):
        extract_text_from_upload(b"\x89PNG\r\n\x1a\n", "photo.png")


def test_extract_pdf():
    from haxjobs.features.onboarding.service import extract_text_from_upload

    pdf = (
        b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 44 >> stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello CV) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n0000000210 00000 n \n"
        b"0000000306 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n387\n%%EOF"
    )
    text = extract_text_from_upload(pdf, "cv.pdf")
    assert "Hello CV" in text


# ── agent mocks ──

CV_EXTRACTION_JSON = json.dumps({
    "user_profile": {
        "name": "Test User",
        "email": "test@example.com",
        "location": "London",
    },
    "skills": ["Python", "FastAPI"],
    "work_experience": [],
    "education": [],
    "projects": [],
    "preferences": {},
})

DEEP_QUESTIONS_JSON = json.dumps([
    {"field": "user_profile.salary_preference", "question": "What salary range?",
     "type": "text", "description": "Salary expectation"},
    {"field": "skills", "question": "Any non-obvious skills?",
     "type": "list", "description": "Hidden skills"},
])


def fake_agent_run(self, prompt, system=None, **kwargs):
    if "Extract structured profile" in (system or ""):
        return CV_EXTRACTION_JSON
    if "career coach" in prompt:
        return DEEP_QUESTIONS_JSON
    return "{}"


# ── profile extraction ──


def test_extract_profile_from_cv(monkeypatch):
    from haxjobs.features.onboarding.service import extract_profile_from_cv
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", fake_agent_run)
    profile = extract_profile_from_cv("Fake CV text")
    assert profile["user_profile"]["name"] == "Test User"
    assert "Python" in profile["skills"]


def test_extract_profile_bad_json_raises(monkeypatch):
    from haxjobs.features.onboarding.service import extract_profile_from_cv
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", lambda s, *a, **kw: "not json at all")
    with pytest.raises(ValueError, match="failed to extract"):
        extract_profile_from_cv("Fake CV")


# ── gap detection ──


def test_required_gaps():
    from haxjobs.features.onboarding.service import _check_required_gaps

    profile = {"user_profile": {"name": "T", "email": "e@e.com"}, "preferences": {}}
    gaps = _check_required_gaps(profile)
    # location, work_auth, roles, locations, work_modes missing
    assert "user_profile.location" in gaps
    assert "user_profile.work_authorization_summary" in gaps
    assert "preferred_roles" in gaps


def test_no_gaps_when_all_filled():
    from haxjobs.features.onboarding.service import _check_required_gaps

    profile = {
        "user_profile": {
            "name": "T", "email": "e@e.com", "location": "London",
            "work_authorization_summary": "Citizen",
        },
        "preferred_roles": ["BE"],
        "preferred_locations": ["London"],
        "preferred_work_modes": ["remote"],
    }
    assert _check_required_gaps(profile) == []


# ── wizard flow ──


def test_get_next_question_returns_required_gap(monkeypatch):
    from haxjobs.features.onboarding.service import (
        start_session, get_next_question, clear_session,
    )
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", fake_agent_run)
    clear_session()
    profile = {
        "user_profile": {"name": "T", "email": "e@e.com"},
        "preferences": {},
    }
    start_session(profile)
    q = get_next_question(profile)
    assert q is not None
    assert q.field in ("user_profile.location", "user_profile.work_authorization_summary",
                       "preferred_roles", "preferred_locations", "preferred_work_modes")


def test_wizard_progresses_to_deep_phase(monkeypatch):
    from haxjobs.features.onboarding.service import (
        start_session, get_next_question, apply_answer, clear_session, get_session,
    )
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", fake_agent_run)
    clear_session()

    # Profile with all required fields filled
    profile = {
        "user_profile": {
            "name": "T", "email": "e@e.com", "location": "London",
            "work_authorization_summary": "Citizen",
        },
        "preferred_roles": ["BE"],
        "preferred_locations": ["London"],
        "preferred_work_modes": ["remote"],
    }
    start_session(profile)
    q = get_next_question(profile)
    # Should now be in deep phase with agent-generated questions
    _, phase, _ = get_session()
    assert phase == "complete" or phase == "deep"
    if q is not None:
        assert q.question != ""  # agent generated


def test_apply_answer_list_type():
    from haxjobs.features.onboarding.service import apply_answer, clear_session

    clear_session()
    profile = {"preferred_roles": []}
    result = apply_answer(profile, "preferred_roles", "Backend, AI Engineer, Full Stack")
    assert result["preferred_roles"] == ["Backend", "AI Engineer", "Full Stack"]


def test_apply_answer_text_type():
    from haxjobs.features.onboarding.service import apply_answer, clear_session

    clear_session()
    profile = {"user_profile": {"name": "Old"}}
    result = apply_answer(profile, "user_profile.phone", "07123456789")
    assert result["user_profile"]["phone"] == "07123456789"


# ── persist ──


def test_save_and_load_profile(tmp_path, monkeypatch):
    from haxjobs.features.onboarding import service as svc

    monkeypatch.setattr(svc, "PROFILE_PATH", tmp_path / "profile.json")
    svc.save_profile({"user_profile": {"name": "Persist Test"}})
    loaded = svc.load_profile()
    assert loaded["user_profile"]["name"] == "Persist Test"


# ── session ──


def test_session_flow():
    from haxjobs.features.onboarding.service import (
        start_session, get_session, clear_session,
    )

    clear_session()
    start_session({"name": "S"})
    profile, phase, _ = get_session()
    assert profile == {"name": "S"}
    assert phase == "required"

    clear_session()
    profile, phase, _ = get_session()
    assert profile is None


# ── routes ──


ISOLATE_SESSION = True  # controlled by fixture


@pytest.fixture(autouse=True)
def _clean_session(monkeypatch, tmp_path):
    from haxjobs.features.onboarding import service as svc
    svc.clear_session()
    monkeypatch.setattr(svc, "PROFILE_PATH", tmp_path / "profile.json")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from haxjobs.app import app
    return TestClient(app)


def test_onboarding_status_not_started(client):
    r = client.get("/api/onboarding/status")
    assert r.status_code == 200
    assert r.json()["stage"] == "not_started"


def test_upload_rejects_no_file(client):
    r = client.post("/api/onboarding/upload")
    assert r.status_code == 422


def test_upload_rejects_huge_file(client):
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", b"x" * (5 * 1024 * 1024 + 1))},
    )
    assert r.status_code == 400


def test_upload_short_text(client):
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", b"hi")},
    )
    assert r.status_code == 400


def test_upload_text_cv(monkeypatch, client):
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", fake_agent_run)
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", b"My name is Test User\nSkills: Python, FastAPI\n" * 10)},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["profile"]["user_profile"]["name"] == "Test User"
    assert data["phase"] == "required"
    assert data["next_question"] is not None


def test_wizard_requires_session(client):
    from haxjobs.features.onboarding.service import clear_session
    clear_session()
    r = client.post("/api/onboarding/wizard", json={
        "question_id": "user_profile.phone",
        "answer": "07123456789",
    })
    assert r.status_code == 400


def test_full_wizard_flow(monkeypatch, client):
    from haxjobs.agent import Agent

    monkeypatch.setattr(Agent, "run", fake_agent_run)

    # upload
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", b"CV content here\n" * 20)},
    )
    assert r.status_code == 200

    # answer a required question
    data = r.json()
    q = data["next_question"]
    r = client.post("/api/onboarding/wizard", json={
        "question_id": q["field"],
        "answer": "my answer",
    })
    assert r.status_code == 200

    # complete
    r = client.post("/api/onboarding/complete")
    assert r.status_code == 200
    assert r.json()["ok"] is True
