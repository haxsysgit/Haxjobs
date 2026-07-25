"""Bounded streaming turn runtime — domain-free model and tool loop.

Responsibilities:
- Stream model responses and handle text/tool-call events
- Dispatch tools through the ToolRegistry with cancellation safety
- Persist canonical messages at durable boundaries (tool-call before handler,
  tool-result after handler)
- Emit live events for each lifecycle transition
- Return a TurnResult with safe, content-free failure text

Does NOT:
- Own session state, history, or measurement (AgentSession in session.py owns those)
- Know about employment/career data
- Handle message projection (messages.py owns that)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from haxjobs.agent_core.errors import normalize_tool_code, safe_error, safe_tool_error
from haxjobs.agent_core.live_events import LiveEvent, LiveEventEmitter, LiveEventType
from haxjobs.agent_core.messages import (
    AssistantMessage,
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
    project_messages,
)
from haxjobs.agent_core.tools import ToolExecutionContext, ToolRegistry
from haxjobs.model.client import ModelClient
from haxjobs.model.types import (
    ModelMessage,
    ModelRequest,
    ModelStreamEvent,
    ModelStreamEventType,
    ModelUsage,
    ToolSchema,
)

logger = logging.getLogger(__name__)

_MAX_MODEL_STEPS = 5

PersistCallback = Callable[[ConversationMessage], None]


class TurnExitReason(str, Enum):
    COMPLETED = "completed"
    MODEL_FAILED = "model_failed"
    LIMIT_REACHED = "limit_reached"
    INTERRUPTED = "interrupted"
    QUEUED = "queued"
    PERSISTENCE_FAILED = "persistence_failed"


@dataclass
class TurnResult:
    """Result of one conversational turn — domain-free."""

    turn_id: str
    exit_reason: TurnExitReason
    final_text: str = ""
    model_steps: int = 0
    tool_starts: int = 0
    new_messages: list[ConversationMessage] = field(default_factory=list)
    safe_failure: str = ""
    user_message_id: str = ""
    model_name: str = ""
    provider_name: str = ""
    usage: ModelUsage | None = None
    input_characters: int = 0


class _TurnResultBuilder:
    """Mutable accumulator — call .build() to get the frozen TurnResult."""

    def __init__(self, turn_id: str, user_message_id: str):
        self.turn_id = turn_id
        self.user_message_id = user_message_id
        self.exit_reason = TurnExitReason.COMPLETED
        self.final_text = ""
        self.model_steps = 0
        self.tool_starts = 0
        self.new_messages: list[ConversationMessage] = []
        self.safe_failure = ""
        self.model_name = ""
        self.provider_name = ""
        self.usage: ModelUsage | None = None
        self.input_characters = 0

    def build(self) -> TurnResult:
        return TurnResult(
            turn_id=self.turn_id,
            exit_reason=self.exit_reason,
            final_text=self.final_text,
            model_steps=self.model_steps,
            tool_starts=self.tool_starts,
            new_messages=list(self.new_messages),
            safe_failure=self.safe_failure,
            user_message_id=self.user_message_id,
            model_name=self.model_name,
            provider_name=self.provider_name,
            usage=self.usage,
            input_characters=self.input_characters,
        )

    def mark_failed(self, reason: TurnExitReason, failure_key: str) -> None:
        self.exit_reason = reason
        self.safe_failure = safe_error(failure_key)

    def mark_interrupted(self) -> None:
        self.exit_reason = TurnExitReason.INTERRUPTED
        self.safe_failure = safe_error("interrupted")


async def run_turn(
    *,
    session_id: str,
    turn_id: str,
    model: ModelClient,
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
    tool_registry: ToolRegistry,
    active_tools: tuple[str, ...],
    cancel_event: asyncio.Event,
    emit: LiveEventEmitter,
    persist_message: PersistCallback,
    user_message_id: str,
    max_model_steps: int = 5,
) -> TurnResult:
    """Execute one conversational turn — streaming model and tool loop.

    Returns a TurnResult regardless of outcome.
    persist_message is called for every ToolCallMessage (before handler),
    ToolResultMessage (after handler), and AssistantMessage.
    """
    max_steps = min(max(max_model_steps, 1), _MAX_MODEL_STEPS)
    new_messages: list[ConversationMessage] = []
    model_steps = 0
    tool_starts = 0

    builder = _TurnResultBuilder(turn_id=turn_id, user_message_id=user_message_id)

    # Compute projected input characters
    provider_messages_initial: list[ModelMessage] = project_messages(
        system_prompt=system_prompt,
        context_messages=context_messages,
        history=history,
    )
    builder.input_characters = sum(len(m.content or "") for m in provider_messages_initial)

    emit(
        LiveEvent(
            session_id=session_id,
            turn_id=turn_id,
            event_type=LiveEventType.TURN_STARTED,
        )
    )

    # Build tool schemas once
    tool_schemas: list[ToolSchema] = []
    if active_tools:
        try:
            tool_schemas = tool_registry.active_schemas(active_tools)
        except ValueError as exc:
            logger.warning("active tool schema setup failed: %s", exc, exc_info=True)
            builder.mark_failed(TurnExitReason.MODEL_FAILED, "tool_schema")
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=builder.safe_failure,
                )
            )
            return builder.build()

    # Build initial provider messages
    provider_messages: list[ModelMessage] = provider_messages_initial

    # ── Main loop ──
    while model_steps < max_steps:
        if cancel_event.is_set():
            builder.mark_interrupted()
            break

        model_steps += 1
        accumulated_text = ""
        model_failed = False
        tool_call_events: list[ModelStreamEvent] = []
        finish_reason = ""

        # Build model request
        model_request = ModelRequest(
            messages=list(provider_messages),
            max_tokens=4096,
            tools=list(tool_schemas),
        )

        # Stream from model
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.ASSISTANT_STARTED,
            )
        )

        try:
            async for stream_event in model.stream(model_request, cancel_event):
                # Task.cancel() is independent of the cooperative event. A
                # provider may catch CancelledError and still yield a terminal
                # event, so inspect the task before accepting any event.
                if _task_cancel_requested():
                    cancel_event.set()
                    builder.mark_interrupted()
                    break
                if cancel_event.is_set():
                    builder.mark_interrupted()
                    # Persist partial assistant text before publishing interruption.
                    if accumulated_text:
                        assistant_msg = AssistantMessage(
                            message_id=_mid(),
                            turn_id=turn_id,
                            content=accumulated_text,
                            status="interrupted",
                        )
                        new_messages.append(assistant_msg)
                        if not _persist_partial_assistant(assistant_msg, persist_message):
                            builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                            emit(LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TURN_FAILED,
                                error=builder.safe_failure,
                            ))
                            builder.final_text = accumulated_text
                            builder.model_steps = model_steps
                            builder.tool_starts = tool_starts
                            builder.new_messages = new_messages
                            return builder.build()
                    emit(LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_INTERRUPTED,
                    ))
                    builder.final_text = accumulated_text
                    builder.model_steps = model_steps
                    builder.tool_starts = tool_starts
                    builder.new_messages = new_messages
                    return builder.build()

                if stream_event.event_type == ModelStreamEventType.TEXT_DELTA:
                    accumulated_text += stream_event.delta
                    emit(
                        LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.ASSISTANT_DELTA,
                            delta=stream_event.delta,
                        )
                    )

                elif stream_event.event_type == ModelStreamEventType.COMPLETE_TOOL_CALL:
                    if stream_event.tool_calls_unsafe:
                        # Reject tool calls when model response was truncated.
                        logger.warning(
                            "Rejecting unsafe tool call %s (finish_reason=length)",
                            stream_event.tool_name,
                        )
                        emit(
                            LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TOOL_FAILED,
                                call_id=stream_event.call_id or "",
                                tool_name=stream_event.tool_name,
                                tool_status="unsafe",
                                error_code="tool_calls_unsafe",
                                error="Tool call rejected: response was truncated",
                            )
                        )
                    else:
                        tool_call_events.append(stream_event)
                        emit(
                            LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TOOL_REQUESTED,
                                call_id=stream_event.call_id,
                                tool_name=stream_event.tool_name,
                            )
                        )

                elif stream_event.event_type == ModelStreamEventType.RESPONSE_COMPLETED:
                    if _task_cancel_requested():
                        cancel_event.set()
                        builder.mark_interrupted()
                        break
                    finish_reason = stream_event.finish_reason
                    builder.usage = stream_event.usage
                    builder.model_name = stream_event.model
                    builder.provider_name = stream_event.provider
                    emit(
                        LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.ASSISTANT_COMPLETED,
                            text=accumulated_text,
                        )
                    )
                    break

                elif stream_event.event_type == ModelStreamEventType.RESPONSE_FAILED:
                    if stream_event.category == "cancelled":
                        # Providers may consume asyncio.CancelledError and
                        # normalize it to this provider-neutral failure event.
                        # It is still cancellation, not a model failure.
                        builder.mark_interrupted()
                        if accumulated_text:
                            assistant_msg = AssistantMessage(
                                message_id=_mid(),
                                turn_id=turn_id,
                                content=accumulated_text,
                                status="interrupted",
                            )
                            new_messages.append(assistant_msg)
                            if not _persist_partial_assistant(assistant_msg, persist_message):
                                builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                                emit(LiveEvent(
                                    session_id=session_id,
                                    turn_id=turn_id,
                                    event_type=LiveEventType.TURN_FAILED,
                                    error=builder.safe_failure,
                                ))
                                builder.final_text = accumulated_text
                                builder.model_steps = model_steps
                                builder.tool_starts = tool_starts
                                builder.new_messages = new_messages
                                return builder.build()
                        emit(
                            LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TURN_INTERRUPTED,
                            )
                        )
                        builder.final_text = accumulated_text
                        builder.model_steps = model_steps
                        builder.tool_starts = tool_starts
                        builder.new_messages = new_messages
                        return builder.build()

                    model_failed = True
                    builder.mark_failed(TurnExitReason.MODEL_FAILED, "model")
                    # Persist partial assistant text. A failed write changes the
                    # turn outcome; it is not an interrupted/model-only failure.
                    if accumulated_text:
                        assistant_msg = AssistantMessage(
                            message_id=_mid(),
                            turn_id=turn_id,
                            content=accumulated_text,
                            status="failed",
                        )
                        new_messages.append(assistant_msg)
                        if not _persist_partial_assistant(assistant_msg, persist_message):
                            builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                            emit(LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TURN_FAILED,
                                error=builder.safe_failure,
                            ))
                            builder.final_text = accumulated_text
                            builder.model_steps = model_steps
                            builder.tool_starts = tool_starts
                            builder.new_messages = new_messages
                            return builder.build()
                    break
        except asyncio.CancelledError:
            # External task cancellation can interrupt the provider iterator
            # without giving it a chance to observe cancel_event. Preserve only
            # text that was actually received, and mark it interrupted rather
            # than manufacturing a completed response.
            if accumulated_text:
                assistant_msg = AssistantMessage(
                    message_id=_mid(),
                    turn_id=turn_id,
                    content=accumulated_text,
                    status="interrupted",
                )
                new_messages.append(assistant_msg)
                if not _persist_partial_assistant(assistant_msg, persist_message):
                    builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                    emit(LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=builder.safe_failure,
                    ))
                    builder.final_text = accumulated_text
                    builder.model_steps = model_steps
                    builder.tool_starts = tool_starts
                    builder.new_messages = new_messages
                    return builder.build()
            builder.mark_interrupted()
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                )
            )
            builder.final_text = accumulated_text
            builder.model_steps = model_steps
            builder.tool_starts = tool_starts
            builder.new_messages = new_messages
            return builder.build()
        except Exception as exc:
            logger.warning("model stream failed: %s", exc, exc_info=True)
            model_failed = True
            builder.mark_failed(TurnExitReason.MODEL_FAILED, "model")
            break

        # A provider can consume external task cancellation and make its
        # iterator appear successful. Preserve only partial text and stop
        # before assistant completion or tool effects.
        if builder.exit_reason == TurnExitReason.INTERRUPTED:
            if accumulated_text:
                assistant_msg = AssistantMessage(
                    message_id=_mid(),
                    turn_id=turn_id,
                    content=accumulated_text,
                    status="interrupted",
                )
                new_messages.append(assistant_msg)
                if not _persist_partial_assistant(assistant_msg, persist_message):
                    builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                    emit(LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=builder.safe_failure,
                    ))
                    builder.final_text = accumulated_text
                    builder.model_steps = model_steps
                    builder.tool_starts = tool_starts
                    builder.new_messages = new_messages
                    return builder.build()
            builder.safe_failure = builder.safe_failure or safe_error("interrupted")
            emit(LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_INTERRUPTED,
            ))
            builder.final_text = accumulated_text
            builder.model_steps = model_steps
            builder.tool_starts = tool_starts
            builder.new_messages = new_messages
            return builder.build()

        if model_failed:
            break

        # ── No tool calls: turn complete ──
        if not tool_call_events:
            builder.exit_reason = TurnExitReason.COMPLETED

            # Persist assistant message
            assistant_msg = AssistantMessage(
                message_id=_mid(),
                turn_id=turn_id,
                content=accumulated_text,
                status="complete",
            )
            new_messages.append(assistant_msg)
            try:
                persist_message(assistant_msg)
            except Exception:
                builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=builder.safe_failure,
                    )
                )
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts
                builder.new_messages = new_messages
                return builder.build()

            # Append to provider messages for potential next step
            provider_messages.append(
                ModelMessage(role="assistant", content=accumulated_text)
            )
            break

        # ── Has tool calls: process them ──
        # First, persist the assistant message with tool calls
        assistant_msg = AssistantMessage(
            message_id=_mid(),
            turn_id=turn_id,
            content=accumulated_text,
            status="complete",
        )
        new_messages.append(assistant_msg)
        try:
            persist_message(assistant_msg)
        except Exception:
            builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=builder.safe_failure,
                )
            )
            builder.final_text = accumulated_text
            builder.model_steps = model_steps
            builder.tool_starts = tool_starts
            builder.new_messages = new_messages
            return builder.build()

        # Build provider assistant message with tool calls
        provider_tool_calls: list[dict[str, Any]] = []
        for tc_event in tool_call_events:
            provider_tool_calls.append({
                "id": tc_event.call_id,
                "type": "function",
                "function": {
                    "name": tc_event.tool_name,
                    "arguments": tc_event.arguments,
                },
            })

        provider_messages.append(
            ModelMessage(
                role="assistant",
                content=accumulated_text,
                tool_calls=provider_tool_calls,
            )
        )

        # Dispatch each tool call
        for tc_event in tool_call_events:
            if cancel_event.is_set():
                builder.mark_interrupted()
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_INTERRUPTED,
                    )
                )
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts
                builder.new_messages = new_messages
                return builder.build()

            # Persist canonical tool call message BEFORE handler execution
            tc_msg = ToolCallMessage(
                message_id=_mid(),
                turn_id=turn_id,
                call_id=tc_event.call_id,
                tool_name=tc_event.tool_name,
                arguments=tc_event.arguments,
            )
            new_messages.append(tc_msg)
            try:
                persist_message(tc_msg)
            except Exception:
                builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_call_persistence")
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=builder.safe_failure,
                    )
                )
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts
                builder.new_messages = new_messages
                return builder.build()

            # Emit tool_started
            t_start = time.monotonic()
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TOOL_STARTED,
                    call_id=tc_event.call_id,
                    tool_name=tc_event.tool_name,
                )
            )

            # Build ToolExecutionContext
            ctx = ToolExecutionContext(
                session_id=session_id,
                turn_id=turn_id,
                call_id=tc_event.call_id,
                user_message_id=user_message_id,
                cancel_event=cancel_event,
            )

            # Dispatch tool — with cancellation awareness
            dispatch_task = asyncio.ensure_future(
                tool_registry.dispatch(
                    name=tc_event.tool_name,
                    arguments=tc_event.arguments,
                    active_names=active_tools,
                    context=ctx,
                )
            )
            cancel_task = asyncio.ensure_future(cancel_event.wait())

            # Race dispatch against cancellation
            try:
                done, pending = await asyncio.wait(
                    [dispatch_task, cancel_task],
                    timeout=None,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            except asyncio.CancelledError:
                # External task cancellation must not abandon a handler. A
                # handler can catch task cancellation after committing an
                # effect, so inspect its joined outcome before synthesizing a
                # cancelled result.
                cancel_event.set()
                dispatch_returned, dispatch_result = await _cancel_and_collect(dispatch_task)
                await _cancel_and_join(cancel_task)
                t_duration_ms = (time.monotonic() - t_start) * 1000

                if dispatch_returned and isinstance(dispatch_result, dict):
                    _, persistence_error = _persist_and_emit_tool_result(
                        result=dispatch_result,
                        session_id=session_id,
                        turn_id=turn_id,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        duration_ms=t_duration_ms,
                        new_messages=new_messages,
                        persist_message=persist_message,
                        emit=emit,
                    )
                    if persistence_error:
                        emit(LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.TURN_FAILED,
                            error=persistence_error,
                        ))
                        builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_result_persistence")
                        builder.final_text = accumulated_text
                        builder.model_steps = model_steps
                        builder.tool_starts = tool_starts + 1
                        builder.new_messages = new_messages
                        return builder.build()
                    tool_starts += 1
                else:
                    _, persistence_error = _persist_and_emit_tool_result(
                        result={
                            "ok": False,
                            "code": "cancelled",
                            "error": "tool execution cancelled",
                        },
                        session_id=session_id,
                        turn_id=turn_id,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        duration_ms=t_duration_ms,
                        new_messages=new_messages,
                        persist_message=persist_message,
                        emit=emit,
                    )
                    if persistence_error:
                        builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_result_persistence")
                        builder.final_text = accumulated_text
                        builder.model_steps = model_steps
                        builder.tool_starts = tool_starts + 1
                        builder.new_messages = new_messages
                        return builder.build()
                    tool_starts += 1
                    provider_messages.append(
                        ModelMessage(
                            role="tool",
                            content=json.dumps({"ok": False, "code": "cancelled", "error": "tool execution cancelled"}, default=str),
                            tool_call_id=tc_event.call_id,
                        )
                    )

                builder.mark_interrupted()
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                ))
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts
                builder.new_messages = new_messages
                return builder.build()

            if dispatch_task not in done:
                # Cancellation wins the race, but the cancelled handler may
                # catch CancelledError and return after committing an effect.
                dispatch_returned, dispatch_result = await _cancel_and_collect(dispatch_task)
                if cancel_task in pending:
                    await _cancel_and_join(cancel_task)
                t_duration_ms = (time.monotonic() - t_start) * 1000

                if dispatch_returned and isinstance(dispatch_result, dict):
                    _, persistence_error = _persist_and_emit_tool_result(
                        result=dispatch_result,
                        session_id=session_id,
                        turn_id=turn_id,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        duration_ms=t_duration_ms,
                        new_messages=new_messages,
                        persist_message=persist_message,
                        emit=emit,
                    )
                    if persistence_error:
                        emit(LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.TURN_FAILED,
                            error=persistence_error,
                        ))
                        builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_result_persistence")
                        builder.final_text = accumulated_text
                        builder.model_steps = model_steps
                        builder.tool_starts = tool_starts + 1
                        builder.new_messages = new_messages
                        return builder.build()
                    tool_starts += 1
                    builder.mark_interrupted()
                else:
                    cancelled_result = {
                        "ok": False,
                        "code": "cancelled",
                        "error": "tool execution cancelled",
                    }
                    _, persistence_error = _persist_and_emit_tool_result(
                        result=cancelled_result,
                        session_id=session_id,
                        turn_id=turn_id,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        duration_ms=t_duration_ms,
                        new_messages=new_messages,
                        persist_message=persist_message,
                        emit=emit,
                    )
                    if persistence_error:
                        builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_result_persistence")
                        builder.final_text = accumulated_text
                        builder.model_steps = model_steps
                        builder.tool_starts = tool_starts + 1
                        builder.new_messages = new_messages
                        return builder.build()
                    tool_starts += 1
                    provider_messages.append(
                        ModelMessage(
                            role="tool",
                            content=json.dumps(cancelled_result, default=str),
                            tool_call_id=tc_event.call_id,
                        )
                    )

                builder.mark_interrupted()
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                ))
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts
                builder.new_messages = new_messages
                return builder.build()

            # Cancel the cancel waiter — dispatch completed normally
            await _cancel_and_join(cancel_task)

            result = _normalize_tool_result(await dispatch_task)
            t_duration_ms = (time.monotonic() - t_start) * 1000

            # Persist the canonical result before publishing lifecycle state.
            # A handler result is not a completed tool until this boundary holds.
            _, persistence_error = _persist_and_emit_tool_result(
                result=result,
                session_id=session_id,
                turn_id=turn_id,
                call_id=tc_event.call_id,
                tool_name=tc_event.tool_name,
                duration_ms=t_duration_ms,
                new_messages=new_messages,
                persist_message=persist_message,
                emit=emit,
            )
            if persistence_error:
                # The ToolCallMessage remains dangling and will reconcile to
                # unknown_outcome on resume. Never publish a false result event.
                builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "tool_result_persistence")
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=builder.safe_failure,
                ))
                builder.final_text = accumulated_text
                builder.model_steps = model_steps
                builder.tool_starts = tool_starts + 1
                builder.new_messages = new_messages
                return builder.build()

            tool_starts += 1

            # Append to provider messages
            provider_messages.append(
                ModelMessage(
                    role="tool",
                    content=json.dumps(result, default=str),
                    tool_call_id=tc_event.call_id,
                )
            )

    else:
        # Loop completed without explicit stop → limit reached
        builder.mark_failed(TurnExitReason.LIMIT_REACHED, "limit")
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_FAILED,
                error=builder.safe_failure,
            )
        )

    # ── Emit final event ──
    if builder.exit_reason == TurnExitReason.COMPLETED:
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_COMPLETED,
            )
        )
    elif builder.exit_reason == TurnExitReason.INTERRUPTED:
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_INTERRUPTED,
            )
        )
    elif builder.exit_reason in (TurnExitReason.MODEL_FAILED,):
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_FAILED,
                error=builder.safe_failure,
            )
        )

    builder.final_text = accumulated_text if 'accumulated_text' in dir() else ""
    builder.model_steps = model_steps
    builder.tool_starts = tool_starts
    builder.new_messages = new_messages
    return builder.build()


def _persist_and_emit_tool_result(
    *,
    result: dict[str, Any],
    session_id: str,
    turn_id: str,
    call_id: str,
    tool_name: str,
    duration_ms: float,
    new_messages: list[ConversationMessage],
    persist_message: PersistCallback,
    emit: LiveEventEmitter,
) -> tuple[ToolResultMessage | None, str]:
    """Persist a tool outcome, then publish its truthful lifecycle event."""
    result = _normalize_tool_result(result)
    ok = result.get("ok", False)
    code = result.get("code", "tool_failed")
    tr_msg = ToolResultMessage(
        message_id=_mid(),
        turn_id=turn_id,
        call_id=call_id,
        tool_name=tool_name,
        ok=ok,
        result=result.get("data"),
        error_code=code if not ok else None,
        error=safe_tool_error(code) if not ok else None,
    )
    new_messages.append(tr_msg)
    try:
        persist_message(tr_msg)
    except Exception:
        error = safe_error("tool_result_persistence")
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TOOL_FAILED,
                call_id=call_id,
                tool_name=tool_name,
                tool_status="persistence_failed",
                tool_duration_ms=duration_ms,
                error_code="persistence_failed",
                error=error,
            )
        )
        return None, error

    if result.get("ok"):
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TOOL_COMPLETED,
                call_id=call_id,
                tool_name=tool_name,
                tool_status="ok",
                tool_duration_ms=duration_ms,
            )
        )
    else:
        code = result.get("code", "tool_failed")
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TOOL_FAILED,
                call_id=call_id,
                tool_name=tool_name,
                tool_status=code,
                tool_duration_ms=duration_ms,
                error_code=code,
                error=safe_tool_error(code),
            )
        )
    return tr_msg, ""


def _normalize_tool_result(result: Any) -> dict[str, Any]:
    """Keep handler-controlled result metadata inside the safe vocabulary."""
    if not isinstance(result, dict):
        return {
            "ok": False,
            "code": "tool_failed",
            "error": safe_tool_error("tool_failed"),
        }
    if result.get("ok") is True:
        return {"ok": True, "data": result.get("data")}
    code = normalize_tool_code(result.get("code"))
    return {
        "ok": False,
        "code": code,
        "error": safe_tool_error(code),
    }


def _persist_partial_assistant(
    message: AssistantMessage, persist_message: PersistCallback
) -> bool:
    """Persist partial text and report failure without exposing exception text."""
    try:
        persist_message(message)
    except Exception as exc:
        logger.warning("partial assistant persistence failed: %s", exc)
        return False
    return True


async def _cancel_and_collect(task: asyncio.Task) -> tuple[bool, Any]:
    """Cancel a child and report whether it returned a real outcome."""
    if not task.done():
        task.cancel()
    try:
        return True, await task
    except asyncio.CancelledError:
        return False, None
    except Exception as exc:
        logger.debug("cancelled child task ended with error: %s", exc)
        return False, None


async def _cancel_and_join(task: asyncio.Task) -> None:
    """Cancel one child task and deliberately consume its cancellation."""
    if not task.done():
        task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.debug("cancelled child task ended with error: %s", exc)


def _task_cancel_requested() -> bool:
    """Return whether the current task has an external cancellation pending."""
    task = asyncio.current_task()
    return task is not None and task.cancelling() > 0


def _mid() -> str:
    """Generate a short unique message ID."""
    return uuid.uuid4().hex[:12]
