"""Employment tool definitions — get_job, inspect_job_source, record_job_assessment.

Each tool gets a Pydantic input/output model, a description, an async handler wrapping
a plain Python action from job_actions.py, and effect_kind/retry_safe metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from haxjobs.agent_core.tools import EffectKind, ToolDefinition, ToolExecutionContext, ToolRegistry
from haxjobs.employment import job_actions
from haxjobs.employment.job_source import JobSourceFetcher
from haxjobs.employment.store import CareerStore

logger = logging.getLogger(__name__)


# ── Input/Output models ──

class GetJobInput(BaseModel):
    job_id: str = Field(description="The job ID, e.g. 'job-49' or 'job-328'")


class GetJobOutput(BaseModel):
    ok: bool
    job_id: str = ""
    title: str = ""
    employer_name: str = ""
    location: str = ""
    description: str = ""
    description_complete: bool = False
    source_status: str = ""
    latest_recommendation: str = ""
    error: str = ""


class InspectJobSourceInput(BaseModel):
    job_id: str = Field(description="The job ID to inspect, e.g. 'job-49'")


class InspectJobSourceOutput(BaseModel):
    ok: bool
    job_id: str = ""
    visible_text: str = ""
    content_type: str = ""
    description_complete: bool | None = None
    status: str = ""
    error: str = ""


class ConstraintCheckInput(BaseModel):
    constraint_id: str
    constraint_text: str
    result: Literal["pass", "fail", "unknown"]


class RecordJobAssessmentInput(BaseModel):
    job_id: str = Field(description="The job ID being assessed")
    track_id: str = Field(description="The career track ID")
    recommendation: Literal["pursue", "consider", "skip", "needs_more_information"] = Field(
        description="Assessment recommendation"
    )
    summary: str = Field(description="Natural language summary of the assessment")
    constraint_checks: list[ConstraintCheckInput] = Field(
        default_factory=list,
        description="List of constraint checks (pass/fail/unknown)",
    )
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class RecordJobAssessmentOutput(BaseModel):
    ok: bool
    assessment_id: str = ""
    recommendation: str = ""
    sequence: int | None = None
    replay: bool = False  # True if this was an idempotent replay
    error: str = ""


# ── Descriptions ──

_GET_JOB_DESC = """Retrieve a saved job from the employment store by job ID.

Use this tool when the user asks about a specific job. Returns the job's title,
employer, location, description, and the latest assessment for the active career track.

Arguments:
  job_id: The job ID, e.g. 'job-49' or 'job-328'
"""

_INSPECT_SOURCE_DESC = """Inspect the current source page for a saved job.

Use this tool when the stored job description is thin, incomplete, or may be stale.
The tool resolves the source URL from the saved job — you do not supply a URL.

Returns the current visible text from the job listing page.

Arguments:
  job_id: The job ID to inspect, e.g. 'job-328'
"""

_RECORD_ASSESSMENT_DESC = """Record a typed assessment for a job against the active career track.

Use this tool after reviewing a job and its evidence. The assessment is append-only.
Use recommendations: pursue (strong fit), consider (possible fit), skip (mismatch),
needs_more_information (insufficient evidence).

Arguments:
  job_id: The job ID being assessed
  track_id: The active career track ID
  recommendation: pursue, consider, skip, or needs_more_information
  summary: Natural language explanation of the assessment
  constraint_checks: List of hard constraint checks with pass/fail/unknown results
  strengths: Skills and experience that match
  gaps: Missing or weak areas
  unknowns: Things that cannot be determined
  evidence_ids: Evidence items that support this assessment
"""


# ── Tool registry builder ──

def build_employment_tool_registry(
    store: CareerStore,
    track_id: str,
    fetcher: JobSourceFetcher | None = None,
) -> tuple[ToolRegistry, tuple[str, ...]]:
    """Build a ToolRegistry with get_job, inspect_job_source, and record_job_assessment.

    Returns (registry, active_tool_names).
    """
    registry = ToolRegistry()
    _fetcher = fetcher or JobSourceFetcher()

    # ── get_job ──
    async def get_job_handler(input_obj: GetJobInput, ctx: ToolExecutionContext) -> dict[str, Any]:
        job = job_actions.get_job(store, input_obj.job_id)
        if job is None:
            return GetJobOutput(
                ok=False,
                job_id=input_obj.job_id,
                error=f"Job not found: {input_obj.job_id}",
            ).model_dump()

        latest = job_actions.get_latest_assessment(store, job.job_id, track_id)

        return GetJobOutput(
            ok=True,
            job_id=job.job_id,
            title=job.title,
            employer_name=job.employer_name or "",
            location=job.location,
            description=job.description,
            description_complete=job.description_complete,
            source_status=job.source_status,
            latest_recommendation=latest.recommendation if latest else "",
        ).model_dump()

    registry.register(ToolDefinition(
        name="get_job",
        description=_GET_JOB_DESC,
        input_model=GetJobInput,
        output_model=GetJobOutput,
        handler=get_job_handler,
        effect_kind=EffectKind.READ,
        retry_safe=True,
    ))

    # ── inspect_job_source ──
    async def inspect_handler(input_obj: InspectJobSourceInput, ctx: ToolExecutionContext) -> dict[str, Any]:
        result = await job_actions.inspect_job_source(
            store=store,
            job_id=input_obj.job_id,
            fetcher=_fetcher,
        )
        return InspectJobSourceOutput(
            ok=result.ok,
            job_id=input_obj.job_id,
            visible_text=result.visible_text,
            content_type=result.content_type,
            description_complete=result.description_complete,
            status=result.status,
            error=result.error,
        ).model_dump()

    registry.register(ToolDefinition(
        name="inspect_job_source",
        description=_INSPECT_SOURCE_DESC,
        input_model=InspectJobSourceInput,
        output_model=InspectJobSourceOutput,
        handler=inspect_handler,
        effect_kind=EffectKind.INTERNAL_WRITE,
        retry_safe=True,
    ))

    # ── record_job_assessment ──
    async def record_handler(input_obj: RecordJobAssessmentInput, ctx: ToolExecutionContext) -> dict[str, Any]:
        from haxjobs.employment.schema import ConstraintCheck, JobAssessment

        assessment = JobAssessment(
            job_id=input_obj.job_id,
            track_id=input_obj.track_id,
            tool_call_id=ctx.call_id,
            recommendation=input_obj.recommendation,
            summary=input_obj.summary,
            constraint_checks=[
                ConstraintCheck(
                    constraint_id=c.constraint_id,
                    constraint_text=c.constraint_text,
                    result=c.result,
                )
                for c in input_obj.constraint_checks
            ],
            strengths=list(input_obj.strengths),
            gaps=list(input_obj.gaps),
            unknowns=list(input_obj.unknowns),
            evidence_ids=list(input_obj.evidence_ids),
        )

        try:
            result = job_actions.record_assessment(store, assessment)
        except ValueError as exc:
            return RecordJobAssessmentOutput(
                ok=False,
                error=str(exc),
            ).model_dump()

        if isinstance(result, job_actions.IdempotencyConflict):
            return RecordJobAssessmentOutput(
                ok=False,
                assessment_id=result.existing_assessment_id,
                recommendation=result.existing_recommendation,
                error=f"Idempotency conflict: {result.conflict_detail}",
            ).model_dump()

        return RecordJobAssessmentOutput(
            ok=True,
            assessment_id=result.assessment_id,
            recommendation=result.recommendation,
            sequence=result.sequence,
            replay=result.sequence is not None and result.assessment_id != assessment.assessment_id,
        ).model_dump()

    registry.register(ToolDefinition(
        name="record_job_assessment",
        description=_RECORD_ASSESSMENT_DESC,
        input_model=RecordJobAssessmentInput,
        output_model=RecordJobAssessmentOutput,
        handler=record_handler,
        effect_kind=EffectKind.INTERNAL_WRITE,
        retry_safe=False,
    ))

    active = ("get_job", "inspect_job_source", "record_job_assessment")
    return registry, active
