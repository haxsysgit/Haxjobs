"""Migration from CareerFixture flat model to career graph schema."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from haxjobs.employment.fixtures import CareerFixture, load_career_fixture
from haxjobs.employment.identifiers import make_stable_id
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

# Skills to detect via keyword matching against evidence content.
_KNOWN_SKILLS = [
    "Python", "Django", "FastAPI", "SQL", "SQLite", "PostgreSQL",
    "React", "TypeScript", "JavaScript", "Docker", "Git", "pytest",
    "MCP", "API design", "LLM pipelines", "agent tooling", "CI/CD",
    "Linux",
]

# Skills considered gaps for this persona.
_GAP_SKILLS = {"React": "working", "TypeScript": "working",
               "Docker": "working", "CI/CD": "working"}

_PROFICIENCY_ORDER = {"learning": 0, "working": 1, "strong": 2, "primary": 3}


def _proficiency_at_least(existing: str, target: str) -> bool:
    """Check whether existing proficiency meets or exceeds target."""
    return _PROFICIENCY_ORDER.get(existing, 0) >= _PROFICIENCY_ORDER.get(target, 0)


def migrate_career_fixture(fixture: CareerFixture, db_path: str | Path) -> CareerStore:
    """Run the full migration from a CareerFixture to the career graph store.

    Returns the open store; caller must close it.
    """
    store = CareerStore(db_path)
    now = datetime.now(timezone.utc).isoformat()

    person_id = fixture.person_id
    track_name = fixture.track_name
    track_id = make_stable_id("track", fixture.person_id, fixture.track_name)

    # ── Person ──
    person = Person(
        person_id=person_id,
        name=fixture.person_name,
        location=fixture.preferred_locations[0] if fixture.preferred_locations else "",
        work_authorization=fixture.work_authorization,
        notice_period="immediate",
        salary_range="35000-45000 GBP",
        created_at=now,
        updated_at=now,
    )
    store.upsert_person(person)

    # ── CareerTrack ──
    track = CareerTrack(
        track_id=track_id,
        person_id=person_id,
        name=track_name,
        target_role_families=fixture.target_role_families,
        excluded_role_families=fixture.excluded_role_families,
        created_at=now,
        updated_at=now,
    )
    store.upsert_track(track)

    # ── HardConstraints ──
    for i, text in enumerate(fixture.hard_constraints, 1):
        constraint_id = make_stable_id("hc", track_id, text)
        store.upsert_hard_constraint(HardConstraint(
            constraint_id=constraint_id,
            track_id=track_id,
            constraint_text=text,
            created_at=now,
        ))

    # ── Preferences ──
    for i, loc in enumerate(fixture.preferred_locations):
        pref_id = make_stable_id("pref", track_id, "preferred_location", loc)
        store.upsert_preference(Preference(
            preference_id=pref_id,
            track_id=track_id,
            key="preferred_location",
            value=loc,
            weight="strong",
            created_at=now,
        ))
    # work_authorization as preference
    store.upsert_preference(Preference(
        preference_id=make_stable_id("pref", track_id, "work_authorization", fixture.work_authorization),
        track_id=track_id,
        key="work_authorization",
        value=fixture.work_authorization,
        weight="strong",
        created_at=now,
    ))

    # ── Evidence → Skill extraction ──
    skill_map: dict[str, Skill] = {}  # canonical name → Skill

    for evidence_item in fixture.evidence:
        content_lower = evidence_item.content.lower()

        # Find matching skills via keyword matching (case-insensitive)
        matched_skills: list[str] = []
        for sk in _KNOWN_SKILLS:
            # Use word-boundary matching to avoid substring hits
            pattern = re.compile(r"\b" + re.escape(sk.lower()) + r"\b")
            if pattern.search(content_lower):
                matched_skills.append(sk)

        # Create EvidenceItem with stable ID
        content_digest = hashlib.sha256(evidence_item.content.encode()).hexdigest()[:12]
        ev = EvidenceItem(
            evidence_id=make_stable_id("ev", evidence_item.label, evidence_item.source, content_digest),
            label=evidence_item.label,
            source=evidence_item.source,
            content=evidence_item.content,
            verified_at=now,
            privacy_level="public_ok",
            created_at=now,
        )
        store.upsert_evidence(ev)

        # Create Skills and links
        for sk_name in matched_skills:
            if sk_name not in skill_map:
                proficiency: str = "strong"
                if sk_name in ("gRPC", "MCP", "agent tooling", "LLM pipelines"):
                    proficiency = "working"
                skill_obj = Skill(
                    skill_id=make_stable_id("skill", track_id, sk_name),
                    track_id=track_id,
                    name=sk_name,
                    parent_skill_id=None,
                    proficiency=proficiency,  # type: ignore[arg-type]
                    created_at=now,
                )
                skill_map[sk_name] = skill_obj
                store.upsert_skill(skill_obj)

            store.link_skill_evidence(SkillEvidence(
                skill_id=skill_map[sk_name].skill_id,
                evidence_id=ev.evidence_id,
            ))

    # ── SkillGaps ──
    existing_skills = {s["name"]: s["proficiency"] for s in store.list_skills(track_id)}
    for gap_skill, prof in _GAP_SKILLS.items():
        if gap_skill in existing_skills and _proficiency_at_least(existing_skills[gap_skill], prof):
            continue  # skip: already met or exceeds target
        store.upsert_gap(SkillGap(
            gap_id=make_stable_id("gap", track_id, gap_skill, prof),
            track_id=track_id,
            skill_name=gap_skill,
            target_proficiency=prof,  # type: ignore[arg-type]
            note=f"Gap: {gap_skill} at {prof} proficiency",
            created_at=now,
        ))

    store._conn.commit()
    return store


def migrate_cli_entrypoint(fixture_path: str | None = None) -> CareerStore | None:
    """Load fixture, run migration, print summary. Returns open store or None."""
    if fixture_path is None:
        fixture_path = "state/experiments/fixtures/backend-career.json"

    from pathlib import Path
    if not Path(fixture_path).exists():
        print(f"Fixture not found: {fixture_path}")
        print("Create it from your profile or run: haxjobs profile migrate --fixture <path>")
        import sys
        sys.exit(1)

    fixture = load_career_fixture(fixture_path)
    from haxjobs.config import CAREER_DB_PATH
    db_path = str(CAREER_DB_PATH)
    store = migrate_career_fixture(fixture, db_path)

    # Summary
    tracks = store.list_tracks(fixture.person_id)
    track_id = tracks[0]["track_id"]
    skills = store.list_skills(track_id)
    gaps = store.list_gaps(track_id)
    constraints = store.list_hard_constraints(track_id)
    prefs = store.list_preferences(track_id)

    print(f"Migrated career fixture → {db_path}")
    print(f"  Person: {fixture.person_id}")
    print(f"  Track: {fixture.track_name} ({track_id})")
    print(f"  Skills extracted: {len(skills)} — {[s['name'] for s in skills]}")
    print(f"  Gaps: {len(gaps)} — {[g['skill_name'] for g in gaps]}")
    print(f"  Constraints: {len(constraints)}")
    print(f"  Preferences: {len(prefs)}")

    return store
