"""Migration from CareerFixture flat model to career graph schema."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

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


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def migrate_career_fixture(fixture: CareerFixture, db_path: str | Path) -> CareerStore:
    """Run the full migration from a CareerFixture to the career graph store.

    Returns the open store; caller must close it.
    """
    store = CareerStore(db_path)
    now = datetime.now(timezone.utc).isoformat()

    person_id = "arinze-elensulu"
    track_id = _short_id("track")

    # ── Person ──
    person = Person(
        person_id=person_id,
        name=fixture.career_direction.split("|")[0].strip().rstrip("."),
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
        name="Backend Python Engineer",
        target_role_families=fixture.target_role_families,
        excluded_role_families=fixture.excluded_role_families,
        created_at=now,
        updated_at=now,
    )
    store.upsert_track(track)

    # ── HardConstraints ──
    for i, text in enumerate(fixture.hard_constraints, 1):
        store.upsert_hard_constraint(HardConstraint(
            constraint_id=_short_id("hc"),
            track_id=track_id,
            constraint_text=text,
            created_at=now,
        ))

    # ── Preferences ──
    # preferred_locations
    for loc in fixture.preferred_locations:
        store.upsert_preference(Preference(
            preference_id=_short_id("pref"),
            track_id=track_id,
            key="preferred_location",
            value=loc,
            weight="strong",
            created_at=now,
        ))
    # work_authorization as preference
    store.upsert_preference(Preference(
        preference_id=_short_id("pref"),
        track_id=track_id,
        key="work_authorization",
        value=fixture.work_authorization,
        weight="strong",
        created_at=now,
    ))

    # ── Evidence → Skill extraction ──
    # Build a lookup of lowercase skill name → canonical name
    skill_canonical: dict[str, str] = {}
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

        # Create EvidenceItem
        ev = EvidenceItem(
            evidence_id=_short_id("ev"),
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
                    skill_id=_short_id("skill"),
                    track_id=track_id,
                    name=sk_name,
                    parent_skill_id=None,
                    proficiency=proficiency,  # type: ignore[arg-type]
                    created_at=now,
                )
                skill_map[sk_name] = skill_obj
                skill_canonical[sk_name.lower()] = sk_name
                store.upsert_skill(skill_obj)

            store.link_skill_evidence(SkillEvidence(
                skill_id=skill_map[sk_name].skill_id,
                evidence_id=ev.evidence_id,
            ))

    # ── SkillGaps ──
    for gap_skill, prof in _GAP_SKILLS.items():
        store.upsert_gap(SkillGap(
            gap_id=_short_id("gap"),
            track_id=track_id,
            skill_name=gap_skill,
            target_proficiency=prof,  # type: ignore[arg-type]
            note=f"Gap: {gap_skill} at {prof} proficiency",
            created_at=now,
        ))

    store._conn.commit()
    return store


def migrate_cli_entrypoint(fixture_path: str | None = None) -> CareerStore:
    """Load fixture, run migration, print summary. Returns open store."""
    if fixture_path is None:
        fixture_path = "state/experiments/fixtures/backend-career.json"

    from pathlib import Path
    if not Path(fixture_path).exists():
        print(f"Fixture not found: {fixture_path}")
        print("Create it from your profile or run: haxjobs profile migrate --fixture <path>")
        return

    fixture = load_career_fixture(fixture_path)
    from haxjobs.config import CAREER_DB_PATH
    db_path = str(CAREER_DB_PATH)
    store = migrate_career_fixture(fixture, db_path)

    # Summary
    track_id = store.list_tracks("arinze-elensulu")[0]["track_id"]
    skills = store.list_skills(track_id)
    gaps = store.list_gaps(track_id)
    constraints = store.list_hard_constraints(track_id)
    prefs = store.list_preferences(track_id)

    print(f"Migrated career fixture → {db_path}")
    print(f"  Person: arinze-elensulu")
    print(f"  Track: Backend Python Engineer ({track_id})")
    print(f"  Skills extracted: {len(skills)} — {[s['name'] for s in skills]}")
    print(f"  Gaps: {len(gaps)} — {[g['skill_name'] for g in gaps]}")
    print(f"  Constraints: {len(constraints)}")
    print(f"  Preferences: {len(prefs)}")

    return store
