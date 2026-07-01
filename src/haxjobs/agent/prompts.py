"""Named prompt templates. Reusable across evaluation, onboarding, wizard."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    system: str
    user: str  # template with {variables}


PROMPTS: dict[str, PromptTemplate] = {
    "evaluate_job": PromptTemplate(
        system="You are a job-candidate fit evaluator. Score from 0-100. Be honest.",
        user="Profile:\n{profile_json}\n\nJob:\n{job_json}\n\nEvaluate fit.",
    ),
    "extract_cv": PromptTemplate(
        system="Extract structured profile data from a CV. Return valid JSON only.",
        user="CV text:\n{cv_text}\n\nExtract: name, email, phone, skills, experience, education, projects.",
    ),
    "wizard_question": PromptTemplate(
        system="Generate one targeted question to refine a job search profile. Be specific — no generic questions.",
        user="Current profile:\n{profile_json}\n\nGap areas: {gaps}\n\nGenerate one question.",
    ),
}


def get_prompt(name: str, **variables) -> tuple[str, str]:
    """Return (system, user) with variables filled."""
    t = PROMPTS[name]
    return t.system, t.user.format(**variables)
