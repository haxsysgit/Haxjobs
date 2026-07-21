"""Employment composition root — wires provider, career store, host, session.

Plan 003 Phase 7: the single place that creates all runtime objects.
"""

from __future__ import annotations

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
) -> AgentSession:
    """Create an AgentSession wired to real or fake providers.

    Args:
        session_id: Existing session to resume, or None for a new session.
        fake: Use FakeModelClient with scriptable streams (for --fake mode).
        fake_delay_ms: Per-event delay for fake model (cancellation tests).
        session_db_path: Override session database path.

    Returns:
        An AgentSession ready for prompt() calls.

    Raises:
        EmploymentSetupError: If the career graph is not set up.
    """
    db_path = Path(session_db_path) if session_db_path else SESSION_DB_PATH
    session_store = SessionStore(db_path)

    # Career store
    career_store = CareerStore(CAREER_DB_PATH)

    try:
        # Create host
        host = EmploymentHost(
            store=career_store,
            person_id="arinze-elensulu",
        )
    except EmploymentSetupError:
        career_store.close()
        session_store.close()
        raise

    # Model
    if fake:
        model = _fake_model(delay_ms=fake_delay_ms)
    else:
        model = OpenAIModelClient()

    # Session
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
        import uuid

        new_id = session_id or uuid.uuid4().hex[:12]
        session_store.create_session(new_id)
        session = AgentSession(
            session_id=new_id,
            session_store=session_store,
            model=model,
            system_prompt=host.system_prompt,
            context_messages=host.context_messages,
            tool_registry_fn=host.registered_tools,
            active_tool_names_fn=host.active_tool_names,
        )

    # Register cleanup so CareerStore is closed when the session closes
    session.add_cleanup(career_store.close)

    return session


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
