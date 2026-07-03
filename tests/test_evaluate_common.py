from __future__ import annotations

import json


def test_build_profile_blurb_supports_onboarding_schema(tmp_path, monkeypatch):
    from haxjobs.evaluate import common

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({
        "personal": {
            "name": "Test User",
            "preferred_headline": "Backend Engineer",
            "email": "test@example.com",
            "location": "London",
            "linkedin_url": "https://linkedin.example/test",
            "github_url": "https://github.com/test",
        },
        "skills": {
            "languages": [{"name": "Python", "proficiency": "advanced"}],
            "frameworks": [{"name": "FastAPI", "proficiency": "intermediate"}],
        },
        "preferences": {
            "preferred_roles": ["Backend Engineer"],
            "preferred_locations": ["Remote UK"],
            "preferred_work_modes": ["remote"],
            "experience_levels": ["junior", "mid"],
            "salary_range": {"min": 35000, "max": 60000, "currency": "GBP"},
        },
        "work_authorization": {
            "status": "Graduate visa",
            "requires_sponsorship_now": False,
            "requires_sponsorship_future": True,
        },
        "work_experience": [{
            "company": "Acme",
            "title": "Engineer",
            "technologies": ["Python", "PostgreSQL"],
            "achievements": ["Cut admin time by 70%"],
        }],
        "projects": [{"name": "Pharmax", "technologies": ["FastAPI"]}],
        "education": [{"institution": "Middlesex", "degree": "BSc Computer Science"}],
        "confirmed_profile_facts": [{
            "category": "project",
            "claim": "Built Pharmax",
            "safe_wording": "Built an AI pharmacy SaaS prototype",
            "avoid_wording": "enterprise production",
        }],
        "evaluation_context": {"behavioral_guardrails": ["Do not overstate seniority"]},
        "company_notes": {"acme": {"pattern": "acme", "note": "User likes Acme"}},
    }))
    monkeypatch.setattr(common, "PROFILE_PATH", profile_path)

    blurb = common.build_profile_blurb("Acme Ltd")

    assert "Name: Test User" in blurb
    assert "Languages: Python (advanced)" in blurb
    assert "Work authorization: Graduate visa" in blurb
    assert "Requires sponsorship now: no" in blurb
    assert "Engineer — Acme" in blurb
    assert "Pharmax" in blurb
    assert "Middlesex" in blurb
    assert "User likes Acme" in blurb
    assert "{\"" not in blurb
    assert '"personal"' not in blurb


def test_build_profile_blurb_supports_legacy_user_profile(tmp_path, monkeypatch):
    from haxjobs.evaluate import common

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({
        "user_profile": {
            "name": "Legacy User",
            "preferred_headline": "AI Engineer",
            "location": "Manchester",
            "email": "legacy@example.com",
            "skills": ["Python", "PyTorch"],
            "preferred_roles": ["AI Engineer"],
            "preferred_locations": ["London"],
            "preferred_work_modes": ["hybrid"],
            "experience_levels": ["graduate"],
            "work_authorization_summary": "Can work in the UK",
            "requires_sponsorship": "future",
            "salary_preference": "£35k-£50k",
            "university": "Middlesex University",
            "university_location": "London",
        }
    }))
    monkeypatch.setattr(common, "PROFILE_PATH", profile_path)

    blurb = common.build_profile_blurb()

    assert "Name: Legacy User" in blurb
    assert "Skills: Python, PyTorch" in blurb
    assert "Preferred roles: AI Engineer" in blurb
    assert "Work authorization: Can work in the UK" in blurb
    assert "University: Middlesex University, London" in blurb
    assert '"user_profile"' not in blurb


def test_build_profile_blurb_missing_profile(tmp_path, monkeypatch):
    from haxjobs.evaluate import common

    monkeypatch.setattr(common, "PROFILE_PATH", tmp_path / "missing.json")
    assert common.build_profile_blurb() == "Profile not found."
