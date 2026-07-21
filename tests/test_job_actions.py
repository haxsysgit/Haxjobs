"""Job actions tests — import, retrieval, assessment, idempotency."""

from __future__ import annotations

import hashlib
import json

import pytest

from haxjobs.employment.job_actions import (
    IdempotencyConflict,
    get_job,
    get_latest_assessment,
    import_job_from_fixture,
    list_assessments,
    normalise_description,
    record_assessment,
)
from haxjobs.employment.schema import ConstraintCheck, Job, JobAssessment
from haxjobs.employment.store import CareerStore


@pytest.fixture
def store() -> CareerStore:
    store = CareerStore(":memory:")
    yield store
    store.close()


def test_import_job_49_from_fixture(store: CareerStore):
    """Job 49 imports with stable ID job-49, correct title, employer."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    assert job.job_id == "job-49"
    assert job.title == "IT Support Analyst"
    assert job.employer_name == "Trainline"
    assert job.description_complete is False  # fixture has content_complete: false

    # Verify in store
    row = store.get_job("job-49")
    assert row is not None
    assert row["title"] == "IT Support Analyst"


def test_import_job_328_from_fixture(store: CareerStore):
    """Job 328 imports with stable ID job-328, content_complete=False."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-328.json")
    assert job.job_id == "job-328"
    assert job.description_complete is False

    row = store.get_job("job-328")
    assert row is not None


def test_get_job_returns_none_for_unknown(store: CareerStore):
    """get_job('nonexistent') returns None."""
    assert get_job(store, "nonexistent") is None


def test_record_assessment_and_retrieve(store: CareerStore):
    """Record assessment, retrieve it as latest."""
    # Need a job and track in the store first
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")

    # Set up a minimal track
    from haxjobs.employment.schema import CareerTrack, Person
    now = "2026-07-21T00:00:00+00:00"
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    assessment = JobAssessment(
        job_id="job-49",
        track_id="t1",
        tool_call_id="call-001",
        recommendation="skip",
        summary="Not a backend role",
        constraint_checks=[
            ConstraintCheck(
                constraint_id="c1",
                constraint_text="Must be backend role",
                result="fail",
            )
        ],
        strengths=[],
        gaps=["Role mismatch"],
        unknowns=[],
    )

    result = record_assessment(store, assessment)
    assert isinstance(result, JobAssessment)
    assert result.recommendation == "skip"
    assert result.assessment_id != ""
    assert result.sequence is not None

    # Retrieve
    latest = get_latest_assessment(store, "job-49", "t1")
    assert latest is not None
    assert latest.recommendation == "skip"
    assert len(latest.constraint_checks) == 1
    assert latest.constraint_checks[0].result == "fail"


def test_assessment_idempotent_replay_same_payload(store: CareerStore):
    """Same call_id + same payload returns existing row, no new write."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    from haxjobs.employment.schema import CareerTrack, Person
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    assessment = JobAssessment(
        job_id="job-49",
        track_id="t1",
        tool_call_id="call-idem-001",
        recommendation="consider",
        summary="Maybe",
    )

    first = record_assessment(store, assessment)
    assert isinstance(first, JobAssessment)

    # Second call with same payload
    second = record_assessment(store, assessment)
    assert isinstance(second, JobAssessment)
    assert second.assessment_id == first.assessment_id
    assert second.sequence == first.sequence

    # Only one row in DB
    all_assmt = list_assessments(store, "job-49", "t1")
    assert len(all_assmt) == 1


def test_assessment_idempotency_conflict_different_payload(store: CareerStore):
    """Same call_id + different payload returns typed idempotency_conflict, writes nothing."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    from haxjobs.employment.schema import CareerTrack, Person
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    assessment1 = JobAssessment(
        job_id="job-49",
        track_id="t1",
        tool_call_id="call-conflict-001",
        recommendation="skip",
        summary="Skip it",
    )

    assessment2 = JobAssessment(
        job_id="job-49",
        track_id="t1",
        tool_call_id="call-conflict-001",
        recommendation="pursue",
        summary="Different summary",
    )

    first = record_assessment(store, assessment1)
    assert isinstance(first, JobAssessment)

    second = record_assessment(store, assessment2)
    assert isinstance(second, IdempotencyConflict)
    assert second.existing_recommendation == "skip"

    # Only one row in DB
    all_assmt = list_assessments(store, "job-49", "t1")
    assert len(all_assmt) == 1


def test_latest_assessment_uses_sequence_not_created_at(store: CareerStore):
    """Two assessments within same created_at second: latest uses sequence order."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    from haxjobs.employment.schema import CareerTrack, Person
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    # Record two assessments
    a1 = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="seq-001",
        recommendation="consider", summary="First",
    )
    a2 = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="seq-002",
        recommendation="skip", summary="Second",
    )

    r1 = record_assessment(store, a1)
    r2 = record_assessment(store, a2)

    # Latest should be the second one (higher sequence)
    latest = get_latest_assessment(store, "job-49", "t1")
    assert latest is not None
    assert latest.sequence == r2.sequence
    assert latest.recommendation == "skip"


def test_assessment_no_fit_score_field(store: CareerStore):
    """JobAssessment has no numeric fit_score field."""
    # Check that the model fields don't include fit_score
    fields = JobAssessment.model_fields
    assert "fit_score" not in fields
    assert "score" not in fields


def test_assessment_no_user_decision_field(store: CareerStore):
    """JobAssessment has no user decision field."""
    fields = JobAssessment.model_fields
    assert "user_decision" not in fields
    assert "decision" not in fields


def test_source_content_hash_computed_server_side(store: CareerStore):
    """Hash is SHA-256 of normalized description, not model supplied."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")

    # The hash should be a valid SHA-256 hex string
    assert len(job.source_content_hash) == 64
    assert all(c in "0123456789abcdef" for c in job.source_content_hash)

    # Verify it matches the normalized description
    normalized = normalise_description(job.description)
    expected = hashlib.sha256(normalized.encode()).hexdigest()
    assert job.source_content_hash == expected


def test_inspect_updates_job_snapshot(store: CareerStore):
    """Placeholder: test that inspection updates Job snapshot.
    Full test requires fake transport — tested in test_employment_tools.py."""
    pass


def test_assessment_hash_loads_from_saved_job(store: CareerStore):
    """Assessment.source_content_hash equals the Job's current source_content_hash."""
    job = import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    from haxjobs.employment.schema import CareerTrack, Person
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    assessment = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="hash-test",
        recommendation="consider", summary="Checking hash",
    )

    result = record_assessment(store, assessment)
    assert isinstance(result, JobAssessment)
    assert result.source_content_hash == job.source_content_hash
