"""Agent session — owns interaction boundaries, persistence, resume, subscribers, cancellation.

Plan 003 Phase 7: The session persists canonical messages, manages busy-input policy,
and orchestrates turns through the turn runtime.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable

from haxjobs.agent_core.live_events import LiveEvent, LiveEventEmitter, LiveEventType
from haxjobs.agent_core.messages import ConversationMessage, UserMessage
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.turn import TurnExitReason, TurnResult, run_turn
from haxjobs.model.client import ModelClient

logger = logging.getLogger(__name__)


class AgentSession:
    """Owns prompt boundaries, canonical history, persistence, subscribers, and cancellation.

    One pending message slot for busy-input policy.
    """

    def __init__(
        self,
        *,
        session_id: str,
        session_store: SessionStore,
        model: ModelClient,
        system_prompt: Callable[[], str],
        context_messages: Callable[[], list],
        tool_registry_fn: Callable[[], object],
        active_tool_names_fn: Callable[[], tuple[str, ...]],
    ) -> None:
        self.session_id = session_id
        self._store = session_store
        self._model = model
        self._system_prompt_fn = system_prompt
        self._context_messages_fn = context_messages
        self._tool_registry_fn = tool_registry_fn
        self._active_tool_names_fn = active_tool_names_fn

        self._subscribers: list[LiveEventEmitter] = []
        self._cancel_event = asyncio.Event()
        self._busy = False
        self._turn_count = 0
        self._session_started_emitted = False
        self._pending_message: str | None = None
        self._cleanup_callbacks: list[Callable[[], None]] = []

    def subscribe(self, listener: LiveEventEmitter) -> Callable[[], None]:
        """Subscribe to live events. Returns an unsubscribe function."""
        self._subscribers.append(listener)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def abort(self) -> None:
        """Signal cancellation to the active turn. Returns the session to idle."""
        self._cancel_event.set()

    def _emit(self, event: LiveEvent) -> None:
        """Emit to all subscribers. Subscriber failures are collected and logged."""
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception as exc:
                logger.warning("session subscriber error: %s", exc)

    def add_cleanup(self, callback: Callable[[], None]) -> None:
        """Register a cleanup callback called by close(). Domain-neutral."""
        self._cleanup_callbacks.append(callback)

    def close(self) -> None:
        """Close the session store and run cleanup callbacks."""
        for cb in self._cleanup_callbacks:
            try:
                cb()
            except Exception:
                pass
        self._cleanup_callbacks.clear()
        self._store.close()

    async def prompt(self, text: str) -> TurnResult:
        """Submit user text for a new turn. Queues if busy.

        Returns the TurnResult when the turn settles.
        """
        if self._busy:
            # Busy: replace pending message
            old = self._pending_message
            self._pending_message = text
            if old is not None:
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id="",
                        event_type=LiveEventType.USER_MESSAGE_ACCEPTED,
                        text="Pending message replaced",
                    )
                )
            # Return a truthful typed result — not interrupted
            return TurnResult(
                turn_id="",
                exit_reason=TurnExitReason.QUEUED,
                safe_failure="session busy, message queued",
            )

        return await self._run_turn(text)

    async def _run_turn(self, text: str) -> TurnResult:
        """Execute one conversational turn."""
        self._busy = True
        turn_id = _tid()
        self._turn_count += 1

        # Emit SESSION_STARTED exactly once, on the first turn
        if not self._session_started_emitted:
            self._session_started_emitted = True
            self._emit(
                LiveEvent(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.SESSION_STARTED,
                )
            )

        try:
            # Persist user message before any provider call
            user_msg = UserMessage(
                message_id=_mid(),
                turn_id=turn_id,
                content=text,
            )
            self._store.append_message(self.session_id, user_msg)

            self._emit(
                LiveEvent(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.USER_MESSAGE_ACCEPTED,
                    text=text,
                )
            )

            # ── Honour any abort set before the turn started ──
            # _cancel_event.clear() is delayed until after persistence so an abort
            # delivered between prompt scheduling and _run_turn start is seen.
            was_aborted = self._cancel_event.is_set()
            self._cancel_event.clear()
            if was_aborted:
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_INTERRUPTED,
                    )
                )
                self._store.mark_turn_settled(self.session_id, self._turn_count)
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.SESSION_SETTLED,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.INTERRUPTED,
                    safe_failure="aborted before model call",
                )

            # Get current system prompt, context, and tools
            try:
                system_prompt = self._system_prompt_fn()
                context_msgs = self._context_messages_fn()
                tool_registry = self._tool_registry_fn()
                active_tool_names = self._active_tool_names_fn()
            except Exception as exc:
                logger.error("host/context setup failed: %s", exc)
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error="Host or context setup failed",
                    )
                )
                self._store.mark_turn_settled(self.session_id, self._turn_count)
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.SESSION_SETTLED,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.MODEL_FAILED,
                    safe_failure=f"host/context setup: {exc}",
                )

            # Load canonical history
            stored = self._store.load_messages(self.session_id)
            try:
                history = _parse_canonical_history(stored)
            except CanonicalParseError as exc:
                logger.error("canonical parse error: %s", exc)
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=f"Session history corrupted: {exc}",
                    )
                )
                self._store.mark_turn_settled(self.session_id, self._turn_count)
                self._emit(
                    LiveEvent(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.SESSION_SETTLED,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.MODEL_FAILED,
                    safe_failure=f"canonical parse: {exc}",
                )

            # Run turn
            result = await run_turn(
                session_id=self.session_id,
                turn_id=turn_id,
                model=self._model,
                system_prompt=system_prompt,
                context_messages=context_msgs,
                history=history,
                tool_registry=tool_registry,
                active_tools=active_tool_names,
                cancel_event=self._cancel_event,
                emit=self._emit,
            )

            # Persist new messages
            for msg in result.new_messages:
                self._store.append_message(self.session_id, msg)

            # Mark turn settled
            self._store.mark_turn_settled(self.session_id, self._turn_count)

            # Emit session_settled
            self._emit(
                LiveEvent(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.SESSION_SETTLED,
                )
            )

            return result

        finally:
            # Process pending message if any — keep _busy=True across the chain
            pending = self._pending_message
            self._pending_message = None
            if pending is not None:
                task = asyncio.create_task(self._run_turn(pending))

                def _safe_pending_done(t: asyncio.Task) -> None:
                    try:
                        exc = t.exception()
                        if exc is not None:
                            logger.error("pending turn failed: %s", exc)
                    except Exception:
                        pass

                task.add_done_callback(_safe_pending_done)
            else:
                self._busy = False

    @classmethod
    def resume(
        cls,
        session_id: str,
        session_store: SessionStore,
        model: ModelClient,
        system_prompt: Callable[[], str],
        context_messages: Callable[[], list],
        tool_registry_fn: Callable[[], object],
        active_tool_names_fn: Callable[[], tuple[str, ...]],
    ) -> AgentSession:
        """Resume an existing session by session_id."""
        existing = session_store.get_session(session_id)
        if existing is None:
            raise ValueError(f"Session not found: {session_id}")

        session = cls(
            session_id=session_id,
            session_store=session_store,
            model=model,
            system_prompt=system_prompt,
            context_messages=context_messages,
            tool_registry_fn=tool_registry_fn,
            active_tool_names_fn=active_tool_names_fn,
        )
        # Restore turn count
        session._turn_count = existing.get("turn_count", 0)
        return session


def _tid() -> str:
    return uuid.uuid4().hex[:12]


def _mid() -> str:
    return uuid.uuid4().hex[:12]


class CanonicalParseError(Exception):
    """Raised when stored session messages cannot be parsed."""


def _parse_canonical_history(
    stored: list[dict],
) -> list[ConversationMessage]:
    """Parse stored messages back into ConversationMessage objects.

    Raises CanonicalParseError on any corrupt message instead of silently dropping.
    """
    from haxjobs.agent_core.messages import (
        AssistantMessage,
        ToolCallMessage,
        ToolResultMessage,
        UserMessage,
    )

    result: list[ConversationMessage] = []
    for row in stored:
        payload = row.get("payload_json", {})
        kind = payload.get("kind", "")
        try:
            if kind == "user":
                result.append(UserMessage.model_validate(payload))
            elif kind == "assistant":
                result.append(AssistantMessage.model_validate(payload))
            elif kind == "tool_call":
                result.append(ToolCallMessage.model_validate(payload))
            elif kind == "tool_result":
                result.append(ToolResultMessage.model_validate(payload))
            else:
                raise CanonicalParseError(
                    f"Unknown message kind '{kind}' at sequence {row.get('sequence', '?')}"
                )
        except CanonicalParseError:
            raise
        except Exception as exc:
            raise CanonicalParseError(
                f"Failed to parse kind={kind} at sequence {row.get('sequence', '?')}: {exc}"
            ) from exc
    return result
