"""Career graph schema tests — model validation, store CRUD, migration, CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from haxjobs.employment.fixtures import CareerFixture, load_career_fixture
from haxjobs.employment.schema import (
    CareerTrack,
    EvidenceItem,
    HardConstraint,
    Person,
    Preference,
    Skill,
    SkillEvidence,
    SkillGap,
)
from haxjobs.employment.store import CareerStore
from haxjobs.employment.migration import migrate_career_fixture, migrate_cli_entrypoint


# ── helpers ──

def _valid_career_fixture() -> CareerFixture:
    return load_career_fixture("state/experiments/fixtures/backend-career.json")


def _temp_db() -> str:
    return ":memory:"


# ══════════════════════════════════════════════
# Phase 1: Model validation
# ══════════════════════════════════════════════

def test_person_defaults():
    """Person model fills defaults for optional fields."""
    p = Person(person_id="test-1", name="Test User", location="London")
    assert p.work_authorization == ""
    assert p.notice_period == ""
    assert p.salary_range == ""
    assert p.created_at
    assert p.updated_at


def test_skill_parent_null_or_string():
    """parent_skill_id accepts None or a string."""
    s1 = Skill(skill_id="s1", track_id="t1", name="Python", proficiency="strong")
    assert s1.parent_skill_id is None

    s2 = Skill(skill_id="s2", track_id="t1", name="FastAPI", parent_skill_id="s1", proficiency="working")
    assert s2.parent_skill_id == "s1"

    # Empty string normalized to None
    s3 = Skill(skill_id="s3", track_id="t1", name="Django", parent_skill_id="  ", proficiency="strong")
    assert s3.parent_skill_id is None


def test_evidence_verified_at_iso():
    """EvidenceItem rejects invalid ISO 8601 verified_at."""
    EvidenceItem(evidence_id="e1", label="test", source="src", content="text", verified_at="2026-07-20T12:00:00+00:00")
    EvidenceItem(evidence_id="e2", label="test", source="src", content="text", verified_at=None)
    with pytest.raises(ValueError):
        EvidenceItem(evidence_id="e3", label="test", source="src", content="text", verified_at="not-a-date")


def test_proficiency_literal():
    """Proficiency rejects invalid values."""
    Skill(skill_id="s1", track_id="t1", name="Python", proficiency="primary")
    Skill(skill_id="s2", track_id="t1", name="SQL", proficiency="strong")
    Skill(skill_id="s3", track_id="t1", name="React", proficiency="working")
    Skill(skill_id="s4", track_id="t1", name="Docker", proficiency="learning")
    with pytest.raises(ValueError):
        Skill(skill_id="s5", track_id="t1", name="Bad", proficiency="expert")  # type: ignore[arg-type]


def test_gap_target_proficiency_literal():
    """SkillGap rejects invalid target_proficiency."""
    SkillGap(gap_id="g1", track_id="t1", skill_name="React", target_proficiency="working")
    with pytest.raises(ValueError):
        SkillGap(gap_id="g2", track_id="t1", skill_name="Bad", target_proficiency="unknown")  # type: ignore[arg-type]


def test_constraint_preference_separation():
    """HardConstraint and Preference are separate domain types."""
    hc = HardConstraint(constraint_id="c1", track_id="t1", constraint_text="Must be in London")
    pref = Preference(preference_id="p1", track_id="t1", key="location", value="London", weight="strong")
    assert hc.constraint_text == "Must be in London"
    assert pref.key == "location"
    assert pref.value == "London"
    # They are different types
    assert type(hc) is not type(pref)


# ══════════════════════════════════════════════
# Phase 2: Store
# ══════════════════════════════════════════════

def test_store_table_creation():
    """CareerStore creates all tables on init."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [t["name"] for t in tables]
        assert "persons" in names
        assert "career_tracks" in names
        assert "skills" in names
        assert "evidence_items" in names
        assert "skill_evidence" in names
        assert "skill_gaps" in names
        assert "hard_constraints" in names
        assert "preferences" in names
    finally:
        store.close()


def test_person_crud():
    """Store: upsert and get_person."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        p = Person(person_id="p1", name="Arinze", location="London", salary_range="35k-45k")
        store.upsert_person(p)

        row = store.get_person("p1")
        assert row is not None
        assert row["name"] == "Arinze"
        assert row["location"] == "London"
        assert row["salary_range"] == "35k-45k"

        # Update
        p.name = "Arinze E."
        store.upsert_person(p)
        row2 = store.get_person("p1")
        assert row2["name"] == "Arinze E."
    finally:
        store.close()


def test_track_crud():
    """Store: upsert, get, and list career tracks."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        t = CareerTrack(track_id="t1", person_id="p1", name="Backend")
        store.upsert_track(t)

        row = store.get_track("t1")
        assert row is not None
        assert row["name"] == "Backend"

        tracks = store.list_tracks("p1")
        assert len(tracks) == 1
    finally:
        store.close()


def test_skill_crud():
    """Store: upsert, get, list skills."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))

        s = Skill(skill_id="s1", track_id="t1", name="Python", proficiency="primary")
        store.upsert_skill(s)

        row = store.get_skill("s1")
        assert row is not None
        assert row["name"] == "Python"
        assert row["proficiency"] == "primary"

        skills = store.list_skills("t1")
        assert len(skills) == 1
    finally:
        store.close()


def test_evidence_crud_and_linking():
    """Store: upsert evidence and link to skill."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))
        store.upsert_skill(Skill(skill_id="s1", track_id="t1", name="Python", proficiency="primary"))

        ev = EvidenceItem(evidence_id="e1", label="python-cv", source="cv", content="Python since 2020")
        store.upsert_evidence(ev)

        row = store.get_evidence("e1")
        assert row is not None
        assert row["label"] == "python-cv"

        store.link_skill_evidence(SkillEvidence(skill_id="s1", evidence_id="e1"))

        linked = store.list_evidence_for_skill("s1")
        assert len(linked) == 1
        assert linked[0]["label"] == "python-cv"
    finally:
        store.close()


def test_skill_tree():
    """Store: get_skill_tree returns nested dict."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))

        s1 = Skill(skill_id="s1", track_id="t1", name="Python", proficiency="primary")
        s2 = Skill(skill_id="s2", track_id="t1", name="FastAPI", parent_skill_id="s1", proficiency="strong")
        s3 = Skill(skill_id="s3", track_id="t1", name="Django", parent_skill_id="s1", proficiency="working")
        store.upsert_skill(s1)
        store.upsert_skill(s2)
        store.upsert_skill(s3)

        tree = store.get_skill_tree("t1")
        assert "s1" in tree
        assert len(tree["s1"]["children"]) == 2
        child_names = {c["name"] for c in tree["s1"]["children"]}
        assert child_names == {"FastAPI", "Django"}
    finally:
        store.close()


def test_gap_crud():
    """Store: upsert and list gaps."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))

        g = SkillGap(gap_id="g1", track_id="t1", skill_name="React", target_proficiency="working",
                     note="Need frontend")
        store.upsert_gap(g)

        gaps = store.list_gaps("t1")
        assert len(gaps) == 1
        assert gaps[0]["skill_name"] == "React"
        assert gaps[0]["target_proficiency"] == "working"
        assert gaps[0]["note"] == "Need frontend"
    finally:
        store.close()


def test_hard_constraint_crud():
    """Store: upsert and list hard constraints."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))

        hc = HardConstraint(constraint_id="c1", track_id="t1", constraint_text="Must be remote")
        store.upsert_hard_constraint(hc)

        constraints = store.list_hard_constraints("t1")
        assert len(constraints) == 1
        assert constraints[0]["constraint_text"] == "Must be remote"
    finally:
        store.close()


def test_preference_crud():
    """Store: upsert and list preferences."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        store.upsert_person(Person(person_id="p1", name="N", location="L"))
        store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="T"))

        pref = Preference(preference_id="p1", track_id="t1", key="location", value="London", weight="strong")
        store.upsert_preference(pref)

        prefs = store.list_preferences("t1")
        assert len(prefs) == 1
        assert prefs[0]["key"] == "location"
        assert prefs[0]["value"] == "London"
    finally:
        store.close()


def test_foreign_key_enforcement():
    """Store: FK prevents orphan rows."""
    db_path = _temp_db()
    store = CareerStore(db_path)
    try:
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO career_tracks (track_id, person_id, name, "
                "target_role_families, excluded_role_families, created_at, updated_at) "
                "VALUES ('bad', 'nonexistent', 'N', '[]', '[]', '', '')"
            )
    finally:
        store.close()


# ══════════════════════════════════════════════
# Phase 3: Migration
# ══════════════════════════════════════════════

def test_migration_row_counts():
    """Migration produces expected row counts."""
    fixture = _valid_career_fixture()
    db_path = _temp_db()
    store = migrate_career_fixture(fixture, db_path)
    try:
        assert store.get_person("arinze-elensulu") is not None
        tracks = store.list_tracks("arinze-elensulu")
        assert len(tracks) == 1
        track_id = tracks[0]["track_id"]

        skills = store.list_skills(track_id)
        assert len(skills) > 0, "Migration should extract at least one skill"

        constraints = store.list_hard_constraints(track_id)
        assert len(constraints) == len(fixture.hard_constraints)

        prefs = store.list_preferences(track_id)
        assert len(prefs) >= 2  # locations + work_authorization

        gaps = store.list_gaps(track_id)
        assert len(gaps) == 4  # React, TypeScript, Docker, CI/CD
    finally:
        store.close()


def test_migration_skill_extraction():
    """Migration extracts expected skills from evidence."""
    fixture = _valid_career_fixture()
    db_path = _temp_db()
    store = migrate_career_fixture(fixture, db_path)
    try:
        track_id = store.list_tracks("arinze-elensulu")[0]["track_id"]
        skills = store.list_skills(track_id)
        names = {s["name"] for s in skills}
        # Evidence mentions: Python (python-backend-base, haxjobs),
        # pytest (pharmax), MCP (haxaml), React (haxjobs), TypeScript (haxjobs)
        assert "Python" in names
        assert "pytest" in names
        assert "MCP" in names
        assert "React" in names
        assert "TypeScript" in names
    finally:
        store.close()


def test_migration_gap_creation():
    """Migration creates expected gap records."""
    fixture = _valid_career_fixture()
    db_path = _temp_db()
    store = migrate_career_fixture(fixture, db_path)
    try:
        track_id = store.list_tracks("arinze-elensulu")[0]["track_id"]
        gaps = store.list_gaps(track_id)
        gap_names = {g["skill_name"] for g in gaps}
        assert "React" in gap_names
        assert "TypeScript" in gap_names
        assert "Docker" in gap_names
        assert "CI/CD" in gap_names
    finally:
        store.close()


# ══════════════════════════════════════════════
# Phase 4: CLI
# ══════════════════════════════════════════════

def test_cli_profile_migrate():
    """CLI 'profile migrate' runs and prints summary."""
    result = subprocess.run(
        [sys.executable, "-m", "haxjobs.cli", "profile", "migrate",
         "--fixture", "state/experiments/fixtures/backend-career.json"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        cwd=os.getcwd(),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Migrated career fixture" in result.stdout
    assert "Skills extracted:" in result.stdout
    assert "Gaps:" in result.stdout
    assert "Constraints:" in result.stdout
    assert "Preferences:" in result.stdout


def test_cli_profile_show():
    """CLI 'profile show' runs after migration and shows data."""
    # Migrate first
    subprocess.run(
        [sys.executable, "-m", "haxjobs.cli", "profile", "migrate",
         "--fixture", "state/experiments/fixtures/backend-career.json"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        cwd=os.getcwd(),
    )
    result = subprocess.run(
        [sys.executable, "-m", "haxjobs.cli", "profile", "show"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "src:."},
        cwd=os.getcwd(),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "arinze-elensulu" in result.stdout


# ══════════════════════════════════════════════
# Phase 5: TUI import
# ══════════════════════════════════════════════

def test_tui_import():
    """TUI module imports cleanly."""
    from haxjobs.interfaces.tui import HaxJobsChat, run_tui
    assert HaxJobsChat is not None
    assert run_tui is not None
