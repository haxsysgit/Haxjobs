"""Plain Python actions for job import, retrieval, source inspection, and assessment.

Tool handlers wrap these actions. Tests for actions do not need the tool registry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from haxjobs.employment.identifiers import make_stable_id
from haxjobs.employment.schema import Job, JobAssessment


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IdempotencyConflict:
    """Typed conflict: same tool_call_id, different payload."""
    existing_assessment_id: str
    existing_recommendation: str
    conflict_detail: str


@dataclass
class SourceInspectionResult:
    """Result of a source inspection action."""
    ok: bool
    content_hash: str = ""
    visible_text: str = ""
    error: str = ""
    status: str = ""
    content_type: str = ""
    description_complete: bool | None = None
    warnings: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def import_job_from_fixture(store, fixture_path: str) -> Job:
    """Import a job from a JSON fixture file into the store."""
    raw = json.loads(open(fixture_path).read())
    job = Job(
        job_id=f"job-{raw['job_ref']}",
        external_ref=str(raw.get("job_ref", "")),
        employer_name=raw.get("employer_name"),
        title=raw.get("title", ""),
        location=raw.get("location", ""),
        source_url=raw.get("source_url", ""),
        source_type=raw.get("source_type", ""),
        description=raw.get("description", ""),
        source_status=raw.get("source_status", ""),
        description_kind=raw.get("description_kind", ""),
        description_complete=raw.get("content_complete", False),
        observed_at=raw.get("observed_at", _utcnow()),
        allowed_source_hosts=raw.get("allowed_source_hosts", []),
        warnings=raw.get("warnings", []),
    )
    # Compute initial source content hash
    normalized = normalise_description(job.description)
    job.source_content_hash = hashlib.sha256(normalized.encode()).hexdigest()
    store.upsert_job(job)
    return job


def get_job(store, job_id: str) -> Job | None:
    """Retrieve a Job by ID."""
    row = store.get_job(job_id)
    if row is None:
        return None
    return _job_from_row(row)


def record_assessment(store, assessment: JobAssessment) -> JobAssessment | IdempotencyConflict:
    """Append an assessment. Returns existing or conflict on duplicate tool_call_id."""
    import sqlite3

    # Load current job hash server-side
    job_row = store.get_job(assessment.job_id)
    if job_row is None:
        raise ValueError(f"Job {assessment.job_id} not found")

    # Work on a copy to avoid mutating the caller's object
    assessment = assessment.model_copy()

    # Set assessment_id from tool_call_id
    assessment.assessment_id = make_stable_id("asmt", assessment.tool_call_id)
    assessment.source_content_hash = job_row.get("source_content_hash", "")
    assessment.sequence = None  # store-populated

    # Check for existing assessment with same tool_call_id
    existing = store.get_assessment_by_call_id(assessment.tool_call_id)
    if existing is not None:
        # Compare semantic payload (exclude generated fields)
        existing_assmt = _assessment_from_row(existing)
        if _assessments_equal(assessment, existing_assmt):
            # Same payload -> idempotent replay
            return existing_assmt
        else:
            # Different payload -> conflict
            return IdempotencyConflict(
                existing_assessment_id=existing["assessment_id"],
                existing_recommendation=existing["recommendation"],
                conflict_detail=f"Same tool_call_id ({assessment.tool_call_id}) with different payload",
            )

    # Insert new assessment
    try:
        seq = store.upsert_assessment(assessment)
        assessment.sequence = seq
    except sqlite3.IntegrityError:
        # Race condition: check again
        existing = store.get_assessment_by_call_id(assessment.tool_call_id)
        if existing is not None:
            existing_assmt = _assessment_from_row(existing)
            if _assessments_equal(assessment, existing_assmt):
                return existing_assmt
            return IdempotencyConflict(
                existing_assessment_id=existing["assessment_id"],
                existing_recommendation=existing["recommendation"],
                conflict_detail=f"Same tool_call_id ({assessment.tool_call_id}) with different payload",
            )
        raise

    return assessment


def get_latest_assessment(store, job_id: str, track_id: str) -> JobAssessment | None:
    """Return the most recent assessment for a job/track pair."""
    row = store.get_latest_assessment(job_id, track_id)
    if row is None:
        return None
    return _assessment_from_row(row)


def list_assessments(store, job_id: str, track_id: str) -> list[JobAssessment]:
    """All assessments for a job/track pair, ordered by sequence ASC."""
    rows = store.list_assessments(job_id, track_id)
    return [_assessment_from_row(r) for r in rows]


async def inspect_job_source(
    store,
    job_id: str,
    fetcher,
) -> SourceInspectionResult:
    """Fetch source for a saved job and update the Job row's current snapshot."""
    job = get_job(store, job_id)
    if job is None:
        return SourceInspectionResult(ok=False, error="Job not found")

    # Fetch from source URL
    raw_result = await fetcher.fetch_from_job(job)
    if not raw_result.ok:
        return SourceInspectionResult(
            ok=False,
            error=raw_result.error or "fetch failed",
            status=raw_result.status,
        )

    # Compute hash server side
    normalized = normalise_description(raw_result.visible_text)
    content_hash = hashlib.sha256(normalized.encode()).hexdigest()

    # Update Job snapshot
    job.description = normalized
    job.source_content_hash = content_hash
    if raw_result.status:
        job.source_status = raw_result.status
    job.description_kind = "source_page_text"
    job.warnings = list(raw_result.warnings) if raw_result.warnings else []
    job.observed_at = _utcnow()
    if raw_result.description_complete is not None:
        job.description_complete = raw_result.description_complete
    store.upsert_job(job)

    return SourceInspectionResult(
        ok=True,
        content_hash=content_hash,
        visible_text=raw_result.visible_text,
        status=raw_result.status,
        content_type=getattr(raw_result, "content_type", ""),
        description_complete=raw_result.description_complete,
        warnings=job.warnings,
    )


def normalise_description(text: str) -> str:
    """Normalize description text: strip extra whitespace, normalize line endings."""
    import re
    # Collapse multiple newlines to at most two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


# ── Helpers ──

def _job_from_row(row: dict) -> Job:
    row = dict(row)
    # Parse JSON columns
    for col in ("allowed_source_hosts", "warnings"):
        if isinstance(row.get(col), str):
            try:
                row[col] = json.loads(row[col])
            except (json.JSONDecodeError, TypeError):
                row[col] = []
    row["description_complete"] = bool(row.get("description_complete", 0))
    return Job.model_validate(row)


def _assessment_from_row(row: dict) -> JobAssessment:
    row = dict(row)
    for col in ("constraint_checks", "strengths", "gaps", "unknowns", "evidence_ids"):
        if isinstance(row.get(col), str):
            try:
                row[col] = json.loads(row[col])
            except (json.JSONDecodeError, TypeError):
                row[col] = []
    return JobAssessment.model_validate(row)


def _assessments_equal(a: JobAssessment, b: JobAssessment) -> bool:
    """Compare semantic payload excluding generated fields."""
    return (
        a.job_id == b.job_id
        and a.track_id == b.track_id
        and a.tool_call_id == b.tool_call_id
        and a.recommendation == b.recommendation
        and a.summary == b.summary
        and a.constraint_checks == b.constraint_checks
        and a.strengths == b.strengths
        and a.gaps == b.gaps
        and a.unknowns == b.unknowns
        and a.evidence_ids == b.evidence_ids
        and a.source_content_hash == b.source_content_hash
    )


# ── CLI entry point for one-way job import ──

if __name__ == "__main__":
    import sys
    from haxjobs.config import CAREER_DB_PATH
    from haxjobs.employment.store import CareerStore

    if len(sys.argv) < 2:
        print("Usage: python -m haxjobs.employment.job_actions import <fixture_path>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "import":
        fixture_path = sys.argv[2]
        store = CareerStore(CAREER_DB_PATH)
        try:
            job = import_job_from_fixture(store, fixture_path)
            print(f"Imported job: {job.job_id} — {job.title} at {job.employer_name or '(unknown)'}")
        finally:
            store.close()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
