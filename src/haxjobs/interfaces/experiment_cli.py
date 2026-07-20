"""Thin experiment CLI — no employment logic in argparse handlers."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from haxjobs.agent_core.artifacts import ArtifactWriter
from haxjobs.agent_core.runtime import run_stage0
from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.agent_core.types import RunExitReason
from haxjobs.employment.fixtures import load_career_fixture, load_job_fixture
from haxjobs.employment.job_source import JobSourceFetcher, SourceObservation
from haxjobs.employment.review_job import assemble_job_review_request, build_stage1_tools
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelFailure, ModelResponse, ToolCall

logger = logging.getLogger(__name__)

FAKE_STAGE0_RESPONSE = "FAKE_STAGE0_RESPONSE: provider boundary and artifact writing are working."
FAKE_STAGE1_FINAL = "FAKE_STAGE1: one tool call completed, final response."

_JOB_FIXTURES: dict[int, str] = {
    49: "discussion/fixtures/harness/job-49.json",
    328: "discussion/fixtures/harness/job-328.json",
}

_DEFAULT_CAREER_FIXTURE = "tests/fixtures/job_review/career.json"
_PRIVATE_CAREER_FIXTURE = "state/experiments/fixtures/backend-career.json"


def cmd_experiment_review_job(args) -> None:
    """Run the Stage 0 or Stage 1 job-review experiment."""
    # Validate max-model-steps
    if args.max_model_steps < 1 or args.max_model_steps > 5:
        print(f"--max-model-steps must be between 1 and 5, got {args.max_model_steps}", file=sys.stderr)
        sys.exit(2)

    # Validate --live and --fake
    if args.live and args.fake:
        print("--live and --fake are mutually exclusive", file=sys.stderr)
        sys.exit(2)

    # Resolve job fixture
    job_path = _JOB_FIXTURES.get(args.job)
    if not job_path:
        print(f"Unknown job ref: {args.job}. Valid: {sorted(_JOB_FIXTURES.keys())}", file=sys.stderr)
        sys.exit(2)

    # Resolve career fixture
    if args.career_fixture:
        career_path = args.career_fixture
    elif args.fake:
        career_path = _DEFAULT_CAREER_FIXTURE
    else:
        career_path = _PRIVATE_CAREER_FIXTURE

    if not Path(career_path).exists():
        print(f"Career fixture not found: {career_path}", file=sys.stderr)
        sys.exit(2)

    # Load fixtures
    career = load_career_fixture(career_path)
    job = load_job_fixture(job_path)

    # Assemble RunRequest
    run_request = assemble_job_review_request(career=career, job=job)

    # Create artifact writer with configured root
    artifact_writer = ArtifactWriter(root=Path(args.artifacts_dir or "state/harness-runs"))

    # ── Stage 1 ──
    if args.inspect_source:
        if args.fake:
            # Fake model + fake source transport
            fetcher = _FakeSourceFetcher()
            registry, active = build_stage1_tools(job, fetcher)

            model = FakeModelClient(responses=[
                ModelResponse(
                    text="Let me check the source.",
                    finish_reason="tool_calls",
                    tool_calls=[
                        ToolCall(
                            call_id="fake_call_1",
                            name="inspect_job_source",
                            arguments=f'{{"job_ref": "{job.job_ref}"}}',
                        )
                    ],
                    model="fake-stage1",
                    provider="fake",
                ),
                ModelResponse(
                    text=FAKE_STAGE1_FINAL,
                    finish_reason="stop",
                    model="fake-stage1",
                    provider="fake",
                ),
            ])
        else:
            from haxjobs.model.client import OpenAIModelClient
            model = OpenAIModelClient()
            fetcher = JobSourceFetcher()
            registry, active = build_stage1_tools(job, fetcher)

        result = asyncio.run(
            run_stage0(
                run_request,
                model=model,
                artifact_writer=artifact_writer,
                active_tools=active,
                tool_registry=registry,
                max_model_steps=args.max_model_steps,
            )
        )
    else:
        # ── Stage 0 ──
        if args.fake:
            model = FakeModelClient(responses=[
                ModelResponse(
                    text=FAKE_STAGE0_RESPONSE,
                    finish_reason="stop",
                    model="fake-stage0",
                    provider="fake",
                )
            ])
        else:
            from haxjobs.model.client import OpenAIModelClient
            model = OpenAIModelClient()

        result = asyncio.run(run_stage0(run_request, model=model, artifact_writer=artifact_writer))

    # Report
    if result.exit_reason == RunExitReason.COMPLETED:
        print(result.final_text)
    else:
        print(f"Run failed: {result.safe_failure}", file=sys.stderr)

    print(f"Run ID: {result.run_id}")
    print(f"Model steps: {result.model_steps}")
    print(f"Tool starts: {result.tool_starts}")
    print(f"Artifact directory: {result.artifact_dir}")
    review_path = Path(result.artifact_dir) / "review.md" if result.artifact_dir else ""
    print(f"Review path: {review_path}")

    # Exit status
    exit_code = 0
    if result.exit_reason == RunExitReason.MODEL_FAILED:
        print(f"Model failure: {result.safe_failure}", file=sys.stderr)
        exit_code = 1
    if result.observer_errors:
        print(f"Observer errors: {result.observer_errors}", file=sys.stderr)
        exit_code = 1
    if result.artifact_errors:
        print(f"Artifact errors: {result.artifact_errors}", file=sys.stderr)
        exit_code = 1
    if not result.receipt_complete:
        print("Warning: receipt writing incomplete", file=sys.stderr)

    sys.exit(exit_code)


class _FakeSourceFetcher:
    """Fake source fetcher for CLI tests — returns scripted observation."""

    async def fetch(self, job_ref: str, job_fixture, allowed_hosts: tuple[str, ...]) -> SourceObservation:
        return SourceObservation(
            ok=True,
            job_ref=int(job_ref),
            source_url=job_fixture.source_url,
            host="fake.example.com",
            status="current",
            visible_text="Fake job description: Python backend role in London. "
                         "Requirements: FastAPI, Django, PostgreSQL. "
                         "Mid-level, remote-friendly.",
            visible_text_length=120,
            content_hash="fakehash123",
            source_type="text/html",
        )
