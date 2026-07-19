"""Stage 0 job review — deterministic greenfield test floor.

No network. No private data. No haxjobs.agent imports.
"""

import asyncio
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from haxjobs.agent_core.artifacts import ArtifactWriter
from haxjobs.agent_core.events import RunEvent, RunEventType, RunObserver
from haxjobs.agent_core.runtime import run_stage0
from haxjobs.agent_core.types import RunExitReason, RunRequest
from haxjobs.employment.fixtures import (
    CareerFixture,
    EvidenceItem,
    JobFixture,
    load_career_fixture,
    load_job_fixture,
)
from haxjobs.employment.review_job import (
    assemble_job_review_request,
    build_job_review_system_prompt,
    build_job_review_user_prompt,
)
from haxjobs.model.fake import FakeModelClient
from haxjobs.model.types import ModelFailure, ModelResponse


# ── helpers ──

def _valid_job49() -> JobFixture:
    return load_job_fixture("discussion/fixtures/harness/job-49.json")


def _valid_job328() -> JobFixture:
    return load_job_fixture("discussion/fixtures/harness/job-328.json")


def _valid_career() -> CareerFixture:
    return load_career_fixture("tests/fixtures/job_review/career.json")


def _fake_response(text: str = "test response") -> ModelResponse:
    return ModelResponse(
        text=text,
        finish_reason="stop",
        model="test-model",
        provider="test",
    )


def _fake_failure(error: str = "test error") -> ModelFailure:
    return ModelFailure(error=error, category="test_error")


# ── test 1: fixture contracts ──

def test_job49_fixture_contracts():
    j = _valid_job49()
    assert j.fixture_id == "job-49"
    assert j.fixture_version == 1
    assert j.job_ref == 49
    assert j.description_kind == "curated_source_summary"
    assert j.content_complete is False
    assert len(j.warnings) > 0
    assert j.employer_name == "Trainline"
    assert j.source_status == "direct"


def test_job328_fixture_contracts():
    j = _valid_job328()
    assert j.fixture_id == "job-328"
    assert j.description_kind == "title_and_url_stub"
    assert j.source_status == "lead_only"
    assert j.employer_name is None
    assert j.content_complete is False


def test_career_fixture_contracts():
    c = _valid_career()
    assert c.career_direction
    assert len(c.hard_constraints) > 0
    assert len(c.evidence) > 0
    for ev in c.evidence:
        assert ev.label
        assert ev.source
        assert ev.content


# ── test 2: missing fields rejection ──

def test_job_fixture_rejects_missing_observed_at():
    data = json.loads(Path("discussion/fixtures/harness/job-49.json").read_text())
    del data["observed_at"]
    with pytest.raises(ValueError):
        JobFixture.model_validate(data)


def test_career_fixture_rejects_empty_evidence():
    data = json.loads(Path("tests/fixtures/job_review/career.json").read_text())
    data["evidence"] = []
    with pytest.raises(ValueError):
        CareerFixture.model_validate(data)


def test_evidence_item_rejects_empty_source():
    with pytest.raises(ValueError):
        EvidenceItem(label="test", source="", content="test")


# ── test 3: truncated marking ──

def test_job49_is_marked_content_incomplete():
    j = _valid_job49()
    assert j.content_complete is False


# ── test 4: stub preservation ──

def test_job328_preserves_stub_no_extrapolation():
    j = _valid_job328()
    assert j.employer_name is None
    assert j.description_kind == "title_and_url_stub"
    assert "Software Engineer" in j.description
    assert "linkedin.com" in j.source_url


# ── test 5: context block order ──

def test_context_blocks_in_fixed_order():
    career = _valid_career()
    job = _valid_job49()
    user_prompt = build_job_review_user_prompt(career=career, job=job)

    idx_request = user_prompt.index("## USER REQUEST")
    idx_direction = user_prompt.index("## CAREER DIRECTION AND CONSTRAINTS")
    idx_evidence = user_prompt.index("## RELEVANT EVIDENCE")
    idx_snapshot = user_prompt.index("## JOB SOURCE SNAPSHOT")

    assert idx_request < idx_direction < idx_evidence < idx_snapshot


def test_system_prompt_contains_truth_rules():
    system = build_job_review_system_prompt()
    assert "never invent" in system.lower() or "Never invent" in system


# ── test 6: fake single call ──

@pytest.mark.asyncio
async def test_fake_model_single_call():
    fake = FakeModelClient(responses=[_fake_response("hello")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake)

    assert result.exit_reason == RunExitReason.COMPLETED
    assert result.final_text == "hello"
    assert fake.call_count == 1


@pytest.mark.asyncio
async def test_fake_model_exhausted_raises():
    fake = FakeModelClient(responses=[_fake_response("only")])
    request = RunRequest(system_message="sys", user_message="usr")

    await run_stage0(request, model=fake)

    with pytest.raises(RuntimeError, match="exhausted"):
        await fake.complete(request=None)  # type: ignore[arg-type]
    assert fake.call_count == 1


# ── test 7: max_retries=0 ──

def test_openai_client_max_retries_zero():
    """The OpenAIModelClient must use max_retries=0."""
    # ponytail: inspect the client init path without requiring live credentials
    import inspect
    from haxjobs.model.client import OpenAIModelClient

    source = inspect.getsource(OpenAIModelClient._ensure_client)
    assert "max_retries=0" in source


def test_openai_client_raises_on_missing_model_key():
    """OpenAIModelClient must raise ValueError when provider config lacks a 'model' key."""
    from haxjobs.model.client import OpenAIModelClient

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[provider]\napi_key = "sk-test"\nbase_url = "https://api.example.com/v1"\n')
        config_path = Path(f.name)

    try:
        client = OpenAIModelClient(credentials_path=config_path)
        with pytest.raises(ValueError, match="model"):
            client._ensure_client()
    finally:
        config_path.unlink()


# ── test 8: zero tools ──

@pytest.mark.asyncio
async def test_stage0_has_zero_tools():
    """Stage 0 runtime must not reference tool registries, tool dispatch, or tool schemas."""
    import inspect
    from haxjobs.agent_core.runtime import run_stage0

    source = inspect.getsource(run_stage0)
    # The function has no tool_registry, tool_dispatch, tool_schema, or tool_call references
    forbidden = ["tool_registry", "tool_dispatch", "tool_schema", "tool_call"]
    for term in forbidden:
        assert term not in source.lower(), f"found {term} in run_stage0 source"


# ── test 9: event order ──

@pytest.mark.asyncio
async def test_event_order_completed():
    events: list[RunEvent] = []

    class Collector(RunObserver):
        def on_event(self, event: RunEvent) -> None:
            events.append(event)

    fake = FakeModelClient(responses=[_fake_response("ok")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake, observers=[Collector()])

    assert result.exit_reason == RunExitReason.COMPLETED
    types = [e.event_type for e in events]
    expected = [
        RunEventType.RUN_STARTED,
        RunEventType.CONTEXT_PREPARED,
        RunEventType.MODEL_STARTED,
        RunEventType.MODEL_COMPLETED,
        RunEventType.RUN_COMPLETED,
    ]
    assert types == expected


@pytest.mark.asyncio
async def test_event_order_model_failed():
    events: list[RunEvent] = []

    class Collector(RunObserver):
        def on_event(self, event: RunEvent) -> None:
            events.append(event)

    fake = FakeModelClient(responses=[_fake_failure("boom")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake, observers=[Collector()])

    assert result.exit_reason == RunExitReason.MODEL_FAILED
    types = [e.event_type for e in events]
    expected = [
        RunEventType.RUN_STARTED,
        RunEventType.CONTEXT_PREPARED,
        RunEventType.MODEL_STARTED,
        RunEventType.MODEL_FAILED,
        RunEventType.RUN_FAILED,
    ]
    assert types == expected


# ── test 10: JSONL redaction ──

def test_run_event_no_raw_content():
    """RunEvent model forbids extra fields — no raw prompts, career data, or model text."""
    event = RunEvent(run_id="test", event_type=RunEventType.RUN_STARTED)
    d = event.model_dump()
    # Safe fields only: run_id, event_type, timestamp, and optional metadata
    assert "prompt" not in d
    assert "career" not in d  # noqa: PD011 — checking for absence, not membership
    assert "model_text" not in d  # noqa: PD011
    assert "credentials" not in d  # noqa: PD011
    assert "headers" not in d  # noqa: PD011


def test_run_event_rejects_extra_fields():
    with pytest.raises(ValueError):
        RunEvent(run_id="t", event_type=RunEventType.RUN_STARTED, secret="leak")


# ── test 11: file permissions ──

@pytest.mark.asyncio
async def test_receipt_files_mode_0600_and_dir_0700():
    with tempfile.TemporaryDirectory() as tmp:
        writer = ArtifactWriter(root=Path(tmp))
        fake = FakeModelClient(responses=[_fake_response("ok")])
        request = RunRequest(system_message="sys", user_message="usr")
        result = await run_stage0(request, model=fake, artifact_writer=writer)

        assert result.receipt_complete
        run_dir = Path(result.artifact_dir)
        assert run_dir.exists()

        # dir mode 0700
        dir_mode = stat.S_IMODE(os.stat(run_dir).st_mode)
        assert dir_mode == 0o700

        # receipt files mode 0600
        for fname in [
            "events.jsonl",
            "manifest.json",
            "context.json",
            "transcript.json",
            "result.json",
            "review.md",
        ]:
            fp = run_dir / fname
            assert fp.exists(), f"missing: {fname}"
            file_mode = stat.S_IMODE(os.stat(fp).st_mode)
            assert file_mode == 0o600, f"{fname}: expected 0600, got {oct(file_mode)}"


# ── test 12: manifest hash stability ──

def test_manifest_hash_stable():
    writer = ArtifactWriter()
    h1 = writer.stable_manifest_hash("abc", "2026-01-01T00:00:00Z")
    h2 = writer.stable_manifest_hash("abc", "2026-01-01T00:00:00Z")
    assert h1 == h2

    h3 = writer.stable_manifest_hash("def", "2026-01-01T00:00:00Z")
    assert h1 != h3


# ── test 13: safe failure RunResult ──

@pytest.mark.asyncio
async def test_model_failure_produces_safe_result():
    fake = FakeModelClient(responses=[_fake_failure("provider timed out")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake)

    assert result.exit_reason == RunExitReason.MODEL_FAILED
    assert result.safe_failure
    assert "timed out" in result.safe_failure
    assert result.final_text == ""


# ── test 14: observer failure isolation ──

@pytest.mark.asyncio
async def test_observer_error_does_not_break_run():
    class FailingObserver:
        def on_event(self, event: RunEvent) -> None:
            raise RuntimeError("observer crash")

    fake = FakeModelClient(responses=[_fake_response("survived")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake, observers=[FailingObserver()])

    assert result.exit_reason == RunExitReason.COMPLETED
    assert result.final_text == "survived"
    # One error per emit call (5 events: run_started, context_prepared, model_started, model_completed, run_completed)
    assert len(result.observer_errors) == 5
    assert "observer crash" in result.observer_errors[0]


# ── test 15: artifact-write failure (receipt_complete=false) ──

@pytest.mark.asyncio
async def test_artifact_write_failure_preserves_model_outcome():
    """When receipt writing fails, the model outcome is preserved but receipt_complete is false."""

    class BrokenWriter:
        def create_run_dir(self, run_id):
            p = Path(tempfile.mkdtemp()) / run_id
            p.mkdir(parents=True, exist_ok=True)
            return p

        def write_receipt(self, run_dir, filename, content):
            raise OSError("disk full")

        def write_all_receipts(self, run_id, events, manifest, context, transcript, result, review_md):
            raise OSError("disk full")

        def stable_manifest_hash(self, run_id, started_at):
            return "deadbeef"

    fake = FakeModelClient(responses=[_fake_response("still good")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake, artifact_writer=BrokenWriter())

    assert result.exit_reason == RunExitReason.COMPLETED
    assert result.final_text == "still good"
    assert result.receipt_complete is False
    assert len(result.artifact_errors) == 1
    assert "disk full" in result.artifact_errors[0]


# ── test 16: fake CLI exit 0 with 6 receipt files ──

def test_fake_cli_creates_six_receipt_files():
    """End-to-end: fake CLI exits 0 and produces all 6 receipt files."""
    with tempfile.TemporaryDirectory() as tmp:
        artifacts_dir = Path(tmp) / "runs"
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "haxjobs.cli",
                "experiment",
                "review-job",
                "--job",
                "49",
                "--fake",
                "--career-fixture",
                "tests/fixtures/job_review/career.json",
                "--artifacts-dir",
                str(artifacts_dir),
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src:."},
            cwd=os.getcwd(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "FAKE_STAGE0_RESPONSE" in result.stdout
        assert "Run ID:" in result.stdout

        # Find the run directory
        run_dirs = list(artifacts_dir.iterdir())
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        for fname in [
            "events.jsonl",
            "manifest.json",
            "context.json",
            "transcript.json",
            "result.json",
            "review.md",
        ]:
            fp = run_dir / fname
            assert fp.exists(), f"missing: {fname}"
            assert fp.stat().st_size > 0, f"empty: {fname}"


# ── test 17: no network calls ──

@pytest.mark.asyncio
async def test_fake_model_does_not_call_network():
    fake = FakeModelClient(responses=[_fake_response("offline")])
    request = RunRequest(system_message="sys", user_message="usr")
    result = await run_stage0(request, model=fake)

    assert result.exit_reason == RunExitReason.COMPLETED
    assert result.final_text == "offline"

    # The fake model records requests but never touches network
    assert len(fake.requests) == 1
    assert fake.requests[0].messages[0].role == "system"


# ── test 18: no haxjobs.agent imports ──

def test_no_agent_imports():
    """Greenfield modules must not import haxjobs.agent."""
    # Clear any cached imports
    for mod in list(sys.modules):
        if "haxjobs.agent" in mod and mod != "haxjobs.agent_core":
            del sys.modules[mod]

    # Import greenfield modules
    import haxjobs.model
    import haxjobs.agent_core
    import haxjobs.employment
    import haxjobs.interfaces

    agent_modules = [
        m for m in sys.modules
        if m.startswith("haxjobs.agent") and not m.startswith("haxjobs.agent_core")
    ]
    assert not agent_modules, f"agent modules leaked: {agent_modules}"
