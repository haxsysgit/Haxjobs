"""Tests for onboarding — deterministic extraction + agent enrichment + wizard."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# ── test CV text ──

SAMPLE_CV = """
Arinze Elenasulu
elenasuluarinze@gmail.com | +44 7823 765497 | London, UK
linkedin.com/in/arinze-elenasulu | github.com/haxsysgit

Python Backend Engineer with experience in FastAPI, PostgreSQL, and AI/ML.

EXPERIENCE
Sole Developer, Vigilis (Aug 2024 - Feb 2026)
- Built digital operations platform processing 200+ invoices/day
- Reduced admin time by 70%, stock discrepancies by 60%
- Python, FastAPI, PostgreSQL, Docker, Linux

EDUCATION
Middlesex University, London — BSc Computer Science (2023-2026)

SKILLS
Python, FastAPI, PostgreSQL, Docker, PyTorch, HuggingFace, React, TypeScript,
Git, pytest, Linux, Redis, Celery, Nginx, SQLAlchemy, Django

PROJECTS
Pharmax — AI-integrated SaaS for pharmacies (github.com/haxsysgit/Pharmax-backend)
Haxaml — Project memory tool for AI coding agents (pypi.org/project/haxaml)
"""

AGENT_EXTRACTION_OUTPUT = json.dumps({
    "schema_version": "1.0.0",
    "personal": {
        "name": "Arinze Elenasulu",
        "email": "elenasuluarinze@gmail.com",
        "phone": "+447823765497",
        "location": "London, UK",
        "preferred_headline": "Python Backend Engineer | AI & Automation",
        "summary": "Python backend engineer with experience in FastAPI, PostgreSQL, and AI/ML.",
    },
    "work_experience": [
        {
            "company": "Vigilis",
            "title": "Sole Developer",
            "start_date": "2024-08",
            "end_date": "2026-02",
            "technologies": ["Python", "FastAPI", "PostgreSQL", "Docker", "Linux"],
        }
    ],
    "education": [
        {"institution": "Middlesex University", "degree": "BSc Computer Science", "location": "London, UK"}
    ],
    "skills": {"languages": [{"name": "Python", "proficiency": "advanced"}]},
    "projects": [{"name": "Pharmax", "description": "AI-integrated SaaS"}],
})

AGENT_QUESTIONS_OUTPUT = json.dumps({"questions": [
    {"field": "work_authorization.status", "question": "What is your current UK work authorization status?",
     "type": "text", "description": "Required for job filtering"},
    {"field": "preferences.preferred_roles", "question": "Which specific roles are you targeting?",
     "type": "list", "description": "Required for job matching"},
]})


# ── mocks ──

def _fake_agent_run(self, prompt, system=None, **kwargs):
    if "CV parser" in (system or ""):
        return AGENT_EXTRACTION_OUTPUT
    if "career coach" in (system or ""):
        return AGENT_QUESTIONS_OUTPUT
    return "{}"


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


# ── deterministic extraction ──


def test_deterministic_extracts_email():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert profile["personal"]["email"] == "elenasuluarinze@gmail.com"


def test_deterministic_extracts_phone():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert profile["personal"]["phone"] is not None
    assert "7823" in profile["personal"]["phone"]


def test_deterministic_extracts_location():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert "London" in (profile["personal"].get("location") or "")


def test_deterministic_extracts_linkedin():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert "arinze-elenasulu" in (profile["personal"].get("linkedin_url") or "")


def test_deterministic_extracts_github():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert "haxsysgit" in (profile["personal"].get("github_url") or "")


def test_deterministic_extracts_name():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    assert "Arinze" in (profile["personal"].get("name") or "")


def test_deterministic_extracts_skills():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic(SAMPLE_CV)
    langs = [s["name"] for s in profile["skills"]["languages"]]
    assert "Python" in langs
    frameworks = [s["name"] for s in profile["skills"]["frameworks"]]
    assert "FastAPI" in frameworks


def test_deterministic_has_full_schema():
    from haxjobs.features.onboarding.service import _extract_deterministic
    profile = _extract_deterministic("Arinze Elenasulu\nLondon\npython@test.com")
    assert profile["schema_version"] == "1.0.0"
    assert "personal" in profile
    assert "work_experience" in profile
    assert "education" in profile
    assert "skills" in profile
    assert "preferences" in profile
    assert "learning" in profile
    assert "work_authorization" in profile


# ── gap detection ──


def test_finds_required_gaps():
    from haxjobs.features.onboarding.service import _find_gaps
    profile = {
        "personal": {"name": "T", "email": "e@e.com", "location": "London"},
        "work_authorization": {"status": ""},
        "preferences": {"preferred_roles": [], "preferred_locations": [], "preferred_work_modes": []},
    }
    gaps = _find_gaps(profile)
    gap_fields = [g[0] for g in gaps]
    assert "work_authorization.status" in gap_fields
    assert "preferences.preferred_roles" in gap_fields


def test_no_gaps_when_filled():
    from haxjobs.features.onboarding.service import _find_gaps
    profile = {
        "personal": {"name": "T", "email": "e@e.com", "location": "L"},
        "work_authorization": {"status": "Citizen"},
        "preferences": {"preferred_roles": ["BE"], "preferred_locations": ["London"], "preferred_work_modes": ["remote"]},
    }
    assert _find_gaps(profile) == []


# ── full pipeline ──


def test_process_cv(monkeypatch):
    from haxjobs.agent import Agent
    monkeypatch.setattr(Agent, "run", _fake_agent_run)
    from haxjobs.features.onboarding.service import process_cv
    profile, questions, phases = process_cv(SAMPLE_CV)
    assert profile["personal"]["email"] == "elenasuluarinze@gmail.com"
    assert len(questions) > 0
    assert questions[0]["field"]
    assert len(phases) == 4


# ── wizard ──


def test_get_next_question(monkeypatch):
    from haxjobs.agent import Agent
    monkeypatch.setattr(Agent, "run", _fake_agent_run)
    from haxjobs.features.onboarding.service import (
        process_cv, start_session, get_next_question, clear_session,
    )
    clear_session()
    profile, questions, phases = process_cv(SAMPLE_CV)
    start_session(profile, questions)
    q = get_next_question(profile)
    assert q is not None
    assert "field" in q


def test_apply_answer():
    from haxjobs.features.onboarding.service import apply_answer, clear_session
    clear_session()
    profile = {"preferences": {"preferred_roles": []}}
    apply_answer(profile, "preferences.preferred_roles", "Backend, AI Engineer")
    assert "Backend" in profile["preferences"]["preferred_roles"]


# ── persist ──


def test_save_and_load(tmp_path, monkeypatch):
    from haxjobs.features.onboarding import service as svc
    monkeypatch.setattr(svc, "PROFILE_PATH", tmp_path / "profile.json")
    svc.save_profile({"personal": {"name": "Test"}})
    # Without onboarding_complete flag, load returns None
    assert svc.load_profile() is None
    # With flag, it returns the profile
    svc.save_profile({"personal": {"name": "Test"}, "onboarding_complete": True})
    loaded = svc.load_profile()
    assert loaded["personal"]["name"] == "Test"


# ── routes ──


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


def test_get_reset_is_not_state_changing(client):
    r = client.get("/api/onboarding/reset")
    assert r.status_code in {404, 405}


def test_onboarding_mutations_reject_cross_site(client):
    headers = {"Origin": "https://evil.example"}
    assert client.post("/api/onboarding/reset", headers=headers).status_code == 403
    assert client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", SAMPLE_CV.encode())},
        headers=headers,
    ).status_code == 403
    assert client.post("/api/onboarding/extract-text", json={"text": SAMPLE_CV}, headers=headers).status_code == 403
    assert client.post("/api/onboarding/wizard", json={"question_id": "x", "answer": "y"}, headers=headers).status_code == 403
    assert client.post("/api/onboarding/complete", headers=headers).status_code == 403


def test_onboarding_mutations_reject_cross_site_fetch_metadata(client):
    r = client.post("/api/onboarding/reset", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


def test_upload_text_cv(monkeypatch, client):
    from haxjobs.agent import Agent
    monkeypatch.setattr(Agent, "run", _fake_agent_run)
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", SAMPLE_CV.encode())},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["profile"]["personal"]["email"] == "elenasuluarinze@gmail.com"
    assert data["next_question"] is not None


def test_full_wizard_flow(monkeypatch, client):
    from haxjobs.agent import Agent
    monkeypatch.setattr(Agent, "run", _fake_agent_run)

    # Upload
    r = client.post(
        "/api/onboarding/upload",
        files={"file": ("cv.txt", SAMPLE_CV.encode())},
    )
    assert r.status_code == 200

    # Answer a question
    data = r.json()
    q = data["next_question"]
    r = client.post("/api/onboarding/wizard", json={
        "question_id": q["field"],
        "answer": "my answer",
    })
    assert r.status_code == 200

    # Complete
    r = client.post("/api/onboarding/complete")
    assert r.status_code == 200
    assert r.json()["ok"] is True
