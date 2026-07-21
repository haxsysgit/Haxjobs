"""Career graph SQLite store — stdlib sqlite3, no ORM, synchronous."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    work_authorization TEXT NOT NULL DEFAULT '',
    notice_period TEXT NOT NULL DEFAULT '',
    salary_range TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS career_tracks (
    track_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_role_families TEXT NOT NULL DEFAULT '[]',
    excluded_role_families TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    parent_skill_id TEXT REFERENCES skills(skill_id) ON DELETE SET NULL,
    proficiency TEXT NOT NULL DEFAULT 'working',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    verified_at TEXT,
    privacy_level TEXT NOT NULL DEFAULT 'public_ok',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_evidence (
    skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id) ON DELETE CASCADE,
    PRIMARY KEY (skill_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS skill_gaps (
    gap_id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    target_proficiency TEXT NOT NULL DEFAULT 'working',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hard_constraints (
    constraint_id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    constraint_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    preference_id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    weight TEXT NOT NULL DEFAULT 'strong',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    external_ref TEXT NOT NULL,
    employer_name TEXT,
    title TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    source_status TEXT NOT NULL DEFAULT '',
    description_kind TEXT NOT NULL DEFAULT '',
    description_complete INTEGER NOT NULL DEFAULT 0,
    observed_at TEXT NOT NULL,
    allowed_source_hosts TEXT NOT NULL DEFAULT '[]',
    warnings TEXT NOT NULL DEFAULT '[]',
    source_content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_assessments (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    tool_call_id TEXT NOT NULL UNIQUE,
    recommendation TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    constraint_checks TEXT NOT NULL DEFAULT '[]',
    strengths TEXT NOT NULL DEFAULT '[]',
    gaps TEXT NOT NULL DEFAULT '[]',
    unknowns TEXT NOT NULL DEFAULT '[]',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    source_content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Return rows as dicts keyed by column name."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CareerStore:
    """SQLite store for the career graph schema."""

    def __init__(self, db_path: str | Path):
        db_path = Path(db_path)
        is_memory = str(db_path) == ":memory:"
        if not is_memory:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = _row_factory
        if not is_memory:
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_DDL)
        self._migrate_job_columns()
        if not is_memory:
            db_path.chmod(0o600)

    def close(self) -> None:
        self._conn.close()

    def _migrate_job_columns(self) -> None:
        """Add Plan 004 job columns to databases created before they existed."""
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(jobs)").fetchall()
        }
        for name in ("source_status", "description_kind"):
            if name not in columns:
                self._conn.execute(
                    f"ALTER TABLE jobs ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"
                )
        self._conn.commit()

    # ── Person ──

    def get_person(self, person_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM persons WHERE person_id = ?", (person_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_people(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM persons ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_person(self, person: Person) -> None:
        person.updated_at = _now()
        d = person.model_dump()
        self._conn.execute(
            """INSERT INTO persons (person_id, name, location, work_authorization,
               notice_period, salary_range, created_at, updated_at)
               VALUES (:person_id, :name, :location, :work_authorization,
               :notice_period, :salary_range, :created_at, :updated_at)
               ON CONFLICT(person_id) DO UPDATE SET
               name=excluded.name, location=excluded.location,
               work_authorization=excluded.work_authorization,
               notice_period=excluded.notice_period,
               salary_range=excluded.salary_range,
               updated_at=excluded.updated_at""",
            d,
        )
        self._conn.commit()

    # ── CareerTrack ──

    def get_track(self, track_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM career_tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_tracks(self, person_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM career_tracks WHERE person_id = ? ORDER BY created_at",
            (person_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_track(self, track: CareerTrack) -> None:
        import json
        track.updated_at = _now()
        d = track.model_dump()
        d["target_role_families"] = json.dumps(track.target_role_families)
        d["excluded_role_families"] = json.dumps(track.excluded_role_families)
        self._conn.execute(
            """INSERT INTO career_tracks (track_id, person_id, name,
               target_role_families, excluded_role_families, created_at, updated_at)
               VALUES (:track_id, :person_id, :name,
               :target_role_families, :excluded_role_families, :created_at, :updated_at)
               ON CONFLICT(track_id) DO UPDATE SET
               name=excluded.name,
               target_role_families=excluded.target_role_families,
               excluded_role_families=excluded.excluded_role_families,
               updated_at=excluded.updated_at""",
            d,
        )
        self._conn.commit()

    # ── Skill ──

    def get_skill(self, skill_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_skills(self, track_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM skills WHERE track_id = ? ORDER BY name", (track_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_skill(self, skill: Skill) -> None:
        d = skill.model_dump()
        self._conn.execute(
            """INSERT INTO skills (skill_id, track_id, name, parent_skill_id,
               proficiency, created_at)
               VALUES (:skill_id, :track_id, :name, :parent_skill_id,
               :proficiency, :created_at)
               ON CONFLICT(skill_id) DO UPDATE SET
               name=excluded.name,
               parent_skill_id=excluded.parent_skill_id,
               proficiency=excluded.proficiency""",
            d,
        )
        self._conn.commit()

    def get_skill_tree(self, track_id: str) -> dict:
        """Return skills nested by parent_skill_id: {skill_id: {**row, children: [...]}}."""
        skills = self.list_skills(track_id)
        by_id: dict[str, dict] = {s["skill_id"]: {**s, "children": []} for s in skills}
        roots: dict[str, dict] = {}
        for sid, node in by_id.items():
            parent = node.get("parent_skill_id")
            if parent and parent in by_id:
                by_id[parent]["children"].append(node)
            else:
                roots[sid] = node
        return roots

    # ── EvidenceItem ──

    def get_evidence(self, evidence_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM evidence_items WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_evidence_for_skill(self, skill_id: str) -> list[dict]:
        rows = self._conn.execute(
            """SELECT e.* FROM evidence_items e
               JOIN skill_evidence se ON e.evidence_id = se.evidence_id
               WHERE se.skill_id = ? ORDER BY e.created_at""",
            (skill_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_evidence(self, evidence: EvidenceItem) -> None:
        d = evidence.model_dump()
        self._conn.execute(
            """INSERT INTO evidence_items (evidence_id, label, source, content,
               verified_at, privacy_level, created_at)
               VALUES (:evidence_id, :label, :source, :content,
               :verified_at, :privacy_level, :created_at)
               ON CONFLICT(evidence_id) DO UPDATE SET
               label=excluded.label,
               source=excluded.source,
               content=excluded.content,
               verified_at=excluded.verified_at,
               privacy_level=excluded.privacy_level""",
            d,
        )
        self._conn.commit()

    def link_skill_evidence(self, link: SkillEvidence) -> None:
        self._conn.execute(
            "INSERT INTO skill_evidence (skill_id, evidence_id) VALUES (?, ?) "
            "ON CONFLICT(skill_id, evidence_id) DO NOTHING",
            (link.skill_id, link.evidence_id),
        )
        self._conn.commit()

    # ── SkillGap ──

    def list_gaps(self, track_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM skill_gaps WHERE track_id = ? ORDER BY created_at",
            (track_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_gap(self, gap: SkillGap) -> None:
        d = gap.model_dump()
        self._conn.execute(
            """INSERT INTO skill_gaps (gap_id, track_id, skill_name,
               target_proficiency, note, created_at)
               VALUES (:gap_id, :track_id, :skill_name,
               :target_proficiency, :note, :created_at)
               ON CONFLICT(gap_id) DO UPDATE SET
               skill_name=excluded.skill_name,
               target_proficiency=excluded.target_proficiency,
               note=excluded.note""",
            d,
        )
        self._conn.commit()

    # ── HardConstraint ──

    def list_hard_constraints(self, track_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM hard_constraints WHERE track_id = ? ORDER BY created_at",
            (track_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_hard_constraint(self, constraint: HardConstraint) -> None:
        d = constraint.model_dump()
        self._conn.execute(
            """INSERT INTO hard_constraints (constraint_id, track_id,
               constraint_text, created_at)
               VALUES (:constraint_id, :track_id, :constraint_text, :created_at)
               ON CONFLICT(constraint_id) DO UPDATE SET
               constraint_text=excluded.constraint_text""",
            d,
        )
        self._conn.commit()

    # ── Preference ──

    def list_preferences(self, track_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM preferences WHERE track_id = ? ORDER BY created_at",
            (track_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_preference(self, preference: Preference) -> None:
        d = preference.model_dump()
        self._conn.execute(
            """INSERT INTO preferences (preference_id, track_id, key, value,
               weight, created_at)
               VALUES (:preference_id, :track_id, :key, :value,
               :weight, :created_at)
               ON CONFLICT(preference_id) DO UPDATE SET
               key=excluded.key,
               value=excluded.value,
               weight=excluded.weight""",
            d,
        )
        self._conn.commit()

    # ── Plan 004: Jobs ──

    def upsert_job(self, job) -> None:
        """Upsert a saved Job row."""
        import json
        from haxjobs.employment.schema import Job
        job.updated_at = _now()
        d = job.model_dump()
        d["allowed_source_hosts"] = json.dumps(job.allowed_source_hosts)
        d["warnings"] = json.dumps(job.warnings)
        d["description_complete"] = 1 if job.description_complete else 0
        self._conn.execute(
            """INSERT INTO jobs (job_id, external_ref, employer_name, title,
               location, source_url, source_type, description,
               source_status, description_kind, description_complete,
               observed_at, allowed_source_hosts, warnings,
               source_content_hash, created_at, updated_at)
               VALUES (:job_id, :external_ref, :employer_name, :title,
               :location, :source_url, :source_type, :description,
               :source_status, :description_kind, :description_complete,
               :observed_at, :allowed_source_hosts, :warnings,
               :source_content_hash, :created_at, :updated_at)
               ON CONFLICT(job_id) DO UPDATE SET
               external_ref=excluded.external_ref,
               employer_name=excluded.employer_name,
               title=excluded.title,
               location=excluded.location,
               source_url=excluded.source_url,
               source_type=excluded.source_type,
               description=excluded.description,
               source_status=excluded.source_status,
               description_kind=excluded.description_kind,
               description_complete=excluded.description_complete,
               observed_at=excluded.observed_at,
               allowed_source_hosts=excluded.allowed_source_hosts,
               warnings=excluded.warnings,
               source_content_hash=excluded.source_content_hash,
               updated_at=excluded.updated_at""",
            d,
        )
        self._conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None

    # ── Plan 004: Job assessments ──

    def upsert_assessment(self, assessment) -> int | None:
        """Insert a new assessment. Returns the auto-assigned sequence.

        Raises IntegrityError if tool_call_id already exists.
        Uses a transaction for atomic check+insert.
        """
        import json
        from haxjobs.employment.schema import JobAssessment
        d = assessment.model_dump()
        d["constraint_checks"] = json.dumps(
            [c.model_dump() if hasattr(c, 'model_dump') else c
             for c in assessment.constraint_checks]
        )
        d["strengths"] = json.dumps(assessment.strengths)
        d["gaps"] = json.dumps(assessment.gaps)
        d["unknowns"] = json.dumps(assessment.unknowns)
        d["evidence_ids"] = json.dumps(assessment.evidence_ids)

        with self._conn:
            self._conn.execute(
                """INSERT INTO job_assessments (
                    assessment_id, job_id, track_id, tool_call_id,
                    recommendation, summary, constraint_checks,
                    strengths, gaps, unknowns, evidence_ids,
                    source_content_hash, created_at
                ) VALUES (
                    :assessment_id, :job_id, :track_id, :tool_call_id,
                    :recommendation, :summary, :constraint_checks,
                    :strengths, :gaps, :unknowns, :evidence_ids,
                    :source_content_hash, :created_at
                )""",
                d,
            )
            cursor = self._conn.execute("SELECT last_insert_rowid()")
            row = cursor.fetchone()
            if row is not None:
                # _row_factory returns dict; column name is "last_insert_rowid()"
                return row["last_insert_rowid()"]

    def get_latest_assessment(self, job_id: str, track_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM job_assessments WHERE job_id = ? AND track_id = ? "
            "ORDER BY sequence DESC LIMIT 1",
            (job_id, track_id),
        ).fetchone()
        return dict(row) if row else None

    def list_assessments(self, job_id: str, track_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM job_assessments WHERE job_id = ? AND track_id = ? "
            "ORDER BY sequence ASC",
            (job_id, track_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_assessment_by_call_id(self, tool_call_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM job_assessments WHERE tool_call_id = ?",
            (tool_call_id,),
        ).fetchone()
        return dict(row) if row else None
