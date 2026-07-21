"""Bounded streaming turn runtime — domain-free model and tool loop.

Plan 003 Phase 5: Run one conversational turn through the model with streaming,
tool dispatch, live events, and cancellation.

Plan 004: Durable tool execution boundary — persist_message callback, ToolExecutionContext,
user_message_id, TurnResult usage/input_characters.
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
    final_text = ""
    safe_failure = ""
    exit_reason = TurnExitReason.COMPLETED
    model_steps = 0
    tool_starts = 0
    captured_usage: ModelUsage | None = None
    captured_model_name = ""
    captured_provider_name = ""

    # Compute projected input characters
    provider_messages_initial: list[ModelMessage] = project_messages(
        system_prompt=system_prompt,
        context_messages=context_messages,
        history=history,
    )
    input_characters = sum(len(m.content or "") for m in provider_messages_initial)

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
            safe_failure = f"active tool schema setup failed: {exc}"
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=safe_failure,
                )
            )
            return TurnResult(
                turn_id=turn_id,
                exit_reason=TurnExitReason.MODEL_FAILED,
                safe_failure=safe_failure,
                user_message_id=user_message_id,
                input_characters=input_characters,
            )

    # Build initial provider messages
    provider_messages: list[ModelMessage] = provider_messages_initial

    # ── Main loop ──
    while model_steps < max_steps:
        if cancel_event.is_set():
            exit_reason = TurnExitReason.INTERRUPTED
            safe_failure = "interrupted before model call"
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
                if cancel_event.is_set():
                    exit_reason = TurnExitReason.INTERRUPTED
                    safe_failure = "interrupted during streaming"
                    emit(
                        LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.TURN_INTERRUPTED,
                        )
                    )
                    # Persist partial assistant text
                    if accumulated_text:
                        assistant_msg = AssistantMessage(
                            message_id=_mid(),
                            turn_id=turn_id,
                            content=accumulated_text,
                            status="interrupted",
                        )
                        new_messages.append(assistant_msg)
                        try:
                            persist_message(assistant_msg)
                        except Exception:
                            pass  # best-effort on interrupt
                    return TurnResult(
                        turn_id=turn_id,
                        exit_reason=exit_reason,
                        final_text=accumulated_text,
                        model_steps=model_steps,
                        tool_starts=tool_starts,
                        new_messages=new_messages,
                        safe_failure=safe_failure,
                        user_message_id=user_message_id,
                        model_name=captured_model_name,
                        provider_name=captured_provider_name,
                        usage=captured_usage,
                        input_characters=input_characters,
                    )

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
                    finish_reason = stream_event.finish_reason
                    captured_usage = stream_event.usage
                    captured_model_name = stream_event.model
                    captured_provider_name = stream_event.provider
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
                    final_text = accumulated_text
                    if stream_event.category == "cancelled":
                        # Providers may consume asyncio.CancelledError and
                        # normalize it to this provider-neutral failure event.
                        # It is still cancellation, not a model failure.
                        exit_reason = TurnExitReason.INTERRUPTED
                        safe_failure = stream_event.error or "interrupted during streaming"
                        if accumulated_text:
                            assistant_msg = AssistantMessage(
                                message_id=_mid(),
                                turn_id=turn_id,
                                content=accumulated_text,
                                status="interrupted",
                            )
                            new_messages.append(assistant_msg)
                            try:
                                persist_message(assistant_msg)
                            except Exception as exc:
                                logger.warning(
                                    "partial assistant persistence failed: %s", exc
                                )
                        emit(
                            LiveEvent(
                                session_id=session_id,
                                turn_id=turn_id,
                                event_type=LiveEventType.TURN_INTERRUPTED,
                            )
                        )
                        return TurnResult(
                            turn_id=turn_id,
                            exit_reason=exit_reason,
                            final_text=final_text,
                            model_steps=model_steps,
                            tool_starts=tool_starts,
                            new_messages=new_messages,
                            safe_failure=safe_failure,
                            user_message_id=user_message_id,
                            model_name=captured_model_name,
                            provider_name=captured_provider_name,
                            usage=captured_usage,
                            input_characters=input_characters,
                        )

                    model_failed = True
                    safe_failure = stream_event.error or "model stream failed"
                    exit_reason = TurnExitReason.MODEL_FAILED
                    # Persist partial assistant text
                    if accumulated_text:
                        assistant_msg = AssistantMessage(
                            message_id=_mid(),
                            turn_id=turn_id,
                            content=accumulated_text,
                            status="failed",
                        )
                        new_messages.append(assistant_msg)
                        try:
                            persist_message(assistant_msg)
                        except Exception:
                            pass
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
                try:
                    persist_message(assistant_msg)
                except Exception as exc:
                    logger.warning("partial assistant persistence failed: %s", exc)
            safe_failure = "externally cancelled during streaming"
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                )
            )
            return TurnResult(
                turn_id=turn_id,
                exit_reason=TurnExitReason.INTERRUPTED,
                final_text=accumulated_text,
                model_steps=model_steps,
                tool_starts=tool_starts,
                new_messages=new_messages,
                safe_failure=safe_failure,
                user_message_id=user_message_id,
                model_name=captured_model_name,
                provider_name=captured_provider_name,
                usage=captured_usage,
                input_characters=input_characters,
            )
        except Exception as exc:
            model_failed = True
            safe_failure = str(exc)
            exit_reason = TurnExitReason.MODEL_FAILED
            break

        if model_failed:
            break

        # ── No tool calls: turn complete ──
        if not tool_call_events:
            final_text = accumulated_text
            exit_reason = TurnExitReason.COMPLETED

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
                safe_failure = "assistant message persistence failed"
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=safe_failure,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

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
            safe_failure = "assistant message persistence failed"
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=safe_failure,
                )
            )
            return TurnResult(
                turn_id=turn_id,
                exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                final_text=accumulated_text,
                model_steps=model_steps,
                tool_starts=tool_starts,
                new_messages=new_messages,
                safe_failure=safe_failure,
                user_message_id=user_message_id,
                model_name=captured_model_name,
                provider_name=captured_provider_name,
                usage=captured_usage,
                input_characters=input_characters,
            )

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
                exit_reason = TurnExitReason.INTERRUPTED
                safe_failure = "interrupted before tool dispatch"
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_INTERRUPTED,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=exit_reason,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

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
                safe_failure = "tool call persistence failed"
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TURN_FAILED,
                        error=safe_failure,
                    )
                )
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

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
                        return TurnResult(
                            turn_id=turn_id,
                            exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                            final_text=accumulated_text,
                            model_steps=model_steps,
                            tool_starts=tool_starts + 1,
                            new_messages=new_messages,
                            safe_failure=persistence_error,
                            user_message_id=user_message_id,
                            model_name=captured_model_name,
                            provider_name=captured_provider_name,
                            usage=captured_usage,
                            input_characters=input_characters,
                        )
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
                        safe_failure = persistence_error
                    tool_starts += 1

                safe_failure = safe_failure or "externally cancelled during tool execution"
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                ))
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.INTERRUPTED,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

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
                        return TurnResult(
                            turn_id=turn_id,
                            exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                            final_text=accumulated_text,
                            model_steps=model_steps,
                            tool_starts=tool_starts + 1,
                            new_messages=new_messages,
                            safe_failure=persistence_error,
                            user_message_id=user_message_id,
                            model_name=captured_model_name,
                            provider_name=captured_provider_name,
                            usage=captured_usage,
                            input_characters=input_characters,
                        )
                    tool_starts += 1
                    safe_failure = "interrupted after tool completed"
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
                        safe_failure = persistence_error
                    tool_starts += 1
                    provider_messages.append(
                        ModelMessage(
                            role="tool",
                            content=json.dumps(cancelled_result, default=str),
                            tool_call_id=tc_event.call_id,
                        )
                    )

                exit_reason = TurnExitReason.INTERRUPTED
                safe_failure = safe_failure or "interrupted during tool execution"
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                ))
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=exit_reason,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

            # Cancel the cancel waiter — dispatch completed normally
            await _cancel_and_join(cancel_task)

            result = await dispatch_task
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
                safe_failure = persistence_error
                emit(LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=safe_failure,
                ))
                return TurnResult(
                    turn_id=turn_id,
                    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
                    final_text=accumulated_text,
                    model_steps=model_steps,
                    tool_starts=tool_starts + 1,
                    new_messages=new_messages,
                    safe_failure=safe_failure,
                    user_message_id=user_message_id,
                    model_name=captured_model_name,
                    provider_name=captured_provider_name,
                    usage=captured_usage,
                    input_characters=input_characters,
                )

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
        exit_reason = TurnExitReason.LIMIT_REACHED
        safe_failure = f"limit reached after {model_steps} model step(s)"
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_FAILED,
                error=safe_failure,
            )
        )

    # ── Emit final event ──
    if exit_reason == TurnExitReason.COMPLETED:
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_COMPLETED,
            )
        )
    elif exit_reason == TurnExitReason.INTERRUPTED:
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_INTERRUPTED,
            )
        )
    elif exit_reason in (TurnExitReason.MODEL_FAILED,):
        emit(
            LiveEvent(
                session_id=session_id,
                turn_id=turn_id,
                event_type=LiveEventType.TURN_FAILED,
                error=safe_failure,
            )
        )

    return TurnResult(
        turn_id=turn_id,
        exit_reason=exit_reason,
        final_text=final_text,
        model_steps=model_steps,
        tool_starts=tool_starts,
        new_messages=new_messages,
        safe_failure=safe_failure,
        user_message_id=user_message_id,
        model_name=captured_model_name,
        provider_name=captured_provider_name,
        usage=captured_usage,
        input_characters=input_characters,
    )


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
    tr_msg = ToolResultMessage(
        message_id=_mid(),
        turn_id=turn_id,
        call_id=call_id,
        tool_name=tool_name,
        ok=result.get("ok", False),
        result=result.get("data"),
        error_code=result.get("code") if not result.get("ok") else None,
        error=result.get("error") if not result.get("ok") else None,
    )
    new_messages.append(tr_msg)
    try:
        persist_message(tr_msg)
    except Exception:
        error = "tool result persistence failed"
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
        code = result.get("code", "handler_error")
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
                error=result.get("error", ""),
            )
        )
    return tr_msg, ""


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


def _mid() -> str:
    """Generate a short unique message ID."""
    return uuid.uuid4().hex[:12]
