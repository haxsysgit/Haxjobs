"""Agent session — owns interaction boundaries, persistence, resume, subscribers, cancellation.

Plan 003 Phase 7: The session persists canonical messages, manages busy-input policy,
and orchestrates turns through the turn runtime.

Plan 004: persist_message callback, dangling call detection, measurement recording,
session configuration validation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from haxjobs.agent_core.errors import safe_error
from haxjobs.agent_core.live_events import LiveEvent, LiveEventEmitter, LiveEventType
from haxjobs.agent_core.messages import (
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
)
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.turn import TurnExitReason, TurnResult, run_turn
from haxjobs.model.client import ModelClient

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        self._cancel_event: asyncio.Event | None = None
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
        """Signal cancellation to the currently busy turn. No-op when idle.

        Each turn gets a fresh asyncio.Event. Idle Escape never poisons the next turn.
        """
        if self._cancel_event is not None:
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

        When idle the calling task owns a serial loop that runs the current turn
        and every pending successor. No detached asyncio.create_task is spawned
        inside AgentSession.

        The original owner prompt returns the result of the **last** turn in the
        chain (deterministic: the final turn before all pending work is exhausted).
        Secondary prompt calls while busy return QUEUED immediately.
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

        # Idle: become the owner and run a serial chain
        self._busy = True
        self._pending_message = text
        try:
            return await self._run_serial_loop()
        finally:
            self._busy = False

    async def _run_serial_loop(self) -> TurnResult:
        """Run turns serially until no pending work remains.

        Each iteration gets a fresh asyncio.Event so idle abort never poisons
        the next turn. The original prompt task owns the entire chain.
        """
        last_result: TurnResult | None = None
        while self._pending_message is not None:
            text = self._pending_message
            self._pending_message = None
            self._cancel_event = asyncio.Event()
            try:
                last_result = await self._run_turn(text)
            except Exception as exc:
                # Never let an orchestration/read failure fall through to the
                # synthetic COMPLETED result below.
                logger.exception("_run_turn unexpected error: %s", exc)
                failure = safe_error("turn")
                self._emit(LiveEvent(
                    session_id=self.session_id,
                    turn_id="",
                    event_type=LiveEventType.TURN_FAILED,
                    error=failure,
                ))
                last_result = TurnResult(
                    turn_id="",
                    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                    safe_failure=failure,
                )
            finally:
                self._cancel_event = None
        if last_result is None:
            last_result = TurnResult(
                turn_id="",
                exit_reason=TurnExitReason.COMPLETED,
            )
        return last_result

    async def _run_turn(self, text: str) -> TurnResult:
        """Execute one conversational turn.

        A fresh cancel_event was already created by _run_serial_loop and is
        stored in self._cancel_event. No was_aborted / clear() dance is needed.
        """
        self._busy = True  # defensive; already True from serial loop
        turn_id = _tid()
        self._turn_count += 1
        started_at = _utcnow()
        started_mono = time.monotonic()

        # Persist user message before any provider call. If this fails, the
        # turn was not accepted and must never enter model execution.
        user_msg = UserMessage(
            message_id=_mid(),
            turn_id=turn_id,
            content=text,
        )
        try:
            self._store.append_message(self.session_id, user_msg)
        except Exception as exc:
            self._turn_count -= 1
            logger.warning("user message persistence failed: %s", exc, exc_info=True)
            safe_failure = safe_error("user_message_persistence")
            return self._settle_failed_turn(
                turn_id=turn_id,
                started_at=started_at,
                started_mono=started_mono,
                safe_failure=safe_failure,
                measurement_reason="user_message_persistence_failed",
                result_reason=TurnExitReason.PERSISTENCE_FAILED,
            )

        # Emit SESSION_STARTED exactly once, after the first user message is
        # durably accepted.
        if not self._session_started_emitted:
            self._session_started_emitted = True
            self._emit(
                LiveEvent(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.SESSION_STARTED,
                )
            )

        self._emit(
            LiveEvent(
                session_id=self.session_id,
                turn_id=turn_id,
                event_type=LiveEventType.USER_MESSAGE_ACCEPTED,
                text=text,
            )
        )

        # Get current system prompt, context, and tools
        try:
            system_prompt = self._system_prompt_fn()
            context_msgs = self._context_messages_fn()
            tool_registry = self._tool_registry_fn()
            active_tool_names = self._active_tool_names_fn()
        except Exception as exc:
            logger.warning("host/context setup failed: %s", exc, exc_info=True)
            safe_failure = safe_error("host_setup")
            return self._settle_failed_turn(
                turn_id=turn_id,
                started_at=started_at,
                started_mono=started_mono,
                safe_failure=safe_failure,
                measurement_reason="host_setup_failure",
            )

        # Load canonical history. A store read failure is a failed turn, never
        # an empty history that can accidentally produce a completion.
        try:
            stored = self._store.load_messages(self.session_id)
        except Exception as exc:
            logger.warning("session history read failed: %s", exc, exc_info=True)
            safe_failure = safe_error("history_read")
            return self._settle_failed_turn(
                turn_id=turn_id,
                started_at=started_at,
                started_mono=started_mono,
                safe_failure=safe_failure,
                measurement_reason="history_read_failure",
            )
        try:
            history = _parse_canonical_history(stored)
        except Exception as exc:
            logger.warning("session history corrupted: %s", exc, exc_info=True)
            safe_failure = safe_error("history_corrupt")
            return self._settle_failed_turn(
                turn_id=turn_id,
                started_at=started_at,
                started_mono=started_mono,
                safe_failure=safe_failure,
                measurement_reason="corrupt_history",
            )

        # Run turn — persist_message passes through to session store
        def _persist_message(msg: ConversationMessage) -> None:
            self._store.append_message(self.session_id, msg)

        def _emit_runtime(event: LiveEvent) -> None:
            # Session owns terminal lifecycle; publish terminal events only
            # after the durable settlement marker succeeds.
            if event.event_type in {
                LiveEventType.TURN_COMPLETED,
                LiveEventType.TURN_FAILED,
                LiveEventType.TURN_INTERRUPTED,
            }:
                return
            self._emit(event)

        try:
            result = await run_turn(
                session_id=self.session_id,
                turn_id=turn_id,
                model=self._model,
                system_prompt=system_prompt,
                context_messages=context_msgs,
                history=history,
                tool_registry=tool_registry,
                active_tools=active_tool_names,
                cancel_event=self._cancel_event,  # type: ignore[arg-type]
                emit=_emit_runtime,
                persist_message=_persist_message,
                user_message_id=user_msg.message_id,
            )
        except asyncio.CancelledError:
            # Cancellation outside the tool wait (for example during model
            # streaming) still gets a durable, content-free settlement.
            if self._cancel_event is not None:
                self._cancel_event.set()
            result = TurnResult(
                turn_id=turn_id,
                exit_reason=TurnExitReason.INTERRUPTED,
                safe_failure=safe_error("interrupted"),
                user_message_id=user_msg.message_id,
            )

        # Record measurement
        self._record_measurement(
            turn_id=turn_id,
            started_at=started_at,
            started_mono=started_mono,
            exit_reason=result.exit_reason.value if isinstance(result.exit_reason, TurnExitReason) else str(result.exit_reason),
            model_name=result.model_name,
            provider_name=result.provider_name,
            model_steps=result.model_steps,
            tool_starts=result.tool_starts,
            input_characters=result.input_characters,
            usage=result.usage,
        )

        # Mark turn settled. If this write fails, canonical messages and the
        # measurement remain durable while the session stays pending for
        # recovery; no completion or SESSION_SETTLED event is published.
        try:
            self._store.mark_turn_settled(self.session_id, self._turn_count)
        except Exception as exc:
            logger.warning("turn settlement persistence failed: %s", exc, exc_info=True)
            settlement_failure = safe_error("settlement")
            # Keep the in-memory counter aligned with the durable counter so
            # the next explicit recovery prompt can settle at the next number
            # rather than skipping the pending turn number.
            self._turn_count -= 1
            self._emit(LiveEvent(
                session_id=self.session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_FAILED,
                error=settlement_failure,
            ))
            from dataclasses import replace
            return replace(
                result,
                exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                safe_failure=settlement_failure,
            )

        # Publish one terminal turn event only after settlement succeeds.
        if result.exit_reason == TurnExitReason.COMPLETED:
            terminal_type = LiveEventType.TURN_COMPLETED
        elif result.exit_reason == TurnExitReason.INTERRUPTED:
            terminal_type = LiveEventType.TURN_INTERRUPTED
        else:
            terminal_type = LiveEventType.TURN_FAILED
        self._emit(LiveEvent(
            session_id=self.session_id,
            turn_id=turn_id,
            event_type=terminal_type,
            error=result.safe_failure if terminal_type == LiveEventType.TURN_FAILED else "",
        ))
        self._emit(LiveEvent(
            session_id=self.session_id,
            turn_id=turn_id,
            event_type=LiveEventType.SESSION_SETTLED,
        ))

        return result

    def _settle_failed_turn(
        self,
        *,
        turn_id: str,
        started_at: str,
        started_mono: float,
        safe_failure: str,
        measurement_reason: str,
        result_reason: TurnExitReason = TurnExitReason.MODEL_FAILED,
    ) -> TurnResult:
        """Emit and persist one truthful failed-turn settlement when possible."""
        self._emit(LiveEvent(
            session_id=self.session_id,
            turn_id=turn_id,
            event_type=LiveEventType.TURN_FAILED,
            error=safe_failure,
        ))
        try:
            self._store.mark_turn_settled(self.session_id, self._turn_count)
        except Exception as exc:
            logger.warning("failed-turn settlement write failed: %s", exc, exc_info=True)
            self._record_measurement(
                turn_id=turn_id,
                started_at=started_at,
                started_mono=started_mono,
                exit_reason=measurement_reason,
            )
            return TurnResult(
                turn_id=turn_id,
                exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                safe_failure=safe_error("settlement"),
            )
        self._record_measurement(
            turn_id=turn_id,
            started_at=started_at,
            started_mono=started_mono,
            exit_reason=measurement_reason,
        )
        self._emit(LiveEvent(
            session_id=self.session_id,
            turn_id=turn_id,
            event_type=LiveEventType.SESSION_SETTLED,
        ))
        return TurnResult(
            turn_id=turn_id,
            exit_reason=result_reason,
            safe_failure=safe_failure,
        )

    def _record_measurement(
        self,
        *,
        turn_id: str,
        started_at: str,
        started_mono: float,
        exit_reason: str,
        model_name: str = "",
        provider_name: str = "",
        model_steps: int = 0,
        tool_starts: int = 0,
        input_characters: int = 0,
        usage=None,
    ) -> None:
        """Record a measurement row. No content columns."""
        finished_at = _utcnow()
        duration_ms = (time.monotonic() - started_mono) * 1000
        try:
            self._store.record_measurement(
                session_id=self.session_id,
                turn_id=turn_id,
                turn_number=self._turn_count,
                started_at=started_at,
                finished_at=finished_at,
                exit_reason=exit_reason,
                model_name=model_name,
                provider_name=provider_name,
                model_steps=model_steps,
                tool_starts=tool_starts,
                input_characters=input_characters,
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
                total_tokens=usage.total_tokens if usage else None,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.warning("measurement recording failed: %s", exc)

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

        # Check for session configuration (Plan 004)
        cfg = session_store.get_session_configuration(session_id)
        if cfg is None:
            raise ValueError(
                f"Session {session_id} has no configuration (created before Plan 004). "
                f"Create a new session with --new."
            )
        # Configuration is opaque to the domain-free core. Employment
        # composition validates its expected scope object before resume.
        if not isinstance(cfg, str) or not cfg.strip():
            raise ValueError(
                f"Session {session_id} has blank configuration; create a new session."
            )

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

        # Detect and resolve dangling calls
        dangling = _detect_dangling_calls(session_store, session_id)
        for tc_msg in dangling:
            # Append a synthetic unknown_outcome result
            tr_msg = ToolResultMessage(
                message_id=_mid(),
                turn_id=tc_msg.turn_id,
                call_id=tc_msg.call_id,
                tool_name=tc_msg.tool_name,
                ok=False,
                result=None,
                error_code="unknown_outcome",
                error="Process terminated before tool completed. Outcome unknown.",
            )
            # Check if result already exists (idempotent)
            existing_results = _find_tool_results(session_store, session_id, tc_msg.call_id)
            if not existing_results:
                session_store.append_message(session_id, tr_msg)

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


def _detect_dangling_calls(
    store: SessionStore, session_id: str
) -> list[ToolCallMessage]:
    """Find unmatched ToolCallMessages (no matching ToolResultMessage)."""
    stored = store.load_messages(session_id)
    calls: dict[str, ToolCallMessage] = {}
    results: set[str] = set()
    for row in stored:
        payload = row.get("payload_json", {})
        if payload.get("kind") == "tool_call":
            call_id = payload.get("call_id", "")
            if call_id:
                try:
                    calls[call_id] = ToolCallMessage.model_validate(payload)
                except Exception:
                    pass
        elif payload.get("kind") == "tool_result":
            call_id = payload.get("call_id", "")
            if call_id:
                results.add(call_id)
    return [c for cid, c in calls.items() if cid not in results]


def _find_tool_results(
    store: SessionStore, session_id: str, call_id: str
) -> list[dict]:
    """Check if a tool result already exists for a given call_id."""
    stored = store.load_messages(session_id)
    return [
        row for row in stored
        if row.get("payload_json", {}).get("kind") == "tool_result"
        and row.get("payload_json", {}).get("call_id") == call_id
    ]
