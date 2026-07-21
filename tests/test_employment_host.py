"""Employment host tests — CareerStore context, tool registration, setup errors.

Plan 003 Phase 6: verify context assembly, person/track selection, job refs, import boundaries.
"""

from __future__ import annotations

import pytest

from haxjobs.employment.host import EmploymentHost, EmploymentSetupError
from haxjobs.employment.schema import (
    CareerTrack,
    EvidenceItem,
    HardConstraint,
    Person,
    Preference,
    Skill,
    SkillEvidence,
)
from haxjobs.employment.store import CareerStore


def _setup_store() -> CareerStore:
    """Create a minimal career graph in memory."""
    store = CareerStore(":memory:")
    now = "2026-07-21T00:00:00+00:00"

    person = Person(
        person_id="test-person",
        name="Test User",
        location="London",
        work_authorization="UK citizen",
        notice_period="1 month",
        salary_range="40000-60000 GBP",
        created_at=now,
        updated_at=now,
    )
    store.upsert_person(person)

    track = CareerTrack(
        track_id="track-backend",
        person_id="test-person",
        name="Backend Python Engineer",
        target_role_families=["Backend Developer", "Python Engineer"],
        created_at=now,
        updated_at=now,
    )
    store.upsert_track(track)

    # Skill
    skill = Skill(
        skill_id="skill-python",
        track_id="track-backend",
        name="Python",
        proficiency="primary",
        created_at=now,
    )
    store.upsert_skill(skill)

    child_skill = Skill(
        skill_id="skill-fastapi",
        track_id="track-backend",
        name="FastAPI",
        parent_skill_id="skill-python",
        proficiency="strong",
        created_at=now,
    )
    store.upsert_skill(child_skill)

    # Evidence
    ev = EvidenceItem(
        evidence_id="ev-cv",
        label="CV Entry",
        source="CV",
        content="Python backend developer since 2020",
        verified_at=now,
        privacy_level="public_ok",
        created_at=now,
    )
    store.upsert_evidence(ev)
    store.link_skill_evidence(SkillEvidence(skill_id="skill-python", evidence_id="ev-cv"))

    # Hard constraint
    hc = HardConstraint(
        constraint_id="hc-1",
        track_id="track-backend",
        constraint_text="Must be remote-friendly",
        created_at=now,
    )
    store.upsert_hard_constraint(hc)

    # Preference
    pref = Preference(
        preference_id="pref-1",
        track_id="track-backend",
        key="preferred_location",
        value="London",
        weight="strong",
        created_at=now,
    )
    store.upsert_preference(pref)

    return store


# ── Correct person and active track ──

def test_host_selects_first_track_by_default():
    """When no track_id is given, the host selects the person's first track."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        assert host.track_id == "track-backend"
    finally:
        store.close()


def test_host_uses_explicit_track_id():
    """When an explicit track_id is given, the host uses it."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person", track_id="track-backend")
        assert host.track_id == "track-backend"
    finally:
        store.close()


# ── Context contains only selected track ──

def test_context_contains_selected_track():
    """The context messages include the selected track's name and skills."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        context = host.context_messages()
        assert len(context) >= 1
        context_text = "\n".join(m.content for m in context)
        assert "Backend Python Engineer" in context_text
        assert "Python" in context_text
        assert "FastAPI" in context_text
    finally:
        store.close()


# ── Hierarchical skills and evidence ──

def test_context_includes_skills_and_evidence():
    """Context shows skills with proficiency and linked evidence."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        context = host.context_messages()
        context_text = "\n".join(m.content for m in context)
        assert "Python" in context_text
        assert "primary" in context_text
        assert "CV Entry" in context_text
        assert "CV" in context_text  # source
    finally:
        store.close()


# ── Hard constraints and preferences ──

def test_context_separates_constraints_and_preferences():
    """Constraints and preferences appear in separate sections."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        context = host.context_messages()
        context_text = "\n".join(m.content for m in context)
        assert "Hard Constraints" in context_text
        assert "Must be remote-friendly" in context_text
        assert "Preferences" in context_text
        assert "London" in context_text
    finally:
        store.close()


# ── Missing profile returns typed setup error ──

def test_missing_person_raises_setup_error():
    """When the person doesn't exist, EmploymentSetupError is raised."""
    store = CareerStore(":memory:")
    try:
        with pytest.raises(EmploymentSetupError, match="No person found"):
            EmploymentHost(store=store, person_id="nonexistent")
    finally:
        store.close()


def test_missing_track_raises_setup_error():
    """When person exists but has no tracks, EmploymentSetupError is raised."""
    store = CareerStore(":memory:")
    now = "2026-07-21T00:00:00+00:00"
    person = Person(
        person_id="p1",
        name="N",
        location="L",
        created_at=now,
        updated_at=now,
    )
    store.upsert_person(person)
    try:
        with pytest.raises(EmploymentSetupError, match="No career tracks"):
            EmploymentHost(store=store, person_id="p1")
    finally:
        store.close()


# ── inspect_job_source is registered as an active tool ──

def test_inspect_job_source_is_active():
    """The host registers inspect_job_source as active."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        assert "inspect_job_source" in host.active_tool_names()
        registry = host.registered_tools()
        schemas = registry.active_schemas(("inspect_job_source",))
        assert len(schemas) == 1
        assert schemas[0].name == "inspect_job_source"
    finally:
        store.close()


# ── System prompt present ──

def test_system_prompt_contains_identity():
    """The system prompt includes Hax identity and truth rules."""
    store = _setup_store()
    try:
        host = EmploymentHost(store=store, person_id="test-person")
        prompt = host.system_prompt()
        assert "Hax" in prompt
        assert "career agent" in prompt.lower()
        assert "never invent" in prompt.lower() or "Never invent" in prompt
    finally:
        store.close()
