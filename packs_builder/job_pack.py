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


PACK_FILE_NAMES = (
    "fit_report.md",
    "cover_letter.md",
    "field_answers.md",
    "interview_questions.md",
    "telegram_summary.md",
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
        cv_variant: Metadata from cv_variants.registry.build_pack_cv_metadata.
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
        "telegram_summary.md": _render_telegram_summary(job, evaluation, cv_variant),
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
    if not cv_pdf.startswith("cv_variants/") or not cv_html.startswith("cv_variants/"):
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
        **cv_variant,
    }


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
    strongest = _sentence_list(evaluation.get("strongest_matches", []), "Python backend work")
    gaps = _sentence_list(evaluation.get("major_gaps", []), "I can close the remaining gaps quickly")
    name = profile.get("name", "Arinze Elenasulu")
    return f"""# Cover letter draft

Hi {job.get('company', 'there')} team,

I'm interested in the {_job_title(job)} role because it lines up with the kind of systems I like building: useful backend services, clean APIs, and practical automation that helps people move faster.

My closest matches are {strongest}. The reusable CV variant for this application is {cv_variant['recommended_cv_variant']}, so the CV stays consistent while this letter focuses on the role.

One thing I would be ready to discuss is {gaps}. I care about being honest on that, but I also learn quickly and prefer shipping working software over hiding behind buzzwords.

Best,
{name}
"""


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


def _render_telegram_summary(job: dict[str, Any], evaluation: dict[str, Any], cv_variant: dict[str, Any]) -> str:
    return f"""{job.get('company', 'Unknown company')} - {_job_title(job)}
Score: {evaluation.get('fit_score', 'unknown')}% ({evaluation.get('level_name', 'unclassified')})
CV: {cv_variant['recommended_cv_variant']}
Apply: {_apply_link(job)}
Why: {_sentence_list(evaluation.get('strongest_matches', []), 'good backend overlap')}
Gap: {_sentence_list(evaluation.get('major_gaps', []), 'check the JD carefully before applying')}
Next: review pack, then apply manually or approve a safe assisted flow.
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
