"""Thin experiment CLI — no employment logic in argparse handlers."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from haxjobs.agent_core.artifacts import ArtifactWriter
from haxjobs.agent_core.runtime import run_stage0
from haxjobs.agent_core.types import RunExitReason
from haxjobs.employment.fixtures import load_career_fixture, load_job_fixture
from haxjobs.employment.review_job import assemble_job_review_request
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelFailure, ModelResponse

logger = logging.getLogger(__name__)

FAKE_STAGE0_RESPONSE = "FAKE_STAGE0_RESPONSE: provider boundary and artifact writing are working."

_JOB_FIXTURES: dict[int, str] = {
    49: "discussion/fixtures/harness/job-49.json",
    328: "discussion/fixtures/harness/job-328.json",
}

_DEFAULT_CAREER_FIXTURE = "tests/fixtures/job_review/career.json"
_PRIVATE_CAREER_FIXTURE = "state/experiments/fixtures/backend-career.json"


def cmd_experiment_review_job(args) -> None:
    """Run the Stage 0 job-review experiment."""
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

    # Resolve model
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

    # Load fixtures
    career = load_career_fixture(career_path)
    job = load_job_fixture(job_path)

    # Assemble RunRequest
    run_request = assemble_job_review_request(career=career, job=job)

    # Create artifact writer with configured root
    artifact_writer = ArtifactWriter(root=Path(args.artifacts_dir or "state/harness-runs"))

    # Run
    result = asyncio.run(run_stage0(run_request, model=model, artifact_writer=artifact_writer))

    # Report
    if result.exit_reason == RunExitReason.COMPLETED:
        print(result.final_text)
    else:
        print(f"Run failed: {result.safe_failure}", file=sys.stderr)

    print(f"Run ID: {result.run_id}")
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
