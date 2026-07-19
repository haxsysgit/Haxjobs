"""Stage 0 runtime — exactly one model call, no tools, no loop."""

from __future__ import annotations

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
from haxjobs.agent_core.types import (
    AgentMessage,
    RunExitReason,
    RunRequest,
    RunResult,
)
from haxjobs.model.client import ModelClient
from haxjobs.model.types import ModelFailure, ModelMessage, ModelRequest, ModelResponse

logger = logging.getLogger(__name__)


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
) -> str:
    """Generate the human-review markdown template."""
    lines = [
        f"# Stage 0 Run Review — {run_id}",
        "",
        f"- **Exit reason:** {exit_reason}",
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


async def run_stage0(
    request: RunRequest,
    model: ModelClient,
    observers: list[RunObserver] | None = None,
    artifact_writer: ArtifactWriter | None = None,
) -> RunResult:
    """Execute exactly one model call with no tools, no retry, no loop.

    Returns a RunResult regardless of success or failure.
    """
    observers = observers or []
    artifact_writer = artifact_writer or ArtifactWriter()
    started_at = time.monotonic()
    iso_started = datetime.now(timezone.utc).isoformat()
    observer_errors: list[str] = []
    artifact_errors: list[str] = []
    events: list[RunEvent] = []

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

    # Project internal messages to provider messages
    provider_messages = _project_messages(
        request.system_message, request.user_message
    )
    model_request = ModelRequest(
        messages=provider_messages,
        max_tokens=request.model_kwargs.get("max_tokens", 4096),
    )

    # Event: model_started
    obs_errs = _emit(
        observers,
        events,
        RunEvent(
            run_id=request.run_id,
            event_type=RunEventType.MODEL_STARTED,
        ),
    )
    observer_errors.extend(obs_errs)

    # One model call
    model_result = await model.complete(model_request)

    duration = time.monotonic() - started_at

    if isinstance(model_result, ModelFailure):
        # Event: model_failed
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
                duration_seconds=duration,
            ),
        )
        observer_errors.extend(obs_errs)

        # Event: run_failed
        obs_errs = _emit(
            observers,
            events,
            RunEvent(
                run_id=request.run_id,
                event_type=RunEventType.RUN_FAILED,
                model=model_result.model,
                provider=model_result.provider,
                duration_seconds=duration,
                error=model_result.safe_summary(),
            ),
        )
        observer_errors.extend(obs_errs)

        # Build result
        run_result = RunResult(
            run_id=request.run_id,
            exit_reason=RunExitReason.MODEL_FAILED,
            safe_failure=model_result.safe_summary(),
            model=model_result.model,
            provider=model_result.provider,
            duration_seconds=duration,
            observer_errors=observer_errors,
            artifact_errors=artifact_errors,
            receipt_complete=False,
        )

        # Write receipts
        try:
            context = {
                "run_id": request.run_id,
                "system_message": request.system_message,
                "user_message": request.user_message,
            }
            transcript = [
                {"role": "user", "content": request.user_message},
                {"role": "model_failure", "content": model_result.safe_summary()},
            ]
            review_md = _build_review_md(
                request.run_id,
                "model_failed",
                "",
                model_result.safe_summary(),
                observer_errors,
                artifact_errors,
            )
            manifest = {
                "run_id": request.run_id,
                "started_at": iso_started,
                "exit_reason": "model_failed",
                "model": model_result.model,
                "provider": model_result.provider,
                "duration_seconds": duration,
                "receipt_complete": True,
                "hash": artifact_writer.stable_manifest_hash(request.run_id, iso_started),
            }
            run_dir, _ = artifact_writer.write_all_receipts(
                run_id=request.run_id,
                events=events,
                manifest=manifest,
                context=context,
                transcript=transcript,
                result={
                    "run_id": request.run_id,
                    "exit_reason": "model_failed",
                    "safe_failure": model_result.safe_summary(),
                    "receipt_complete": True,
                },
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

    # Success path
    response: ModelResponse = model_result

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
            duration_seconds=duration,
        ),
    )
    observer_errors.extend(obs_errs)

    # Event: run_completed
    obs_errs = _emit(
        observers,
        events,
        RunEvent(
            run_id=request.run_id,
            event_type=RunEventType.RUN_COMPLETED,
            model=response.model,
            provider=response.provider,
            duration_seconds=duration,
        ),
    )
    observer_errors.extend(obs_errs)

    # Build result
    run_result = RunResult(
        run_id=request.run_id,
        exit_reason=RunExitReason.COMPLETED,
        final_text=response.text,
        model=response.model,
        provider=response.provider,
        duration_seconds=duration,
        usage=response.usage,
        observer_errors=observer_errors,
        artifact_errors=artifact_errors,
        receipt_complete=False,
    )

    # Write receipts
    try:
        context = {
            "run_id": request.run_id,
            "system_message": request.system_message,
            "user_message": request.user_message,
        }
        transcript = [
            {"role": "user", "content": request.user_message},
            {"role": "assistant", "content": response.text},
        ]
        review_md = _build_review_md(
            request.run_id,
            "completed",
            response.text,
            "",
            observer_errors,
            artifact_errors,
        )
        manifest = {
            "run_id": request.run_id,
            "started_at": iso_started,
            "exit_reason": "completed",
            "model": response.model,
            "provider": response.provider,
            "finish_reason": response.finish_reason,
            "duration_seconds": duration,
            "receipt_complete": True,
            "hash": artifact_writer.stable_manifest_hash(request.run_id, iso_started),
        }
        if response.usage:
            manifest["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        run_dir, _ = artifact_writer.write_all_receipts(
            run_id=request.run_id,
            events=events,
            manifest=manifest,
            context=context,
            transcript=transcript,
            result={
                "run_id": request.run_id,
                "exit_reason": "completed",
                "final_text": response.text,
                "model": response.model,
                "provider": response.provider,
                "finish_reason": response.finish_reason,
                "receipt_complete": True,
            },
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
