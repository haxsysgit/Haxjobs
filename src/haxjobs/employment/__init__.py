"""HaxJobs employment layer — career context, evidence rules, and job-review logic."""

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

__all__ = [
    "CareerFixture",
    "EvidenceItem",
    "JobFixture",
    "assemble_job_review_request",
    "build_job_review_system_prompt",
    "build_job_review_user_prompt",
    "load_career_fixture",
    "load_job_fixture",
]
