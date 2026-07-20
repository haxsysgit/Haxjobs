"""Stage 0/1 runtime — one model call (Stage 0) or bounded tool-call loop (Stage 1)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from haxjobs.agent_core.artifacts import ArtifactWriter
from haxjobs.agent_core.events import (
    RunEvent,
    RunEventType,
    RunObserver,
)
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.agent_core.types import (
    AgentMessage,
    RunExitReason,
    RunRequest,
    RunResult,
)
from haxjobs.model.client import ModelClient
from haxjobs.model.types import ModelFailure, ModelMessage, ModelRequest, ModelResponse, ToolSchema

logger = logging.getLogger(__name__)

_MAX_MODEL_STEPS_HARD_CAP = 5
_MAX_TOOL_HANDLER_STARTS = 1


def _project_messages(system: str, user: str) -> list[ModelMessage]:
    """Project internal agent messages to provider-compatible ModelMessages."""
    messages: list[ModelMessage] = []
    if system:
        messages.append(ModelMessage(role="system", content=system))
    messages.append(ModelMessage(role="user", content=user))
    return messages


def _emit(
    observers: list[RunObserver],
    events: list[RunEvent],
    event: RunEvent,
) -> list[str]:
    """Emit event to all observers and collect it. Returns observer error strings."""
    events.append(event)
    errors: list[str] = []
    for obs in observers:
        try:
            obs.on_event(event)
        except Exception as exc:
            err_msg = f"observer error: {exc}"
            logger.warning("observer error on %s: %s", event.event_type, exc)
            errors.append(err_msg)
    return errors


def _build_review_md(
    run_id: str,
    exit_reason: str,
    final_text: str,
    safe_failure: str,
    observer_errors: list[str],
    artifact_errors: list[str],
    model_steps: int,
    tool_starts: int,
) -> str:
    """Generate the human-review markdown template."""
    stage_label = "Stage 1" if tool_starts > 0 or model_steps > 1 else "Stage 0"
    lines = [
        f"# {stage_label} Run Review — {run_id}",
        "",
        f"- **Exit reason:** {exit_reason}",
        f"- **Model steps:** {model_steps}",
        f"- **Tool starts:** {tool_starts}",
        f"- **Observer errors:** {len(observer_errors)}",
        f"- **Artifact errors:** {len(artifact_errors)}",
        f"- **Receipt complete:** True",
        "",
    ]
    if observer_errors:
        lines.append("## Observer errors")
        for e in observer_errors:
            lines.append(f"- {e}")
        lines.append("")
    if artifact_errors:
        lines.append("## Artifact errors")
        for e in artifact_errors:
            lines.append(f"- {e}")
        lines.append("")
    if safe_failure:
        lines.append("## Failure")
        lines.append(f"```\n{safe_failure}\n```")
        lines.append("")
    lines.append("## Final answer")
    lines.append(f"```\n{final_text}\n```")
    lines.append("")
    lines.append("---")
    lines.append("*Review this run against `discussion/fixtures/harness/job-review-rubric.md`.*")
    return "\n".join(lines)


def _clamp_model_steps(raw: int) -> int:
    """Clamp model steps to 1-5 range. Default 3."""
    if raw < 1:
        return 3
    return min(raw, _MAX_MODEL_STEPS_HARD_CAP)


async def _write_receipts(
    run_id: str,
    events: list[RunEvent],
    context: dict[str, Any],
    transcript: list[dict[str, Any]],
    result: dict[str, Any],
    review_md: str,
    manifest: dict[str, Any],
    artifact_writer: ArtifactWriter,
    iso_started: str,
    duration: float,
    exit_reason: str,
    response: ModelResponse | None,
    safe_failure: str,
) -> tuple[str, list[str]]:
    """Write all receipt files. Returns (artifact_dir, artifact_errors)."""
    artifact_errors: list[str] = []
    try:
        run_dir, _ = artifact_writer.write_all_receipts(
            run_id=run_id,
            events=events,
            manifest=manifest,
            context=context,
            transcript=transcript,
            result=result,
            review_md=review_md,
        )
        return str(run_dir), artifact_errors
    except Exception as exc:
        artifact_err = f"receipt write failed: {exc}"
        logger.warning(artifact_err)
        artifact_errors.append(artifact_err)
        return "", artifact_errors


async def run_stage0(
    request: RunRequest,
    model: ModelClient,
    observers: list[RunObserver] | None = None,
    artifact_writer: ArtifactWriter | None = None,
    active_tools: tuple[str, ...] = (),
    tool_registry: ToolRegistry | None = None,
    max_model_steps: int = 3,
) -> RunResult:
    """Execute Stage 0 (one call, no tools) or Stage 1 (bounded tool-call loop).

    Returns a RunResult regardless of success or failure.
    """
    observers = observers or []
    artifact_writer = artifact_writer or ArtifactWriter()
    started_at = time.monotonic()
    iso_started = datetime.now(timezone.utc).isoformat()
    observer_errors: list[str] = []
    artifact_errors: list[str] = []
    events: list[RunEvent] = []
    max_steps = _clamp_model_steps(max_model_steps)

    # Event: run_started
    obs_errs = _emit(
        observers,
        events,
        RunEvent(
            run_id=request.run_id,
            event_type=RunEventType.RUN_STARTED,
        ),
    )
    observer_errors.extend(obs_errs)

    # Event: context_prepared
    obs_errs = _emit(
        observers,
        events,
        RunEvent(
            run_id=request.run_id,
            event_type=RunEventType.CONTEXT_PREPARED,
        ),
    )
    observer_errors.extend(obs_errs)

    # Build tool schemas once if tools are active
    tool_schemas: list[ToolSchema] = []
    if active_tools and tool_registry is not None:
        tool_schemas = tool_registry.active_schemas(active_tools)

    # ── Loop state ──
    provider_messages: list[ModelMessage] = _project_messages(
        request.system_message, request.user_message
    )
    final_text = ""
    safe_failure = ""
    exit_reason = RunExitReason.COMPLETED
    last_response: ModelResponse | None = None
    model_steps = 0
    tool_starts = 0
    total_usage: Any = None
    accumulated_duration = 0.0
    context = {
        "run_id": request.run_id,
        "system_message": request.system_message,
        "user_message": request.user_message,
    }
    transcript: list[dict[str, Any]] = [
        {"role": "user", "content": request.user_message},
    ]

    # ── Main loop ──
    while model_steps < max_steps:
        model_steps += 1
        model_request = ModelRequest(
            messages=list(provider_messages),
            max_tokens=request.model_kwargs.get("max_tokens", 4096),
            tools=list(tool_schemas),
        )

        # Event: model_started
        step_started = time.monotonic()
        obs_errs = _emit(
            observers,
            events,
            RunEvent(
                run_id=request.run_id,
                event_type=RunEventType.MODEL_STARTED,
                model_step=model_steps,
            ),
        )
        observer_errors.extend(obs_errs)

        model_result = await model.complete(model_request)
        step_duration = time.monotonic() - step_started
        accumulated_duration += step_duration

        if isinstance(model_result, ModelFailure):
            safe_failure = model_result.safe_summary()
            exit_reason = RunExitReason.MODEL_FAILED
            obs_errs = _emit(
                observers,
                events,
                RunEvent(
                    run_id=request.run_id,
                    event_type=RunEventType.MODEL_FAILED,
                    model=model_result.model,
                    provider=model_result.provider,
                    error=model_result.error,
                    error_category=model_result.category,
                    duration_seconds=step_duration,
                    model_step=model_steps,
                ),
            )
            observer_errors.extend(obs_errs)
            obs_errs = _emit(
                observers,
                events,
                RunEvent(
                    run_id=request.run_id,
                    event_type=RunEventType.RUN_FAILED,
                    model=model_result.model,
                    provider=model_result.provider,
                    duration_seconds=accumulated_duration,
                    error=model_result.safe_summary(),
                ),
            )
            observer_errors.extend(obs_errs)
            transcript.append({"role": "model_failure", "content": safe_failure})
            break

        response: ModelResponse = model_result
        last_response = response
        if response.usage:
            total_usage = response.usage

        # Event: model_completed
        obs_errs = _emit(
            observers,
            events,
            RunEvent(
                run_id=request.run_id,
                event_type=RunEventType.MODEL_COMPLETED,
                model=response.model,
                provider=response.provider,
                finish_reason=response.finish_reason,
                duration_seconds=step_duration,
                model_step=model_steps,
            ),
        )
        observer_errors.extend(obs_errs)

        # ── No tool calls: stop ──
        if not response.tool_calls:
            # Check for empty response (no text, no calls)
            if not response.text.strip():
                exit_reason = RunExitReason.EMPTY_MODEL_RESPONSE
                safe_failure = "model returned empty response"
            else:
                final_text = response.text
                exit_reason = RunExitReason.COMPLETED
            transcript.append({"role": "assistant", "content": response.text})
            break

        # ── Has tool calls: process them ──
        # Preserve assistant message with full content before tool results
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.text}
        assistant_msg["tool_calls"] = [
            {"call_id": tc.call_id, "name": tc.name, "arguments": tc.arguments}
            for tc in response.tool_calls
        ]
        transcript.append(assistant_msg)

        # Also preserve in provider messages: assistant with tool_calls
        provider_tool_calls: list[dict] = [
            {
                "id": tc.call_id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments,
                },
            }
            for tc in response.tool_calls
        ]
        assistant_model_msg = ModelMessage(
            role="assistant",
            content=response.text,
            tool_calls=provider_tool_calls,
        )
        provider_messages.append(assistant_model_msg)

        # Dispatch tool calls in source order
        tool_results: list[dict[str, Any]] = []

        for tc in response.tool_calls:
            # Event: tool_requested
            obs_errs = _emit(
                observers,
                events,
                RunEvent(
                    run_id=request.run_id,
                    event_type=RunEventType.TOOL_REQUESTED,
                    call_id=tc.call_id,
                    tool_name=tc.name,
                    model_step=model_steps,
                ),
            )
            observer_errors.extend(obs_errs)

            # Truncated response → all calls unsafe
            if response.tool_calls_unsafe:
                result = {
                    "ok": False,
                    "code": "truncated_tool_call",
                    "error": "response truncated mid-tool-call, unsafe to execute",
                }
                obs_errs = _emit(
                    observers,
                    events,
                    RunEvent(
                        run_id=request.run_id,
                        event_type=RunEventType.TOOL_FAILED,
                        call_id=tc.call_id,
                        tool_name=tc.name,
                        tool_status="truncated",
                        model_step=model_steps,
                    ),
                )
                observer_errors.extend(obs_errs)
            elif tool_registry is None:
                result = {
                    "ok": False,
                    "code": "no_registry",
                    "error": "no tool registry available",
                }
                obs_errs = _emit(
                    observers,
                    events,
                    RunEvent(
                        run_id=request.run_id,
                        event_type=RunEventType.TOOL_FAILED,
                        call_id=tc.call_id,
                        tool_name=tc.name,
                        tool_status="no_registry",
                        model_step=model_steps,
                    ),
                )
                observer_errors.extend(obs_errs)
            else:
                # Check budget: only one handler start allowed
                if tool_starts >= _MAX_TOOL_HANDLER_STARTS:
                    result = {
                        "ok": False,
                        "code": "tool_budget_exhausted",
                        "error": "maximum tool executions reached (1)",
                    }
                    obs_errs = _emit(
                        observers,
                        events,
                        RunEvent(
                            run_id=request.run_id,
                            event_type=RunEventType.TOOL_FAILED,
                            call_id=tc.call_id,
                            tool_name=tc.name,
                            tool_status="budget_exhausted",
                            model_step=model_steps,
                        ),
                    )
                    observer_errors.extend(obs_errs)
                else:
                    # Only count a start if it's a known active tool — attempt dispatch
                    is_valid_dispatch = (
                        tc.name in tool_registry._tools
                        and tc.name in active_tools
                        and not response.tool_calls_unsafe
                    )
                    # Event: tool_started
                    t_start = time.monotonic()
                    obs_errs = _emit(
                        observers,
                        events,
                        RunEvent(
                            run_id=request.run_id,
                            event_type=RunEventType.TOOL_STARTED,
                            call_id=tc.call_id,
                            tool_name=tc.name,
                            model_step=model_steps,
                        ),
                    )
                    observer_errors.extend(obs_errs)

                    result = await tool_registry.dispatch(
                        name=tc.name,
                        arguments=tc.arguments,
                        active_names=active_tools,
                    )
                    t_duration_ms = (time.monotonic() - t_start) * 1000

                    if result.get("ok"):
                        tool_starts += 1
                        obs_errs = _emit(
                            observers,
                            events,
                            RunEvent(
                                run_id=request.run_id,
                                event_type=RunEventType.TOOL_COMPLETED,
                                call_id=tc.call_id,
                                tool_name=tc.name,
                                tool_status="ok",
                                tool_duration_ms=t_duration_ms,
                                model_step=model_steps,
                            ),
                        )
                        observer_errors.extend(obs_errs)
                    else:
                        if result.get("code") not in (
                            "unknown_tool", "tool_inactive", "malformed_arguments", "invalid_arguments"
                        ):
                            tool_starts += 1

                        obs_errs = _emit(
                            observers,
                            events,
                            RunEvent(
                                run_id=request.run_id,
                                event_type=RunEventType.TOOL_FAILED,
                                call_id=tc.call_id,
                                tool_name=tc.name,
                                tool_status=code,
                                tool_duration_ms=t_duration_ms,
                                model_step=model_steps,
                            ),
                        )
                        observer_errors.extend(obs_errs)

            # Append tool result message to transcript and provider messages
            tool_results.append({
                "call_id": tc.call_id,
                "name": tc.name,
                "result": result,
            })

            # Append tool result as a message
            result_str = json.dumps(result, default=str)
            transcript.append({
                "role": "tool",
                "call_id": tc.call_id,
                "name": tc.name,
                "content": result_str,
            })
            provider_messages.append(
                ModelMessage(
                    role="tool",
                    content=json.dumps(result, default=str),
                    tool_call_id=tc.call_id,
                )
            )

    # ── Loop ended (limit) ──
    else:
        # Reached max_model_steps without explicit stop
        exit_reason = RunExitReason.LIMIT_REACHED
        safe_failure = f"limit reached after {model_steps} model step(s)"
        if last_response and last_response.text:
            final_text = last_response.text

    # ── Post-loop events ──
    duration = time.monotonic() - started_at
    if exit_reason == RunExitReason.COMPLETED:
        obs_errs = _emit(
            observers,
            events,
            RunEvent(
                run_id=request.run_id,
                event_type=RunEventType.RUN_COMPLETED,
                model=last_response.model if last_response else "",
                provider=last_response.provider if last_response else "",
                duration_seconds=duration,
            ),
        )
        observer_errors.extend(obs_errs)
    elif exit_reason not in (RunExitReason.MODEL_FAILED,):
        obs_errs = _emit(
            observers,
            events,
            RunEvent(
                run_id=request.run_id,
                event_type=RunEventType.RUN_FAILED,
                model=last_response.model if last_response else "",
                provider=last_response.provider if last_response else "",
                duration_seconds=duration,
                error=safe_failure,
            ),
        )
        observer_errors.extend(obs_errs)

    # ── Build result ──
    run_result = RunResult(
        run_id=request.run_id,
        exit_reason=exit_reason,
        final_text=final_text,
        safe_failure=safe_failure,
        model=last_response.model if last_response else "",
        provider=last_response.provider if last_response else "",
        duration_seconds=duration,
        usage=total_usage,
        observer_errors=observer_errors,
        artifact_errors=artifact_errors,
        receipt_complete=False,
        model_steps=model_steps,
        tool_starts=tool_starts,
    )

    # ── Write receipts ──
    exit_reason_str = exit_reason.value
    review_md = _build_review_md(
        request.run_id,
        exit_reason_str,
        final_text,
        safe_failure,
        observer_errors,
        artifact_errors,
        model_steps,
        tool_starts,
    )
    manifest: dict[str, Any] = {
        "run_id": request.run_id,
        "started_at": iso_started,
        "exit_reason": exit_reason_str,
        "model": last_response.model if last_response else "",
        "provider": last_response.provider if last_response else "",
        "duration_seconds": duration,
        "model_steps": model_steps,
        "tool_starts": tool_starts,
        "receipt_complete": True,
        "hash": artifact_writer.stable_manifest_hash(request.run_id, iso_started),
    }
    if last_response:
        manifest["finish_reason"] = last_response.finish_reason
    if total_usage:
        manifest["usage"] = {
            "prompt_tokens": total_usage.prompt_tokens,
            "completion_tokens": total_usage.completion_tokens,
            "total_tokens": total_usage.total_tokens,
        }
    result_data: dict[str, Any] = {
        "run_id": request.run_id,
        "exit_reason": exit_reason_str,
        "final_text": final_text,
        "safe_failure": safe_failure,
        "model": last_response.model if last_response else "",
        "provider": last_response.provider if last_response else "",
        "finish_reason": last_response.finish_reason if last_response else "",
        "model_steps": model_steps,
        "tool_starts": tool_starts,
        "receipt_complete": True,
    }

    try:
        run_dir, _ = artifact_writer.write_all_receipts(
            run_id=request.run_id,
            events=events,
            manifest=manifest,
            context=context,
            transcript=transcript,
            result=result_data,
            review_md=review_md,
        )
        run_result.artifact_dir = str(run_dir)
        run_result.receipt_complete = True
    except Exception as exc:
        artifact_err = f"receipt write failed: {exc}"
        logger.warning(artifact_err)
        artifact_errors.append(artifact_err)
        run_result.artifact_errors = artifact_errors

    return run_result
