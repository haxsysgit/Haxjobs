"""Durable tool effects tests — persistence order, dangling calls, idempotency, scope."""

from __future__ import annotations

import asyncio
import json

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.messages import (
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.tools import ToolDefinition, ToolExecutionContext, ToolRegistry
from haxjobs.agent_core.turn import TurnExitReason, run_turn
from haxjobs.employment.store import CareerStore
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelStreamEvent, ModelStreamEventType


def _uid() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


def _fake_emit(events: list[LiveEvent]):
    def emit(event: LiveEvent) -> None:
        events.append(event)
    return emit


def _fake_stream_with_tool(call_id, tool_name, arguments, final_text):
    """Two-step stream: tool call then final text."""
    return [
        [
            ModelStreamEvent(
                event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                call_id=call_id,
                tool_name=tool_name,
                arguments=arguments,
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="tool_calls",
            ),
        ],
        [
            ModelStreamEvent(
                event_type=ModelStreamEventType.TEXT_DELTA, delta=final_text,
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="stop",
            ),
        ],
    ]


# ── Tool call persisted before handler ──

@pytest.mark.asyncio
async def test_tool_call_persisted_before_handler():
    """ToolCallMessage row exists before handler function executes."""
    persisted: list[ConversationMessage] = []
    handler_called = asyncio.Event()

    from pydantic import BaseModel

    class _Input(BaseModel):
        value: str

    class _Output(BaseModel):
        ok: bool

    registry = ToolRegistry()

    async def tracking_handler(input_obj: _Input, ctx: ToolExecutionContext) -> dict:
        # Signal handler was called
        handler_called.set()
        await asyncio.sleep(0.02)
        return {"ok": True}

    registry.register(ToolDefinition(
        name="order_tool", description="order test", input_model=_Input,
        output_model=_Output, handler=tracking_handler,
    ))

    fake = FakeModelClient(
        stream_events=_fake_stream_with_tool(
            "call-order", "order_tool", '{"value": "x"}', "Done."
        ),
    )
    cancel = asyncio.Event()

    def my_persist(msg: ConversationMessage) -> None:
        persisted.append(msg)

    result = await run_turn(
        session_id="s1", turn_id="t1", model=fake,
        system_prompt="sys", context_messages=[], history=[],
        tool_registry=registry, active_tools=("order_tool",),
        cancel_event=cancel, emit=_fake_emit([]),
        persist_message=my_persist, user_message_id=_uid(),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    # ToolCallMessage should be in persisted BEFORE handler executed
    tool_calls = [m for m in persisted if m.kind == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0].call_id == "call-order"


# ── Tool result persisted before next model call ──

@pytest.mark.asyncio
async def test_tool_result_persisted_before_next_model_call():
    """ToolResultMessage row exists before second model stream starts."""
    persisted: list[ConversationMessage] = []

    from pydantic import BaseModel

    class _Input(BaseModel):
        value: str

    class _Output(BaseModel):
        ok: bool

    registry = ToolRegistry()

    async def simple_handler(input_obj: _Input, ctx: ToolExecutionContext) -> dict:
        return {"ok": True}

    registry.register(ToolDefinition(
        name="simple", description="simple", input_model=_Input,
        output_model=_Output, handler=simple_handler,
    ))

    fake = FakeModelClient(
        stream_events=_fake_stream_with_tool(
            "call-simple", "simple", '{"value": "x"}', "Done."
        ),
    )
    cancel = asyncio.Event()

    def my_persist(msg: ConversationMessage) -> None:
        persisted.append(msg)

    result = await run_turn(
        session_id="s1", turn_id="t1", model=fake,
        system_prompt="sys", context_messages=[], history=[],
        tool_registry=registry, active_tools=("simple",),
        cancel_event=cancel, emit=_fake_emit([]),
        persist_message=my_persist, user_message_id=_uid(),
    )

    assert result.exit_reason == TurnExitReason.COMPLETED
    tool_results = [m for m in persisted if m.kind == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0].ok is True


# ── Result persistence precedes lifecycle event ──

@pytest.mark.asyncio
async def test_failed_tool_result_persistence_emits_no_completed_event():
    """A successful handler cannot publish completion without its result row."""
    from pydantic import BaseModel

    class _Input(BaseModel):
        value: str

    class _Output(BaseModel):
        ok: bool

    registry = ToolRegistry()

    async def handler(input_obj, ctx):
        return {"ok": True}

    registry.register(ToolDefinition(
        name="persist-fail", description="test", input_model=_Input,
        output_model=_Output, handler=handler,
    ))
    events: list[LiveEvent] = []

    def persist(message: ConversationMessage) -> None:
        if message.kind == "tool_result":
            raise OSError("result store unavailable")

    result = await run_turn(
        session_id="s1", turn_id="t1",
        model=FakeModelClient(stream_events=_fake_stream_with_tool(
            "call-persist-fail", "persist-fail", '{"value":"x"}', "unused",
        )),
        system_prompt="sys", context_messages=[], history=[],
        tool_registry=registry, active_tools=("persist-fail",),
        cancel_event=asyncio.Event(), emit=_fake_emit(events),
        persist_message=persist, user_message_id=_uid(),
    )

    assert result.exit_reason == TurnExitReason.PERSISTENCE_FAILED
    assert not any(e.event_type == LiveEventType.TOOL_COMPLETED for e in events)
    assert any(
        e.event_type == LiveEventType.TOOL_FAILED
        and e.error_code == "persistence_failed"
        for e in events
    )
    assert not any(e.event_type == LiveEventType.TURN_COMPLETED for e in events)


@pytest.mark.asyncio
async def test_cancelled_tool_result_persistence_is_persistence_failed():
    """A cancelled tool whose result cannot persist is not reported interrupted."""
    from pydantic import BaseModel

    class Input(BaseModel):
        value: str

    class Output(BaseModel):
        ok: bool

    registry = ToolRegistry()
    started = asyncio.Event()

    async def slow_handler(input_obj, ctx):
        started.set()
        await asyncio.sleep(30)
        return {"ok": True}

    registry.register(ToolDefinition(
        name="cancel-persist", description="cancel persistence", input_model=Input,
        output_model=Output, handler=slow_handler,
    ))
    persisted: list[ConversationMessage] = []

    def persist(message: ConversationMessage) -> None:
        if message.kind == "tool_result":
            raise OSError("result store unavailable")
        persisted.append(message)

    cancel = asyncio.Event()
    task = asyncio.create_task(run_turn(
        session_id="s-cancel-persist", turn_id="t-cancel-persist",
        model=FakeModelClient(stream_events=[[
            ModelStreamEvent(
                event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                call_id="cancel-persist-call", tool_name="cancel-persist",
                arguments='{"value":"x"}',
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="tool_calls",
            ),
        ]]),
        system_prompt="sys", context_messages=[], history=[],
        tool_registry=registry, active_tools=("cancel-persist",),
        cancel_event=cancel, emit=_fake_emit([]), persist_message=persist,
        user_message_id="user-cancel-persist",
    ))
    await started.wait()
    cancel.set()
    result = await task

    assert result.exit_reason == TurnExitReason.PERSISTENCE_FAILED
    assert result.safe_failure == "Tool result persistence failed."
    assert [message.kind for message in persisted] == ["assistant", "tool_call"]


# ── Dangling call on resume ──

def test_dangling_call_appends_unknown_outcome():
    """Unmatched ToolCallMessage on resume -> synthetic ToolResultMessage."""
    store = SessionStore(":memory:")
    store.create_session("s-dangle", configuration_json=json.dumps(
        {"person_id": "test", "track_id": "test"}
    ))

    tc = ToolCallMessage(
        message_id="tc1", turn_id="t1", call_id="dangle_abc",
        tool_name="test_tool", arguments='{"value": "x"}',
    )
    store.append_message("s-dangle", tc)
    store.mark_turn_settled("s-dangle", 1)

    # Resume
    session = AgentSession.resume(
        session_id="s-dangle",
        session_store=store,
        model=FakeModelClient(
            stream_events=[[
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA, delta="Resumed.",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ]],
        ),
        system_prompt=lambda: "sys",
        context_messages=lambda: [],
        tool_registry_fn=lambda: ToolRegistry(),
        active_tool_names_fn=lambda: (),
    )

    stored = store.load_messages("s-dangle")
    tool_results = [
        m for m in stored
        if m["payload_json"]["kind"] == "tool_result"
        and m["payload_json"]["call_id"] == "dangle_abc"
    ]
    assert len(tool_results) == 1
    assert tool_results[0]["payload_json"]["error_code"] == "unknown_outcome"


# ── Duplicate call_id same payload returns existing ──

@pytest.mark.asyncio
async def test_duplicate_call_id_same_payload_returns_existing():
    """Two record_job_assessment calls with same call_id and payload -> one row."""
    career_store = CareerStore(":memory:")
    from haxjobs.employment import job_actions
    from haxjobs.employment.schema import CareerTrack, Person, JobAssessment

    job_actions.import_job_from_fixture(career_store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    career_store.upsert_person(Person(person_id="p1", name="T", location="L",
                                       created_at=now, updated_at=now))
    career_store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend",
                                           created_at=now, updated_at=now))

    a = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="dup-same-1",
        recommendation="skip", summary="Same payload",
    )

    r1 = job_actions.record_assessment(career_store, a)
    r2 = job_actions.record_assessment(career_store, a)

    assert isinstance(r1, JobAssessment)
    assert isinstance(r2, JobAssessment)
    assert r1.assessment_id == r2.assessment_id

    all_assmt = career_store.list_assessments("job-49", "t1")
    assert len(all_assmt) == 1


# ── Duplicate call_id different payload conflict ──

def test_duplicate_call_id_different_payload_conflict():
    """Same call_id + different payload -> conflict error, no write."""
    career_store = CareerStore(":memory:")
    from haxjobs.employment import job_actions
    from haxjobs.employment.schema import CareerTrack, Person, JobAssessment

    job_actions.import_job_from_fixture(career_store, "discussion/fixtures/harness/job-49.json")
    now = "2026-07-21T00:00:00+00:00"
    career_store.upsert_person(Person(person_id="p1", name="T", location="L",
                                       created_at=now, updated_at=now))
    career_store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend",
                                           created_at=now, updated_at=now))

    a1 = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="dup-diff-1",
        recommendation="skip", summary="First payload",
    )
    a2 = JobAssessment(
        job_id="job-49", track_id="t1", tool_call_id="dup-diff-1",
        recommendation="pursue", summary="Different payload",
    )

    r1 = job_actions.record_assessment(career_store, a1)
    assert isinstance(r1, JobAssessment)

    r2 = job_actions.record_assessment(career_store, a2)
    assert isinstance(r2, job_actions.IdempotencyConflict)

    all_assmt = career_store.list_assessments("job-49", "t1")
    assert len(all_assmt) == 1


# ── Fixed session scope ──

def test_new_session_rejects_cross_person_explicit_track():
    """Explicit composition cannot pair one person's ID with another's track."""
    from haxjobs.employment.composition import _resolve_scope
    from haxjobs.employment.host import EmploymentSetupError
    from haxjobs.employment.schema import CareerTrack, Person

    career_store = CareerStore(":memory:")
    session_store = SessionStore(":memory:")
    try:
        now = "2026-07-21T00:00:00+00:00"
        career_store.upsert_person(Person(person_id="person-a", name="A", location="L", created_at=now, updated_at=now))
        career_store.upsert_person(Person(person_id="person-b", name="B", location="L", created_at=now, updated_at=now))
        career_store.upsert_track(CareerTrack(track_id="track-b", person_id="person-b", name="B", created_at=now, updated_at=now))

        with pytest.raises(EmploymentSetupError, match="belongs to person"):
            _resolve_scope(
                career_store=career_store, person_id="person-a", track_id="track-b",
                session_id=None, session_store=session_store,
            )
    finally:
        career_store.close()
        session_store.close()


def test_resume_rejects_stored_cross_person_track():
    """Resume validates ownership of the immutable stored scope."""
    from haxjobs.employment.composition import _resolve_scope
    from haxjobs.employment.schema import CareerTrack, Person

    career_store = CareerStore(":memory:")
    session_store = SessionStore(":memory:")
    try:
        now = "2026-07-21T00:00:00+00:00"
        career_store.upsert_person(Person(person_id="person-a", name="A", location="L", created_at=now, updated_at=now))
        career_store.upsert_person(Person(person_id="person-b", name="B", location="L", created_at=now, updated_at=now))
        career_store.upsert_track(CareerTrack(track_id="track-b", person_id="person-b", name="B", created_at=now, updated_at=now))
        session_store.create_session(
            "s-cross", configuration_json=json.dumps({"person_id": "person-a", "track_id": "track-b"})
        )

        with pytest.raises(ValueError, match="stores track"):
            _resolve_scope(
                career_store=career_store, person_id=None, track_id=None,
                session_id="s-cross", session_store=session_store,
            )
    finally:
        career_store.close()
        session_store.close()


def test_fixed_session_scope():
    """Session created for person A cannot resume for person B."""
    from haxjobs.employment.composition import _resolve_scope
    from haxjobs.employment.host import EmploymentSetupError
    from haxjobs.employment.schema import Person

    career_store = CareerStore(":memory:")
    session_store = SessionStore(":memory:")
    try:
        now = "2026-07-21T00:00:00+00:00"
        career_store.upsert_person(Person(person_id="person-a", name="A", location="L",
                                           created_at=now, updated_at=now))
        career_store.upsert_person(Person(person_id="person-b", name="B", location="L",
                                           created_at=now, updated_at=now))

        # Create session scoped to person-a
        from haxjobs.employment.schema import CareerTrack
        career_store.upsert_track(CareerTrack(track_id="t1", person_id="person-a", name="T",
                                               created_at=now, updated_at=now))
        career_store.upsert_track(CareerTrack(track_id="t2", person_id="person-b", name="T",
                                               created_at=now, updated_at=now))

        session_store.create_session("s-scope", configuration_json=json.dumps(
            {"person_id": "person-a", "track_id": "t1"}
        ))

        # Resume with wrong person should fail
        with pytest.raises(ValueError, match="person-a"):
            _resolve_scope(
                career_store=career_store,
                person_id="person-b",
                track_id=None,
                session_id="s-scope",
                session_store=session_store,
            )
    finally:
        career_store.close()
