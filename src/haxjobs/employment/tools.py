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
    # Kept as a compact Plan 004 projection; the full typed projections below
    # are the Plan 005 recall contract.
    latest_recommendation: str = ""
    latest_assessment: dict[str, Any] | None = None
    latest_decision: dict[str, Any] | None = None
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
    code: str = ""
    assessment_id: str = ""
    recommendation: str = ""
    sequence: int | None = None
    replay: bool = False  # True if this was an idempotent replay
    error: str = ""


class RecordJobDecisionInput(BaseModel):
    job_id: str = Field(description="The stable job ID, e.g. 'job-49'")
    label: Literal["apply", "maybe", "save", "skip", "reject"] = Field(
        description="The user's decision label"
    )
    reason: str = Field(
        default="",
        description=(
            "Optional concise user stated reason; leave empty if the user did "
            "not state one"
        ),
    )


class RecordJobDecisionOutput(BaseModel):
    ok: bool
    code: str = ""
    decision_id: str = ""
    job_id: str = ""
    label: str = ""
    reason: str = ""
    sequence: int | None = None
    replay: bool = False
    error: str = ""


# ── Descriptions ──

_GET_JOB_DESC = """Retrieve a saved job from the employment store by job ID.

Use this tool when the user asks about a specific job or what they decided about
one. Returns the job's title, employer, location, description, latest assessment,
and latest user decision for the active career track. If latest_decision is null,
there is no recorded decision for that job and track.

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
  job_id: The job ID being assessed. The active career track is bound by the host.
  recommendation: pursue, consider, skip, or needs_more_information
  summary: Natural language explanation of the assessment
  constraint_checks: List of hard constraint checks with pass/fail/unknown results
  strengths: Skills and experience that match
  gaps: Missing or weak areas
  unknowns: Things that cannot be determined
  evidence_ids: Evidence items that support this assessment
"""

_RECORD_DECISION_DESC = """Record the user's append-only decision about a saved job.

Use this tool ONLY when the user has directly stated their decision about a job
in natural language.

Valid triggers include:
- "yeah, skip it"
- "save this one"
- "I want to apply"
- "maybe, I'll think about it"
- "actually no, I'll apply after all" (correction: appends a new decision)

DO NOT call this tool:
- To record your own recommendation as if the user decided it
- When the user has not yet expressed a decision
- When it is unclear which job the user is referring to: ask first

Allowed labels are apply, maybe, save, skip, and reject. The apply label records
intent only: it does not submit, contact, send, queue, create a pack, or imply
that an application happened. Leave reason empty unless the user stated a
concise reason; never invent one. The active track and source user message are
provided by the runtime, not by the model.

Arguments:
  job_id: The saved job ID
  label: The user's directly stated decision
  reason: A concise reason stated by the user, or an empty string
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
        projection = job_actions.get_job(store, input_obj.job_id, track_id)
        if projection is None:
            # Keep failures in the standard top-level envelope. The job ID is
            # model input, not a safe diagnostic to copy into public errors.
            return {
                "ok": False,
                "code": "job_not_found",
                "error": "job lookup failed",
            }

        latest = projection["latest_assessment"]
        return GetJobOutput(
            ok=True,
            job_id=projection["job_id"],
            title=projection["title"],
            employer_name=projection["employer_name"] or "",
            location=projection["location"],
            description=projection["description"],
            description_complete=projection["description_complete"],
            source_status=projection["source_status"],
            latest_recommendation=latest["recommendation"] if latest else "",
            latest_assessment=latest,
            latest_decision=projection["latest_decision"],
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
        if not result.ok:
            # SourceObservation diagnostics stay local to the action. Never
            # place fetched/provider exception text in the tool envelope.
            return {
                "ok": False,
                "code": "source_observation_failed",
                "error": "source observation failed",
            }
        return InspectJobSourceOutput(
            ok=True,
            job_id=input_obj.job_id,
            visible_text=result.visible_text,
            content_type=result.content_type,
            description_complete=result.description_complete,
            status=result.status,
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
            track_id=track_id,
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
        except ValueError:
            # Action validation details can contain job/provider data. The
            # public tool contract exposes only a stable safe category.
            return {
                "ok": False,
                "code": "assessment_invalid",
                "error": "assessment could not be recorded",
            }

        if isinstance(result, job_actions.IdempotencyConflict):
            return {
                "ok": False,
                "code": "idempotency_conflict",
                "error": f"Idempotency conflict: {result.conflict_detail}",
            }

        return RecordJobAssessmentOutput(
            ok=True,
            assessment_id=result.assessment_id,
            recommendation=result.recommendation,
            sequence=result.sequence,
            replay=result.replayed,
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

    # ── record_job_decision ──
    async def decision_handler(
        input_obj: RecordJobDecisionInput,
        ctx: ToolExecutionContext,
    ) -> dict[str, Any]:
        from haxjobs.employment.schema import JobDecision

        if job_actions.get_job(store, input_obj.job_id) is None:
            return {
                "ok": False,
                "code": "tool_failed",
                "error": "decision could not be recorded",
            }

        decision = JobDecision(
            job_id=input_obj.job_id,
            track_id=track_id,
            tool_call_id=ctx.call_id,
            source_user_message_id=ctx.user_message_id,
            label=input_obj.label,
            reason=input_obj.reason,
        )
        try:
            result = job_actions.record_decision(store, decision)
        except ValueError:
            return {
                "ok": False,
                "code": "tool_failed",
                "error": "decision could not be recorded",
            }

        if isinstance(result, job_actions.IdempotencyConflict):
            return {
                "ok": False,
                "code": "idempotency_conflict",
                "error": "idempotency conflict",
            }

        return RecordJobDecisionOutput(
            ok=True,
            decision_id=result.decision_id,
            job_id=result.job_id,
            label=result.label,
            reason=result.reason,
            sequence=result.sequence,
            replay=result.replayed,
        ).model_dump()

    registry.register(ToolDefinition(
        name="record_job_decision",
        description=_RECORD_DECISION_DESC,
        input_model=RecordJobDecisionInput,
        output_model=RecordJobDecisionOutput,
        handler=decision_handler,
        effect_kind=EffectKind.INTERNAL_WRITE,
        retry_safe=False,
    ))

    active = (
        "get_job",
        "inspect_job_source",
        "record_job_assessment",
        "record_job_decision",
    )
    return registry, active
