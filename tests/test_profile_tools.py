"""Tests for profile tools (plan 043 extension)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tmp_profile(tmp_path, monkeypatch):
    """Set up a temporary profile.json for tool tests."""
    import haxjobs.agent.tools as t

    profile_path = tmp_path / "profile.json"
    monkeypatch.setattr(t, "PROFILE_PATH", profile_path)

    # Write a minimal profile
    profile = {
        "schema_version": "1.0.0",
        "updated_at": "2026-07-03T00:00:00Z",
        "personal": {
            "name": "Test User",
            "email": "test@example.com",
            "location": "London",
        },
        "skills": {
            "languages": [{"name": "Python", "proficiency": "advanced"}],
            "frameworks": [],
            "databases": [],
            "devops": [],
            "ai_ml": [],
            "tools": [],
            "soft_skills": [],
        },
        "work_experience": [
            {"company": "Acme Corp", "title": "Engineer", "start_date": "2022-01", "end_date": "2024-06"},
        ],
        "education": [],
        "projects": [],
        "certifications": [],
        "languages": [],
        "work_authorization": {"status": "citizen"},
        "preferences": {"preferred_roles": ["Backend"], "preferred_locations": ["London"], "preferred_work_modes": ["remote"]},
        "cv_tailoring": {},
        "learning": {},
        "confirmed_profile_facts": [],
        "evaluation_context": {},
        "company_notes": {},
        "saved_answers": [],
        "platform_accounts": [],
    }
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    # Also patch onboarding service PROFILE_PATH for tests that go through onboarding
    import haxjobs.features.onboarding.service as svc
    monkeypatch.setattr(svc, "PROFILE_PATH", profile_path)

    # Patch schema path
    schema_real = t.SCHEMA_CACHE_PATH
    monkeypatch.setattr(
        t, "SCHEMA_CACHE_PATH",
        Path(__file__).resolve().parent.parent / "src" / "haxjobs" / "profile" / "profile_schema.json",
    )

    return profile_path


# ── profile_read ──


def test_profile_read_full(tmp_profile):
    from haxjobs.agent.tools import profile_read

    result = profile_read()
    assert "profile" in result
    assert result["profile"]["personal"]["name"] == "Test User"


def test_profile_read_field(tmp_profile):
    from haxjobs.agent.tools import profile_read

    result = profile_read("personal.email")
    assert result == {"personal.email": "test@example.com"}


def test_profile_read_nested(tmp_profile):
    from haxjobs.agent.tools import profile_read

    result = profile_read("skills.languages")
    assert result["skills.languages"] == [{"name": "Python", "proficiency": "advanced"}]


def test_profile_read_missing(tmp_profile):
    from haxjobs.agent.tools import profile_read

    result = profile_read("personal.phone")
    assert result["personal.phone"] is None


def test_profile_read_array_index(tmp_profile):
    from haxjobs.agent.tools import profile_read

    result = profile_read("work_experience.0.company")
    assert result["work_experience.0.company"] == "Acme Corp"


def test_profile_read_no_file(monkeypatch, tmp_path):
    from haxjobs.agent import tools as t

    monkeypatch.setattr(t, "PROFILE_PATH", tmp_path / "nonexistent.json")
    result = t.profile_read()
    assert "error" in result


# ── profile_write ──


def test_profile_write_string(tmp_profile):
    from haxjobs.agent.tools import profile_write, profile_read

    result = profile_write("personal.phone", "+447700900000")
    assert result["ok"] is True
    assert profile_read("personal.phone")["personal.phone"] == "+447700900000"


def test_profile_write_json(tmp_profile):
    from haxjobs.agent.tools import profile_write, profile_read

    val = json.dumps([{"name": "FastAPI", "proficiency": "intermediate"}])
    profile_write("skills.frameworks", val)
    result = profile_read("skills.frameworks")
    assert result["skills.frameworks"] == [{"name": "FastAPI", "proficiency": "intermediate"}]


def test_profile_write_list(tmp_profile):
    from haxjobs.agent.tools import profile_write, profile_read

    profile_write("preferences.preferred_roles", '["AI Engineer", "Backend"]')
    result = profile_read("preferences.preferred_roles")
    assert "AI Engineer" in result["preferences.preferred_roles"]


def test_profile_write_no_file(monkeypatch, tmp_path):
    from haxjobs.agent import tools as t

    monkeypatch.setattr(t, "PROFILE_PATH", tmp_path / "nonexistent.json")
    result = t.profile_write("personal.name", "Someone")
    assert "error" in result


def test_profile_write_persists(tmp_profile):
    from haxjobs.agent.tools import profile_write

    profile_write("personal.location", "Manchester")
    with open(tmp_profile) as f:
        saved = json.load(f)
    assert saved["personal"]["location"] == "Manchester"


# ── profile_schema ──


def test_profile_schema():
    from haxjobs.agent.tools import profile_schema

    result = profile_schema()
    assert "schema" in result
    schema = result["schema"]
    assert "title" in schema
    assert "properties" in schema
    assert "personal" in schema["properties"]


# ── registry integration ──


def test_profile_tools_registered():
    from haxjobs.agent.registry import TOOLS

    assert "profile_read" in TOOLS
    assert "profile_write" in TOOLS
    assert "profile_schema" in TOOLS

    # Verify schemas are valid OpenAI function format
    for name in ("profile_read", "profile_write", "profile_schema"):
        tool = TOOLS[name]
        assert tool.schema["name"] == name
        assert "parameters" in tool.schema
        assert tool.schema["parameters"]["type"] == "object"


def test_profile_tools_dispatch(tmp_profile):
    from haxjobs.agent.registry import dispatch

    result = dispatch("profile_read", {"field_path": "personal.name"})
    parsed = json.loads(result)
    assert parsed["personal.name"] == "Test User"

    dispatch("profile_write", {"field_path": "personal.location", "value": "Bristol"})
    result2 = dispatch("profile_read", {"field_path": "personal.location"})
    assert json.loads(result2)["personal.location"] == "Bristol"
