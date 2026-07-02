"""Tests for onboarding backend — mocked Agent, real file extraction."""
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


def test_extract_pdf_requires_pdftotext():
    """If pdftotext is available, it should work on a minimal PDF."""
    from haxjobs.features.onboarding.service import extract_text_from_upload

    # minimal hand-crafted PDF with "Hello CV" text
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


# ── profile extraction ──


def fake_agent_run(self, prompt, system=None, **kwargs):
    return json.dumps({
        "user_profile": {
            "name": "Test User",
            "email": "test@example.com",
            "location": "London",
        },
        "skills": ["Python", "FastAPI"],
        "work_experience": [],
        "education": [],
        "projects": [],
    })


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

    monkeypatch.setattr(Agent, "run", lambda *a, **kw: "not json at all")
    with pytest.raises(ValueError, match="failed to extract"):
        extract_profile_from_cv("Fake CV")


# ── wizard ──


def test_wizard_questions():
    from haxjobs.features.onboarding.service import get_next_question

    profile = {"user_profile": {"name": "T"}, "skills": []}
    q = get_next_question(profile, [])
    assert q is not None
    assert "field" in q
    assert "question" in q

    # all questions answered → done
    from haxjobs.features.onboarding.service import _GAP_FIELDS

    q = get_next_question(profile, list(_GAP_FIELDS))
    assert q is None


def test_apply_answer():
    from haxjobs.features.onboarding.service import apply_answer

    profile = {"user_profile": {"name": "Old"}}
    result = apply_answer(profile, "user_profile.phone", "07123456789")
    assert result["user_profile"]["phone"] == "07123456789"
    assert result["user_profile"]["name"] == "Old"  # not overwritten


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

    start_session({"name": "S"})
    profile, answered = get_session()
    assert profile == {"name": "S"}
    assert answered == []

    clear_session()
    profile, answered = get_session()
    assert profile is None


# ── routes ──


@pytest.fixture(autouse=True)
def _clean_session(monkeypatch, tmp_path):
    """Isolate onboarding session + profile path between tests."""
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
    assert r.status_code == 422  # FastAPI validation


def test_upload_rejects_huge_file(client):
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", b"x" * (5 * 1024 * 1024 + 1))},
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

    # answer first question
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
