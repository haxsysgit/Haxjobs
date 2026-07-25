"""HaxJobs employment layer — career context, evidence rules, job actions."""

from haxjobs.employment.composition import compose_session
from haxjobs.employment.fixtures import (
    CareerFixture,
    EvidenceItem as FixtureEvidenceItem,
    JobFixture,
    load_career_fixture,
    load_job_fixture,
)
from haxjobs.employment.host import EmploymentHost, EmploymentSetupError
from haxjobs.employment.job_actions import (
    get_job,
    record_assessment,
    record_decision,
)
from haxjobs.employment.job_source import JobSourceFetcher, SourceObservation
from haxjobs.employment.schema import (
    CareerTrack,
    EvidenceItem,
    HardConstraint,
    Job,
    JobAssessment,
    JobDecision,
    Person,
    Preference,
    Skill,
    SkillEvidence,
    SkillGap,
)
from haxjobs.employment.store import CareerStore
from haxjobs.employment.tools import build_employment_tool_registry

__all__ = [
    "CareerFixture",
    "CareerStore",
    "CareerTrack",
    "EmploymentHost",
    "EmploymentSetupError",
    "EvidenceItem",
    "FixtureEvidenceItem",
    "HardConstraint",
    "Job",
    "JobAssessment",
    "JobDecision",
    "JobFixture",
    "JobSourceFetcher",
    "Person",
    "Preference",
    "Skill",
    "SkillEvidence",
    "SkillGap",
    "SourceObservation",
    "build_employment_tool_registry",
    "compose_session",
    "get_job",
    "load_career_fixture",
    "load_job_fixture",
    "record_assessment",
    "record_decision",
]
