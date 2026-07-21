"""Plan 005 decision persistence, correction, and employment-state recall tests."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import ValidationError

from haxjobs.agent_core.tools import ToolExecutionContext
from haxjobs.employment import job_actions
from haxjobs.employment.schema import CareerTrack, JobDecision, Person
from haxjobs.employment.store import CareerStore
from haxjobs.employment.tools import RecordJobDecisionInput, build_employment_tool_registry


@pytest.fixture
def store() -> CareerStore:
    value = CareerStore(":memory:")
    job_actions.import_job_from_fixture(value, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    value.upsert_person(Person(person_id="p1", name="Test", location="L", created_at=now, updated_at=now))
    value.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend", created_at=now, updated_at=now))
    yield value
    value.close()


def _decision(store: CareerStore, call_id: str, user_message_id: str, label: str, reason: str = "") -> JobDecision:
    result = job_actions.record_decision(
        store,
        JobDecision(
            job_id="job-49",
            track_id="t1",
            tool_call_id=call_id,
            source_user_message_id=user_message_id,
            label=label,  # type: ignore[arg-type]
            reason=reason,
        ),
    )
    assert isinstance(result, JobDecision)
    return result


def test_record_decision_and_retrieve_latest(store: CareerStore):
    result = _decision(store, "decision-1", "user-1", "skip")
    latest = job_actions.get_latest_decision(store, "job-49", "t1")
    assert latest is not None
    assert latest.decision_id == result.decision_id
    assert latest.label == "skip"
    assert latest.sequence == 1


def test_decision_idempotent_replay_same_payload(store: CareerStore):
    first = _decision(store, "decision-replay", "user-1", "save", "keep for later")
    second = _decision(store, "decision-replay", "user-1", "save", "keep for later")
    assert second.decision_id == first.decision_id
    assert second.sequence == first.sequence
    assert second.replayed is True
    assert len(job_actions.list_decisions(store, "job-49", "t1")) == 1


def test_decision_idempotency_conflict_different_payload(store: CareerStore):
    _decision(store, "decision-conflict", "user-1", "skip")
    result = job_actions.record_decision(
        store,
        JobDecision(
            job_id="job-49",
            track_id="t1",
            tool_call_id="decision-conflict",
            source_user_message_id="user-1",
            label="apply",
        ),
    )
    assert not isinstance(result, JobDecision)
    assert result.existing_label == "skip"
    assert len(job_actions.list_decisions(store, "job-49", "t1")) == 1


def test_decision_correction_appends_not_mutates(store: CareerStore):
    first = _decision(store, "decision-skip", "user-1", "skip")
    second = _decision(store, "decision-save", "user-2", "save")
    history = job_actions.list_decisions(store, "job-49", "t1")
    assert [item.label for item in history] == ["skip", "save"]
    assert history[0].decision_id == first.decision_id
    assert job_actions.get_latest_decision(store, "job-49", "t1").decision_id == second.decision_id


def test_decision_labels_are_restricted():
    with pytest.raises(ValidationError):
        RecordJobDecisionInput(job_id="job-49", label="recommend")  # type: ignore[arg-type]


def test_latest_decision_uses_sequence(store: CareerStore):
    _decision(store, "decision-1", "user-1", "maybe")
    _decision(store, "decision-2", "user-2", "skip")
    latest = _decision(store, "decision-3", "user-3", "save")
    assert job_actions.get_latest_decision(store, "job-49", "t1").sequence == latest.sequence


def test_apply_label_has_no_side_effect(store: CareerStore):
    _decision(store, "decision-apply", "user-apply", "apply")
    assert job_actions.get_latest_decision(store, "job-49", "t1").label == "apply"
    assert store.list_decisions("job-49", "t1")
    assert store._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_decisions'").fetchone()


def test_reason_not_invented(store: CareerStore):
    decision = _decision(store, "decision-no-reason", "user-1", "skip")
    assert decision.reason == ""


def test_decision_survives_new_session(store: CareerStore):
    _decision(store, "session-a-call", "session-a-user", "skip")
    # A later host/session reads the employment store, rather than transcript memory.
    projected = job_actions.get_job(store, "job-49", "t1")
    assert projected["latest_decision"]["label"] == "skip"
    assert projected["latest_decision"]["source_user_message_id"] == "session-a-user"


def test_get_job_without_decision(store: CareerStore):
    projected = job_actions.get_job(store, "job-49", "t1")
    assert projected["latest_decision"] is None
    assert projected["latest_assessment"] is None


def test_list_decisions_includes_history(store: CareerStore):
    _decision(store, "history-1", "user-1", "skip")
    _decision(store, "history-2", "user-2", "save")
    assert [d.label for d in job_actions.list_decisions(store, "job-49", "t1")] == ["skip", "save"]


@pytest.mark.asyncio
async def test_tool_binds_track_and_user_message(store: CareerStore):
    registry, active = build_employment_tool_registry(store, track_id="t1")
    context = ToolExecutionContext(
        session_id="session-b",
        turn_id="turn-b",
        call_id="tool-b",
        user_message_id="message-b",
        cancel_event=asyncio.Event(),
    )
    result = await registry.dispatch(
        "record_job_decision",
        json.dumps({"job_id": "job-49", "label": "save"}),
        active,
        context,
    )
    assert result["ok"] is True
    stored = job_actions.get_latest_decision(store, "job-49", "t1")
    assert stored.track_id == "t1"
    assert stored.source_user_message_id == "message-b"
    assert "track_id" not in RecordJobDecisionInput.model_json_schema()["properties"]
    assert "user_message_id" not in RecordJobDecisionInput.model_json_schema()["properties"]
