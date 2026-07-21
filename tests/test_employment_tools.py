"""Employment tools tests — get_job, inspect_job_source, record_job_assessment."""

from __future__ import annotations

import asyncio
import json

import pytest

from haxjobs.agent_core.tools import EffectKind, ToolExecutionContext
from haxjobs.employment import job_actions
from haxjobs.employment.store import CareerStore
from haxjobs.employment.tools import (
    GetJobInput,
    InspectJobSourceInput,
    RecordJobAssessmentInput,
    build_employment_tool_registry,
)


def _test_ctx(call_id: str = "test-call-1") -> ToolExecutionContext:
    return ToolExecutionContext(
        session_id="s1",
        turn_id="t1",
        call_id=call_id,
        user_message_id="u1",
        cancel_event=asyncio.Event(),
    )


@pytest.fixture
def store() -> CareerStore:
    store = CareerStore(":memory:")
    # Import jobs
    job_actions.import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    job_actions.import_job_from_fixture(store, "discussion/fixtures/harness/job-328.json")

    # Set up minimal career graph
    from haxjobs.employment.schema import CareerTrack, Person
    now = "2026-07-21T00:00:00+00:00"
    store.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))

    yield store
    store.close()


@pytest.mark.asyncio
async def test_get_job_returns_job_fields(store: CareerStore):
    """get_job('job-49') returns title, employer, description, etc."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    result = await registry.dispatch(
        name="get_job",
        arguments=json.dumps({"job_id": "job-49"}),
        active_names=active,
        context=_test_ctx(),
    )

    assert result["ok"] is True
    assert result["data"]["title"] == "IT Support Analyst"
    assert result["data"]["employer_name"] == "Trainline"
    assert result["data"]["description_complete"] is False


@pytest.mark.asyncio
async def test_get_job_unknown_returns_error(store: CareerStore):
    """get_job('job-999') returns ok=False in data with error."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    result = await registry.dispatch(
        name="get_job",
        arguments=json.dumps({"job_id": "job-999"}),
        active_names=active,
        context=_test_ctx(),
    )

    assert result["data"]["ok"] is False
    assert "not found" in result["data"].get("error", "").lower()


@pytest.mark.asyncio
async def test_inspect_job_source_model_cannot_supply_url(store: CareerStore):
    """Tool input model has no url field."""
    # Validate that InspectJobSourceInput only has job_id
    input_schema = InspectJobSourceInput.model_json_schema()
    assert "url" not in input_schema.get("properties", {})
    assert "job_id" in input_schema.get("properties", {})


@pytest.mark.asyncio
async def test_record_job_assessment_idempotent_replay(store: CareerStore):
    """Same call_id + same payload returns existing row."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    args = {
        "job_id": "job-49",
        "track_id": "t1",
        "recommendation": "skip",
        "summary": "Not a backend role",
        "constraint_checks": [
            {"constraint_id": "c1", "constraint_text": "Must be backend", "result": "fail"}
        ],
        "strengths": [],
        "gaps": ["role mismatch"],
        "unknowns": [],
        "evidence_ids": [],
    }

    ctx = _test_ctx("replay-call-1")
    first = await registry.dispatch(
        name="record_job_assessment",
        arguments=json.dumps(args),
        active_names=active,
        context=ctx,
    )
    assert first["ok"] is True

    # Same call_id, same args
    second = await registry.dispatch(
        name="record_job_assessment",
        arguments=json.dumps(args),
        active_names=active,
        context=ctx,
    )
    assert second["ok"] is True
    assert second["data"]["assessment_id"] == first["data"]["assessment_id"]


@pytest.mark.asyncio
async def test_record_job_assessment_idempotency_conflict(store: CareerStore):
    """Same call_id + different payload returns structured error, writes nothing."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    args1 = {
        "job_id": "job-49",
        "track_id": "t1",
        "recommendation": "skip",
        "summary": "Skip this",
        "constraint_checks": [],
        "strengths": [],
        "gaps": [],
        "unknowns": [],
        "evidence_ids": [],
    }

    args2 = {**args1, "recommendation": "pursue", "summary": "Different assessment"}

    ctx = _test_ctx("conflict-call-1")
    first = await registry.dispatch(
        name="record_job_assessment",
        arguments=json.dumps(args1),
        active_names=active,
        context=ctx,
    )
    assert first["ok"] is True

    second = await registry.dispatch(
        name="record_job_assessment",
        arguments=json.dumps(args2),
        active_names=active,
        context=ctx,
    )
    assert second["data"]["ok"] is False
    assert "conflict" in second["data"].get("error", "").lower()


@pytest.mark.asyncio
async def test_record_job_assessment_uses_context_call_id(store: CareerStore):
    """Tool uses context.call_id, not a separate id parameter."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    args = {
        "job_id": "job-49",
        "track_id": "t1",
        "recommendation": "consider",
        "summary": "Testing call_id",
    }

    ctx = _test_ctx("unique-call-id-xyz")
    result = await registry.dispatch(
        name="record_job_assessment",
        arguments=json.dumps(args),
        active_names=active,
        context=ctx,
    )

    assert result["ok"] is True
    # The assessment_id is derived from tool_call_id via make_stable_id
    assert result["data"]["assessment_id"] != ""


def test_tool_effect_kinds_are_correct(store: CareerStore):
    """get_job=READ, inspect=INTERNAL_WRITE, record_assessment=INTERNAL_WRITE."""
    registry, active = build_employment_tool_registry(store, track_id="t1")

    get_job_def = registry._tools.get("get_job")
    inspect_def = registry._tools.get("inspect_job_source")
    record_def = registry._tools.get("record_job_assessment")

    assert get_job_def is not None
    assert get_job_def.effect_kind == EffectKind.READ
    assert get_job_def.retry_safe is True

    assert inspect_def is not None
    assert inspect_def.effect_kind == EffectKind.INTERNAL_WRITE
    assert inspect_def.retry_safe is True

    assert record_def is not None
    assert record_def.effect_kind == EffectKind.INTERNAL_WRITE
    assert record_def.retry_safe is False
