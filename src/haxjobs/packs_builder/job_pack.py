"""Markdown-first per-job application pack builder.

The builder creates only job-specific prep material. It references one reusable
CV variant through metadata and never writes a PDF, HTML, or job-specific CV.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_TEMPLATE_ROOT = ROOT / "application_templates"


PACK_FILE_NAMES = (
    "fit_report.md",
    "cover_letter.md",
    "field_answers.md",
    "interview_questions.md",
    "metadata.json",
)


def build_job_pack(
    job: dict[str, Any],
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    cv_variant: dict[str, Any],
    output_root: str | Path = "packs",
) -> dict[str, Any]:
    """Create a per-job markdown pack that references a reusable CV variant.

    Args:
        job: Job row or normalized job dict.
        evaluation: Fit evaluation dict from the evaluator.
        profile: Truthful profile/contact dict.
        cv_variant: Metadata from haxjobs.cv_variants.registry.build_pack_cv_metadata.
        output_root: Root directory where the pack directory should be written.

    Returns:
        A small manifest with the pack directory and created file paths.
    """
    _validate_reusable_cv_metadata(cv_variant)

    pack_dir = Path(output_root) / _pack_dir_name(job)
    pack_dir.mkdir(parents=True, exist_ok=True)

    metadata = _build_metadata(job, evaluation, profile, cv_variant)
    files = {
        "fit_report.md": _render_fit_report(job, evaluation, cv_variant),
        "cover_letter.md": _render_cover_letter(job, evaluation, profile, cv_variant),
        "field_answers.md": _render_field_answers(job, evaluation, profile, cv_variant),
        "interview_questions.md": _render_interview_questions(job, evaluation),
        "metadata.json": json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    }

    written_paths: list[str] = []
    for file_name in PACK_FILE_NAMES:
        path = pack_dir / file_name
        path.write_text(files[file_name])
        written_paths.append(str(path))

    return {
        "pack_dir": str(pack_dir),
        "files": written_paths,
        "metadata": metadata,
    }


def _validate_reusable_cv_metadata(cv_variant: dict[str, Any]) -> None:
    if cv_variant.get("pack_owns_cv") is not False:
        raise ValueError("pack_owns_cv must be False for reusable CV variants")

    required = {"recommended_cv_variant", "role_family", "cv_pdf", "cv_html"}
    missing = required - set(cv_variant)
    if missing:
        raise ValueError(f"CV variant metadata missing fields: {sorted(missing)}")

    cv_pdf = str(cv_variant["cv_pdf"])
    cv_html = str(cv_variant["cv_html"])
    if not cv_pdf.startswith("src/haxjobs/cv_variants/") or not cv_html.startswith("src/haxjobs/cv_variants/"):
        raise ValueError("CV files must be referenced from cv_variants/")


def _pack_dir_name(job: dict[str, Any]) -> str:
    job_id = str(job.get("id") or job.get("job_id") or "job")
    company = _slug(job.get("company") or "unknown_company")
    title = _slug(job.get("title") or "unknown_role")
    return f"{job_id}_{company}_{title}"


def _slug(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] or "unknown"


def _build_metadata(
    job: dict[str, Any],
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    cv_variant: dict[str, Any],
) -> dict[str, Any]:
    role_family = _resolve_role_family(job, cv_variant)
    template_path = _cover_letter_template_path(role_family)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "job_id": job.get("id") or job.get("job_id"),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "source_url": job.get("source_url", ""),
        "apply_url": job.get("apply_url") or job.get("source_url", ""),
        "fit_score": evaluation.get("fit_score"),
        "fit_verdict": evaluation.get("fit_verdict", ""),
        "level": evaluation.get("level"),
        "level_name": evaluation.get("level_name", ""),
        "profile_name": profile.get("name", "Arinze Elenasulu"),
        "application_template_id": role_family,
        "cover_letter_template": _relative_template_path(template_path),
        **cv_variant,
    }


def _resolve_role_family(job: dict[str, Any], cv_variant: dict[str, Any]) -> str:
    """Pick the role family that decides which application template to use."""
    return str(
        job.get("role_family")
        or job.get("recommended_cv_variant")
        or cv_variant.get("role_family")
        or cv_variant.get("recommended_cv_variant")
        or "backend_python"
    )


def _cover_letter_template_path(role_family: str) -> Path:
    """Return the cover letter template path for a role family."""
    template_path = APPLICATION_TEMPLATE_ROOT / "cover_letters" / f"{role_family}.md"
    if template_path.exists():
        return template_path
    return APPLICATION_TEMPLATE_ROOT / "cover_letters" / "backend_python.md"


def _relative_template_path(template_path: Path) -> str:
    """Return a stable repo-relative template path for metadata."""
    return str(template_path.relative_to(ROOT))


def _extract_template_body(template_text: str) -> str:
    """Extract only the user-facing body under '## Template'."""
    match = re.search(
        r"^## Template\s*$(.*?)(?=^## \S|\Z)",
        template_text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError("Cover letter template is missing a '## Template' section")
    return match.group(1).strip()


def _hiring_manager_or_team(job: dict[str, Any]) -> str:
    """Use a real hiring contact only if the job payload provides one."""
    manager = str(job.get("hiring_manager") or "").strip()
    return manager if manager else "team"


def _source_context(job: dict[str, Any]) -> str:
    """Describe where the role came from without inventing a source."""
    source = str(job.get("source") or "").strip()
    if source:
        return source
    source_url = str(job.get("source_url") or "").strip()
    return source_url if source_url else "the job listing"


def _company_reason(job: dict[str, Any], evaluation: dict[str, Any]) -> str:
    """Create a truthful, non-generic reason from available job data."""
    jd_text = str(job.get("jd_text") or "").lower()
    if "health" in jd_text or "pharmacy" in jd_text or "health" in str(job.get("company", "")).lower():
        return "the operational and health-adjacent context. I have already built pharmacy workflows where the small details matter"
    if "ai" in jd_text or "llm" in jd_text or "automation" in jd_text:
        return "the practical AI angle. I like AI work most when it becomes useful software, not just a shiny demo"
    summary = str(evaluation.get("summary") or "").strip()
    if summary:
        return summary.rstrip(".")
    return "the way the role seems focused on useful engineering rather than buzzword theatre"


def _evidence_story(role_family: str) -> str:
    """Return role-family evidence from Arinze's confirmed profile."""
    stories = {
        "backend_python": "I built backend workflows at Vigilis and Pharmax around inventory, sales, invoicing, reporting, API design, PostgreSQL, SQLAlchemy, and pytest",
        "fullstack_python_react": "I am backend-first, but HaxJobs gave me real product-surface work across FastAPI, React, TypeScript, dashboard flows, and API integration",
        "ai_engineer_llm": "I built Pharmax AI workflows, used RAGAS for evaluation, trained and fine-tuned transformer models, and built FRAME/Haxaml around AI agent governance",
        "ai_automation_agents": "I use agent infrastructure daily, built Haxaml for AI agent governance, and built HaxJobs as a working automation pipeline rather than a slide-deck idea",
        "junior_software": "I have real engineering time from Vigilis and Aptech, plus a project portfolio that shows I can learn quickly and ship useful work",
        "data_python": "I built data-backed pharmacy workflows, reporting paths, and AI evaluation work with Python, SQL, and RAGAS",
        "platform_backend": "I have worked with Docker, Linux, backend services, structured logging, and long-running agent infrastructure through HaxJobs",
    }
    return stories.get(role_family, stories["backend_python"])


def _gap_note(evaluation: dict[str, Any]) -> str:
    """Turn evaluator gaps into honest cover-letter wording."""
    gaps = _as_list(evaluation.get("major_gaps", []))
    if not gaps:
        return "I do not want to pretend I know every corner of the stack already, but the core engineering patterns here are familiar and I learn quickly."
    gap_text = _sentence_list(gaps, "the remaining stack details")
    return (
        f"I have not had deep production time with every detail in the JD yet, so I will not pretend otherwise. "
        f"One thing to discuss honestly: {gap_text}. "
        f"But the surrounding engineering patterns are familiar: APIs, data flow, testing, debugging, and turning vague requirements into working software. Learning the missing bits should be very manageable."
    )


def _closing_availability(profile: dict[str, Any]) -> str:
    """Return a short availability line if profile data has it."""
    availability = str(profile.get("availability") or "").strip()
    return availability if availability else "I am available to start immediately."


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _render_fit_report(job: dict[str, Any], evaluation: dict[str, Any], cv_variant: dict[str, Any]) -> str:
    matches = _bullet_list(evaluation.get("strongest_matches", []), fallback="No strong matches recorded yet.")
    gaps = _bullet_list(evaluation.get("major_gaps", []), fallback="No major gaps recorded yet.")
    return f"""# Fit report

Role: {_job_title(job)}
Company: {job.get('company', 'Unknown company')}
Fit score: {evaluation.get('fit_score', 'unknown')}%
Verdict: {evaluation.get('fit_verdict', 'Not evaluated')}
Use CV variant: {cv_variant['recommended_cv_variant']}
Apply link: {_apply_link(job)}

## Why this fits
{matches}

## Gaps to handle
{gaps}

## Notes
{evaluation.get('summary', 'No evaluator summary recorded yet.')}
"""


def _render_cover_letter(
    job: dict[str, Any],
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    cv_variant: dict[str, Any],
) -> str:
    """Render the role-family cover letter template with job evidence.

    The template owns tone and structure. This function only fills truthful,
    deterministic slots from the job, evaluation, profile, and CV metadata.
    """
    role_family = _resolve_role_family(job, cv_variant)
    template_path = _cover_letter_template_path(role_family)
    template = _extract_template_body(template_path.read_text())

    slots = {
        "hiring_manager_or_team": _hiring_manager_or_team(job),
        "role_title": _job_title(job),
        "company": str(job.get("company") or "the company"),
        "source_or_context": _source_context(job),
        "jd_match_points": _sentence_list(
            evaluation.get("strongest_matches", []),
            "Python backend APIs, clean data flow, and practical automation",
        ),
        "company_reason": _company_reason(job, evaluation),
        "evidence_story": _evidence_story(role_family),
        "gap_note": _gap_note(evaluation),
        "closing_availability": _closing_availability(profile),
    }

    rendered = template
    for slot, value in slots.items():
        rendered = rendered.replace("{" + slot + "}", value)

    if re.search(r"\{[a-zA-Z0-9_]+\}", rendered):
        raise ValueError(f"Unfilled cover letter slot in {template_path}")
    if "\u2014" in rendered:
        raise ValueError("Cover letter output contains an em dash")

    return "# Cover letter draft\n\n" + rendered.strip() + "\n"


def _render_field_answers(
    job: dict[str, Any], evaluation: dict[str, Any], profile: dict[str, Any], cv_variant: dict[str, Any]) -> str:
    return f"""# Field answers

## Preferred name
{profile.get('name', 'Arinze Elenasulu')}

## Email
{profile.get('email', 'elenasuluarinze@gmail.com')}

## LinkedIn
{profile.get('linkedin', 'https://www.linkedin.com/in/arinze-elenasulu/')}

## Role fit summary
This role is a {evaluation.get('fit_score', 'unknown')}% fit. The strongest overlap is {_sentence_list(evaluation.get('strongest_matches', []), 'Python, backend APIs and practical automation')}.

## CV to upload
Use CV variant: {cv_variant['recommended_cv_variant']}
File reference: {cv_variant['cv_pdf']}

## Application URL
{_apply_link(job)}
"""


def _render_interview_questions(job: dict[str, Any], evaluation: dict[str, Any]) -> str:
    matches = evaluation.get("strongest_matches", []) or ["Python", "backend APIs", "testing"]
    gaps = evaluation.get("major_gaps", []) or ["Any stack area not explicit in the CV"]
    match_questions = "\n".join(f"- How have you used {item} in a real project?" for item in matches[:5])
    gap_questions = "\n".join(f"- How would you handle this gap: {item}?" for item in gaps[:4])
    return f"""# Interview questions

Role: {_job_title(job)}
Company: {job.get('company', 'Unknown company')}

## Likely technical questions
{match_questions}

## Gap questions to prepare
{gap_questions}

## Good questions to ask them
- What does success look like in the first 90 days?
- How is the backend split between new feature work, maintenance and incident work?
- What does the team use for testing, reviews and deployment?
"""


def _job_title(job: dict[str, Any]) -> str:
    return str(job.get("title") or "Unknown role")


def _apply_link(job: dict[str, Any]) -> str:
    return str(job.get("apply_url") or job.get("source_url") or "No apply link recorded")


def _bullet_list(values: Any, fallback: str) -> str:
    items = _as_list(values)
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _sentence_list(values: Any, fallback: str) -> str:
    items = _as_list(values)
    if not items:
        return fallback
    if len(items) == 1:
        return str(items[0])
    return ", ".join(str(item) for item in items[:-1]) + f" and {items[-1]}"


def _as_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values] if values.strip() else []
    if isinstance(values, list):
        return [str(value) for value in values if str(value).strip()]
    return [str(values)]
