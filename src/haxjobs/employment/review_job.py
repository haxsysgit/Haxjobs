"""Job-review instruction strings and context assembly.

Two stable instruction strings: Hax identity/truth rules, and the job-review flow.
The employment host assembles context blocks and creates a frozen RunRequest.
"""

from __future__ import annotations

from haxjobs.agent_core.types import RunRequest
from haxjobs.employment.fixtures import CareerFixture, JobFixture

_HAX_IDENTITY = """You are Hax, a career agent. You help people get interviews and become more employable.
You speak naturally, like a helpful colleague who knows the market — not a recruiter, not an automated scorer, not an academic reviewer.

Your job is to give honest, evidence-based career guidance. You are not here to sell roles or to generate generic encouragement."""

_TRUTH_RULES = """Follow these rules in every response:

1. Never invent skills, metrics, experience, contacts, or company facts. If you do not know something, say so.
2. Distinguish clearly between supported facts, user-reported claims, your own inferences, and genuine unknowns.
3. Check hard constraints first: role type, primary language, location, and any non-negotiable requirements the user has set. If a hard constraint fails, say so directly before discussing softer fit.
4. When evidence is thin, do not guess. Explain what information is missing and what the next useful check would be.
5. Return a natural answer, not a scorecard. No numeric scores, no verdict labels, no tables of pros and cons."""

_JOB_REVIEW_FLOW = """You are reviewing one job opportunity against the user's career direction and evidence.

Review process:
1. Read the user's career direction and hard constraints.
2. Read the user's relevant evidence.
3. Read the job source snapshot carefully.
4. Check hard constraints first. If any fail, explain which ones and why.
5. Then assess fit: what overlaps, what is missing, what is genuinely unknown.
6. If the stored vacancy evidence is too thin for an honest fit judgement, say so plainly and name what information a full source inspection would provide.
7. Explain the strongest overlap, the main blockers, and the most important unknowns.
8. End with clear practical guidance: is this worth pursuing, what should be checked next, and what the user should be aware of."""


def build_job_review_system_prompt() -> str:
    """Assemble the stable system prompt for a job review."""
    return "\n\n".join([_HAX_IDENTITY, _TRUTH_RULES, _JOB_REVIEW_FLOW])


def build_job_review_user_prompt(
    career: CareerFixture,
    job: JobFixture,
) -> str:
    """Assemble the four labelled volatile context blocks in fixed order.

    Blocks:
    1. USER REQUEST — what we're asking Hax to do
    2. CAREER DIRECTION AND CONSTRAINTS — user's target and non-negotiables
    3. RELEVANT EVIDENCE — labelled evidence items from the career fixture
    4. JOB SOURCE SNAPSHOT — the job fixture content and metadata
    """
    blocks: list[str] = []

    # Block 1: User request
    blocks.append(
        "## USER REQUEST\n\n"
        f"Review this job: {job.title} at {job.employer_name or '(employer not stored)'}, "
        f"{job.location}. "
        "Tell me honestly whether it fits my career direction and what I should do next."
    )

    # Block 2: Career direction and constraints
    blocks.append(
        "## CAREER DIRECTION AND CONSTRAINTS\n\n"
        f"**Direction:** {career.career_direction}\n\n"
        f"**Hard constraints:**\n"
        + "\n".join(f"- {c}" for c in career.hard_constraints)
    )

    # Block 3: Relevant evidence
    evidence_lines = ["## RELEVANT EVIDENCE\n"]
    for item in career.evidence:
        evidence_lines.append(
            f"**{item.label}** (source: {item.source})\n{item.content}\n"
        )
    blocks.append("\n".join(evidence_lines))

    # Block 4: Job source snapshot
    warning_lines = ""
    if job.warnings:
        warning_lines = (
            "\n**Source warnings:**\n" + "\n".join(f"- {w}" for w in job.warnings)
        )
    blocks.append(
        "## JOB SOURCE SNAPSHOT\n\n"
        f"**Title:** {job.title}\n"
        f"**Employer:** {job.employer_name or '(not stored)'}\n"
        f"**Location:** {job.location}\n"
        f"**Source:** {job.source_type} ({job.source_status})\n"
        f"**Content type:** {job.description_kind}\n"
        f"**Content complete:** {job.content_complete}\n"
        f"**Observed:** {job.observed_at}\n"
        f"{warning_lines}\n"
        f"**Description:**\n{job.description}"
    )

    return "\n\n".join(blocks)


def assemble_job_review_request(
    career: CareerFixture,
    job: JobFixture,
    run_id: str = "",
) -> RunRequest:
    """Create a frozen RunRequest for a job review.

    The employment host creates this and passes it to the agent core.
    No old evaluation, whole profile, database row, unrelated projects, or company research.
    """
    system = build_job_review_system_prompt()
    user = build_job_review_user_prompt(career=career, job=job)
    kwargs: dict = {
        "system_message": system,
        "user_message": user,
    }
    if run_id:
        kwargs["run_id"] = run_id
    return RunRequest(**kwargs)
