"""Job 328 trajectory — fake, no network.

Tests the full saved job assessment workflow: get_job -> thin evidence ->
inspect_job_source -> needs_more_information assessment.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.agent_core.turn import TurnExitReason
from haxjobs.employment import job_actions
from haxjobs.employment.host import EmploymentHost
from haxjobs.employment.store import CareerStore
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelStreamEvent, ModelStreamEventType


def _setup_career_store() -> CareerStore:
    """Set up a career store with jobs and minimal career graph."""
    store = CareerStore(":memory:")
    job_actions.import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
    job_actions.import_job_from_fixture(store, "discussion/fixtures/harness/job-328.json")

    from haxjobs.employment.schema import CareerTrack, Person
    now = "2026-07-21T00:00:00+00:00"
    store.upsert_person(Person(person_id="p1", name="Test User", location="London",
                                created_at=now, updated_at=now))
    store.upsert_track(CareerTrack(track_id="t1", person_id="p1", name="Backend Python Engineer",
                                    created_at=now, updated_at=now))

    return store


def _fake_stream_with_tool_and_text(
    tool_call: tuple | None = None,
    text: str = "Final answer.",
) -> list[list[ModelStreamEvent]]:
    """Build a fake stream: optional tool call, then final text."""
    streams: list[list[ModelStreamEvent]] = []
    if tool_call:
        call_id, tool_name, args = tool_call
        streams.append([
            ModelStreamEvent(
                event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
            ),
            ModelStreamEvent(
                event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                finish_reason="tool_calls",
            ),
        ])
    streams.append([
        ModelStreamEvent(
            event_type=ModelStreamEventType.TEXT_DELTA, delta=text,
        ),
        ModelStreamEvent(
            event_type=ModelStreamEventType.RESPONSE_COMPLETED,
            finish_reason="stop",
        ),
    ])
    return streams


@pytest.mark.asyncio
async def test_job_328_incomplete_assessment_trajectory():
    """Full fake trajectory: thin job -> source inspection -> needs_more_information.

    The fake model is scripted to:
    1. Call get_job("job-328")
    2. Call inspect_job_source("job-328")
    3. Call record_job_assessment with needs_more_information
    4. Give a natural reply
    """
    store = _setup_career_store()
    session_store = SessionStore(":memory:")
    try:
        # Build host
        host = EmploymentHost(store=store, person_id="p1", track_id="t1")

        # Scripted fake model: get_job -> inspect -> record -> text
        fake_model = FakeModelClient(
            stream_events=[
                # Step 1: get_job
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id="call-get",
                        tool_name="get_job",
                        arguments=json.dumps({"job_id": "job-328"}),
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="tool_calls",
                    ),
                ],
                # Step 2: inspect_job_source (thin evidence)
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id="call-inspect",
                        tool_name="inspect_job_source",
                        arguments=json.dumps({"job_id": "job-328"}),
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="tool_calls",
                    ),
                ],
                # Step 3: record_job_assessment
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id="call-record",
                        tool_name="record_job_assessment",
                        arguments=json.dumps({
                            "job_id": "job-328",
                            "track_id": "t1",
                            "recommendation": "needs_more_information",
                            "summary": "Job description is thin/incomplete. Cannot fully evaluate.",
                            "constraint_checks": [],
                            "strengths": [],
                            "gaps": ["insufficient job description"],
                            "unknowns": ["full job requirements", "tech stack details"],
                            "evidence_ids": [],
                        }),
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="tool_calls",
                    ),
                ],
                # Step 4: final text
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.TEXT_DELTA,
                        delta="Job 328 has a very thin description. I can't evaluate it properly yet.",
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="stop",
                    ),
                ],
            ],
        )

        # Create session
        import uuid
        new_id = uuid.uuid4().hex[:12]
        session_store.create_session(new_id, configuration_json=json.dumps(
            {"person_id": "p1", "track_id": "t1"}
        ))
        session = AgentSession(
            session_id=new_id,
            session_store=session_store,
            model=fake_model,
            system_prompt=host.system_prompt,
            context_messages=host.context_messages,
            tool_registry_fn=host.registered_tools,
            active_tool_names_fn=host.active_tool_names,
        )
        session.add_cleanup(store.close)

        result = await session.prompt("What do you think of job 328?")
        assert result.exit_reason is not None

        # Check that assessment was recorded
        stored = session_store.load_messages(new_id)
        tool_results = [
            m for m in stored
            if m["payload_json"]["kind"] == "tool_result"
            and m["payload_json"]["tool_name"] == "record_job_assessment"
        ]
        assert len(tool_results) == 1

        # Check the assessment in the store
        assessments = store.list_assessments("job-328", "t1")
        assert len(assessments) == 1
        assert assessments[0]["recommendation"] == "needs_more_information"

    finally:
        store.close()


@pytest.mark.asyncio
async def test_job_328_assessment_survives_resume():
    """Close and resume: assessment is retrievable."""
    store = _setup_career_store()
    session_store = SessionStore(":memory:")
    try:
        host = EmploymentHost(store=store, person_id="p1", track_id="t1")

        # First session: record an assessment
        import uuid
        sid = uuid.uuid4().hex[:12]
        session_store.create_session(sid, configuration_json=json.dumps(
            {"person_id": "p1", "track_id": "t1"}
        ))

        # Scripted: record assessment then text
        fake1 = FakeModelClient(
            stream_events=[
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id="call-record-resume",
                        tool_name="record_job_assessment",
                        arguments=json.dumps({
                            "job_id": "job-328",
                            "track_id": "t1",
                            "recommendation": "needs_more_information",
                            "summary": "Thin description for job 328.",
                        }),
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="tool_calls",
                    ),
                ],
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.TEXT_DELTA, delta="Recorded.",
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="stop",
                    ),
                ],
            ],
        )

        session1 = AgentSession(
            session_id=sid,
            session_store=session_store,
            model=fake1,
            system_prompt=host.system_prompt,
            context_messages=host.context_messages,
            tool_registry_fn=host.registered_tools,
            active_tool_names_fn=host.active_tool_names,
        )
        session1.add_cleanup(store.close)
        await session1.prompt("Assess job 328")

        # Resume the session
        fake2 = FakeModelClient(
            stream_events=[
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.COMPLETE_TOOL_CALL,
                        call_id="call-get-resume",
                        tool_name="get_job",
                        arguments=json.dumps({"job_id": "job-328"}),
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="tool_calls",
                    ),
                ],
                [
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.TEXT_DELTA,
                        delta="You assessed job 328 as needing more information.",
                    ),
                    ModelStreamEvent(
                        event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                        finish_reason="stop",
                    ),
                ],
            ],
        )

        session2 = AgentSession.resume(
            session_id=sid,
            session_store=session_store,
            model=fake2,
            system_prompt=host.system_prompt,
            context_messages=host.context_messages,
            tool_registry_fn=host.registered_tools,
            active_tool_names_fn=host.active_tool_names,
        )
        session2.add_cleanup(store.close)

        result = await session2.prompt("What did you say about job 328?")
        assert result.exit_reason is not None

        # The assessment should still be in the store
        assessments = store.list_assessments("job-328", "t1")
        assert len(assessments) == 1
        assert assessments[0]["recommendation"] == "needs_more_information"

    finally:
        store.close()
