"""Bounded streaming turn runtime — domain-free model and tool loop.

Plan 003 Phase 5: Run one conversational turn through the model with streaming,
tool dispatch, live events, and cancellation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from haxjobs.agent_core.live_events import LiveEvent, LiveEventEmitter, LiveEventType
from haxjobs.agent_core.messages import (
    AssistantMessage,
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
    project_messages,
)
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.model.client import ModelClient
from haxjobs.model.types import (
    ModelMessage,
    ModelRequest,
    ModelStreamEvent,
    ModelStreamEventType,
    ToolSchema,
)

logger = logging.getLogger(__name__)

_MAX_MODEL_STEPS = 5


class TurnExitReason(str, Enum):
    COMPLETED = "completed"
    MODEL_FAILED = "model_failed"
    LIMIT_REACHED = "limit_reached"
    INTERRUPTED = "interrupted"


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
    max_model_steps: int = 5,
) -> TurnResult:
    """Execute one conversational turn — streaming model and tool loop.

    Returns a TurnResult regardless of outcome.
    """
    max_steps = min(max(max_model_steps, 1), _MAX_MODEL_STEPS)
    new_messages: list[ConversationMessage] = []
    final_text = ""
    safe_failure = ""
    exit_reason = TurnExitReason.COMPLETED
    model_steps = 0
    tool_starts = 0

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
        tool_schemas = tool_registry.active_schemas(active_tools)

    # Build initial provider messages: system + context + history projection
    provider_messages: list[ModelMessage] = project_messages(
        system_prompt=system_prompt,
        context_messages=context_messages,
        history=history,
    )

    # ── Main loop ──
    while model_steps < max_steps:
        if cancel_event.is_set():
            exit_reason = TurnExitReason.INTERRUPTED
            safe_failure = "interrupted before model call"
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_INTERRUPTED,
                )
            )
            break

        model_steps += 1
        request = ModelMessage  # placeholder, actual request built below
        accumulated_text = ""
        model_failed = False
        tool_call_events: list[ModelStreamEvent] = []
        finish_reason = ""

        # Build model request
        from haxjobs.model.types import ModelRequest

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
                        new_messages.append(
                            AssistantMessage(
                                message_id=_mid(),
                                turn_id=turn_id,
                                content=accumulated_text,
                                status="interrupted",
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
                    model_failed = True
                    safe_failure = stream_event.error or "model stream failed"
                    exit_reason = TurnExitReason.MODEL_FAILED
                    final_text = accumulated_text
                    # Persist partial assistant text
                    if accumulated_text:
                        new_messages.append(
                            AssistantMessage(
                                message_id=_mid(),
                                turn_id=turn_id,
                                content=accumulated_text,
                                status="failed",
                            )
                        )
                    emit(
                        LiveEvent(
                            session_id=session_id,
                            turn_id=turn_id,
                            event_type=LiveEventType.TURN_FAILED,
                            error=safe_failure,
                        )
                    )
                    break
        except Exception as exc:
            model_failed = True
            safe_failure = str(exc)
            exit_reason = TurnExitReason.MODEL_FAILED
            emit(
                LiveEvent(
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type=LiveEventType.TURN_FAILED,
                    error=safe_failure,
                )
            )
            break

        if model_failed:
            break

        # ── No tool calls: turn complete ──
        if not tool_call_events:
            final_text = accumulated_text
            exit_reason = TurnExitReason.COMPLETED

            # Persist assistant message
            new_messages.append(
                AssistantMessage(
                    message_id=_mid(),
                    turn_id=turn_id,
                    content=accumulated_text,
                    status="complete",
                )
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
                )

            # Persist canonical tool call message
            tc_msg = ToolCallMessage(
                message_id=_mid(),
                turn_id=turn_id,
                call_id=tc_event.call_id,
                tool_name=tc_event.tool_name,
                arguments=tc_event.arguments,
            )
            new_messages.append(tc_msg)

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

            # Dispatch tool — with cancellation awareness
            dispatch_task = asyncio.ensure_future(
                tool_registry.dispatch(
                    name=tc_event.tool_name,
                    arguments=tc_event.arguments,
                    active_names=active_tools,
                )
            )

            # Wait for dispatch or cancellation
            done, pending = await asyncio.wait(
                [dispatch_task],
                timeout=None,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if cancel_event.is_set() or dispatch_task not in [d for d in done]:
                # Cancel the dispatch task
                dispatch_task.cancel()
                try:
                    await dispatch_task
                except (asyncio.CancelledError, Exception):
                    pass

                t_duration_ms = (time.monotonic() - t_start) * 1000
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TOOL_FAILED,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        tool_status="cancelled",
                        tool_duration_ms=t_duration_ms,
                    )
                )

                # Persist tool result as cancelled
                tr_msg = ToolResultMessage(
                    message_id=_mid(),
                    turn_id=turn_id,
                    call_id=tc_event.call_id,
                    tool_name=tc_event.tool_name,
                    ok=False,
                    result=None,
                    error_code="cancelled",
                    error="tool execution cancelled",
                )
                new_messages.append(tr_msg)
                provider_messages.append(
                    ModelMessage(
                        role="tool",
                        content=json.dumps({
                            "ok": False,
                            "error_code": "cancelled",
                            "error": "tool execution cancelled",
                        }, default=str),
                        tool_call_id=tc_event.call_id,
                    )
                )

                exit_reason = TurnExitReason.INTERRUPTED
                safe_failure = "interrupted during tool execution"
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
                )

            result = await dispatch_task
            t_duration_ms = (time.monotonic() - t_start) * 1000

            if result.get("ok"):
                tool_starts += 1
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TOOL_COMPLETED,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        tool_status="ok",
                        tool_duration_ms=t_duration_ms,
                    )
                )
            else:
                code = result.get("code", "handler_error")
                # Count as tool start for validation/argument failures too
                # (they were attempted dispatches)
                tool_starts += 1
                emit(
                    LiveEvent(
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type=LiveEventType.TOOL_FAILED,
                        call_id=tc_event.call_id,
                        tool_name=tc_event.tool_name,
                        tool_status=code,
                        tool_duration_ms=t_duration_ms,
                        error_code=code,
                        error=result.get("error", ""),
                    )
                )

            # Persist tool result message
            tr_msg = ToolResultMessage(
                message_id=_mid(),
                turn_id=turn_id,
                call_id=tc_event.call_id,
                tool_name=tc_event.tool_name,
                ok=result.get("ok", False),
                result=result.get("data"),
                error_code=result.get("code") if not result.get("ok") else None,
                error=result.get("error") if not result.get("ok") else None,
            )
            new_messages.append(tr_msg)

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
    )


def _mid() -> str:
    """Generate a short unique message ID."""
    return uuid.uuid4().hex[:12]
