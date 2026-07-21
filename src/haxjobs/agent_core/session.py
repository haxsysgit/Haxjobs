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
        self._pending_message: str | None = None

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
                        text=f"Pending message replaced",
                    )
                )
            # Return a placeholder — caller should handle busy state
            return TurnResult(
                turn_id="",
                exit_reason=TurnExitReason.INTERRUPTED,
                safe_failure="session busy, message queued",
            )

        return await self._run_turn(text)

    async def _run_turn(self, text: str) -> TurnResult:
        """Execute one conversational turn."""
        self._busy = True
        self._cancel_event.clear()
        turn_id = _tid()
        self._turn_count += 1

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

            # Get current system prompt, context, and tools
            system_prompt = self._system_prompt_fn()
            context_msgs = self._context_messages_fn()
            tool_registry = self._tool_registry_fn()
            active_tool_names = self._active_tool_names_fn()

            # Load canonical history
            stored = self._store.load_messages(self.session_id)
            history = _parse_canonical_history(stored)

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
            self._busy = False

            # Process pending message if any
            pending = self._pending_message
            self._pending_message = None
            if pending is not None:
                # Run the pending message asynchronously
                # but don't await it (to avoid re-entrancy issues)
                asyncio.create_task(self._run_turn(pending))

    @classmethod
    async def resume(
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


def _parse_canonical_history(
    stored: list[dict],
) -> list[ConversationMessage]:
    """Parse stored messages back into ConversationMessage objects."""
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
        except Exception as exc:
            logger.warning("failed to parse stored message kind=%s: %s", kind, exc)
    return result
