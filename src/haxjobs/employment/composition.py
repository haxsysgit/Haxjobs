"""Employment composition root — wires provider, career store, host, session.

Plan 003 Phase 7: the single place that creates all runtime objects.
Plan 004: immutable session configuration, person/track auto-selection, cleanup on failure.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.config import CAREER_DB_PATH, SESSION_DB_PATH
from haxjobs.employment.host import EmploymentHost, EmploymentSetupError
from haxjobs.employment.store import CareerStore
from haxjobs.model.client import ModelClient, OpenAIModelClient
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelResponse, ModelStreamEvent, ModelStreamEventType


def compose_session(
    *,
    session_id: str | None = None,
    fake: bool = False,
    fake_delay_ms: float = 0,
    session_db_path: str | Path | None = None,
    person_id: str | None = None,
    track_id: str | None = None,
) -> AgentSession:
    """Create an AgentSession wired to real or fake providers.

    Args:
        session_id: Existing session to resume, or None for a new session.
        fake: Use FakeModelClient with scriptable streams (for --fake mode).
        fake_delay_ms: Per-event delay for fake model (cancellation tests).
        session_db_path: Override session database path.
        person_id: Explicit person selection (new sessions only).
        track_id: Explicit track selection (new sessions only).

    Returns:
        An AgentSession ready for prompt() calls.

    Raises:
        EmploymentSetupError: If the career graph is not set up.
        ValueError: If session configuration is missing or mismatched.
    """
    db_path = Path(session_db_path) if session_db_path else SESSION_DB_PATH
    session_store = SessionStore(db_path)

    career_store: CareerStore | None = None
    try:
        career_store = CareerStore(CAREER_DB_PATH)
        resolved_person_id, resolved_track_id = _resolve_scope(
            career_store=career_store,
            person_id=person_id,
            track_id=track_id,
            session_id=session_id,
            session_store=session_store,
        )

        host = EmploymentHost(
            store=career_store,
            person_id=resolved_person_id,
            track_id=resolved_track_id,
        )

        if fake:
            model = _fake_model(delay_ms=fake_delay_ms)
        else:
            model = OpenAIModelClient()

        if session_id:
            session = AgentSession.resume(
                session_id=session_id,
                session_store=session_store,
                model=model,
                system_prompt=host.system_prompt,
                context_messages=host.context_messages,
                tool_registry_fn=host.registered_tools,
                active_tool_names_fn=host.active_tool_names,
            )
        else:
            new_id = uuid.uuid4().hex[:12]
            config = json.dumps({"person_id": resolved_person_id, "track_id": resolved_track_id})
            session_store.create_session(new_id, configuration_json=config)
            session = AgentSession(
                session_id=new_id,
                session_store=session_store,
                model=model,
                system_prompt=host.system_prompt,
                context_messages=host.context_messages,
                tool_registry_fn=host.registered_tools,
                active_tool_names_fn=host.active_tool_names,
            )

        # Session.close() owns both stores after successful composition.
        session.add_cleanup(career_store.close)
        return session
    except Exception:
        if career_store is not None:
            career_store.close()
        session_store.close()
        raise


def _resolve_scope(
    *,
    career_store: CareerStore,
    person_id: str | None,
    track_id: str | None,
    session_id: str | None,
    session_store: SessionStore,
) -> tuple[str, str]:
    """Resolve person and track scope for a session.

    For resume: validate stored scope against current host.
    For new: auto-select or use explicit params.
    """
    if session_id:
        # Resume: validate stored scope
        cfg_str = session_store.get_session_configuration(session_id)
        if cfg_str is None:
            raise ValueError(
                f"Session {session_id} has no configuration (created before Plan 004). "
                f"Create a new session with --new."
            )
        cfg = json.loads(cfg_str)
        stored_person_id = cfg["person_id"]
        stored_track_id = cfg["track_id"]
        stored_track = career_store.get_track(stored_track_id)
        if stored_track is None:
            raise ValueError(
                f"Session {session_id} references missing career track "
                f"'{stored_track_id}'. Create a new session."
            )
        if stored_track["person_id"] != stored_person_id:
            raise ValueError(
                f"Session {session_id} stores track '{stored_track_id}' for "
                f"person '{stored_track['person_id']}', not '{stored_person_id}'."
            )

        # If caller provides explicit person_id, validate match
        if person_id is not None and person_id != stored_person_id:
            raise ValueError(
                f"Session {session_id} was created for person '{stored_person_id}' "
                f"but current host is for '{person_id}'. Create a new session."
            )
        if track_id is not None and track_id != stored_track_id:
            raise ValueError(
                f"Session {session_id} was created for track '{stored_track_id}' "
                f"but current host requested '{track_id}'. Create a new session."
            )
        return stored_person_id, stored_track_id

    # New session: resolve person
    if person_id is None:
        people = career_store.list_people()
        if len(people) == 0:
            raise EmploymentSetupError("No people found in career store.")
        if len(people) > 1:
            raise EmploymentSetupError(
                f"Multiple people exist. Specify --person-id. "
                f"Available: {[p['person_id'] for p in people]}"
            )
        person_id = people[0]["person_id"]

    # New session: resolve track
    if track_id is None:
        tracks = career_store.list_tracks(person_id)
        if len(tracks) == 0:
            raise EmploymentSetupError("No career tracks found.")
        if len(tracks) > 1:
            raise EmploymentSetupError(
                f"Multiple tracks exist for {person_id}. Specify --track-id. "
                f"Available: {[t['track_id'] for t in tracks]}"
            )
        track_id = tracks[0]["track_id"]
    else:
        selected_track = career_store.get_track(track_id)
        if selected_track is None:
            raise EmploymentSetupError(f"Career track '{track_id}' not found.")
        if selected_track["person_id"] != person_id:
            raise EmploymentSetupError(
                f"Career track '{track_id}' belongs to person "
                f"'{selected_track['person_id']}', not '{person_id}'."
            )

    return person_id, track_id


def _fake_model(delay_ms: float = 0) -> FakeModelClient:
    """Build a fake model with basic scripted responses.

    Args:
        delay_ms: Per-event delay for cancellation tests (0 = instant).
    """
    return FakeModelClient(
        responses=[
            ModelResponse(
                text="FAKE: I am a simulated Hax model. The runtime is working correctly.",
                finish_reason="stop",
                model="fake",
                provider="fake",
            ),
        ],
        stream_events=[
            [
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA,
                    delta="FAKE: I am a simulated Hax model. ",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.TEXT_DELTA,
                    delta="The runtime is working correctly.",
                ),
                ModelStreamEvent(
                    event_type=ModelStreamEventType.RESPONSE_COMPLETED,
                    finish_reason="stop",
                ),
            ],
        ],
        repeat=True,
        delay_ms=delay_ms,
    )
