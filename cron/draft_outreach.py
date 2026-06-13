#!/usr/bin/env python3
"""Template-based outreach message drafter — zero LLM.

Generates personalized outreach messages by filling templates with
job details and Arinze's profile facts. Runs on Archilles (SSH OK).

Usage:
  python3 cron/draft_outreach.py              # Draft for all high-fit jobs
  python3 cron/draft_outreach.py --job 42     # Single job
  python3 cron/draft_outreach.py --dry-run    # Preview only, don't save
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import schema
from db.outreach import (
    get_jobs_for_outreach,
    get_contacts_for_job,
    insert_draft,
    get_drafts,
)


# ── Message templates ──────────────────────────────────────────────
# Templates fill in: {name}, {role}, {company}, {match_points}, {score}

LINKEDIN_CONNECT_NOTE = """Hi {name},

I came across the {role} role at {company} and it aligns well with my background — I scored a {score}% fit based on the JD.

{intro_line}

Would be great to connect and learn more about the team.

Best,
Arinze"""

INMAIL_SHORT = """Subject: {role} role at {company}

Hi {name},

I'm a Python backend engineer in London with hands-on experience building production APIs, AI-integrated SaaS, and agentic automation systems.

I noticed the {role} opening at {company}. My background aligns on:
{match_bullets}

{closing_line}

Would you be open to a quick chat?

Arinze Elenasulu
linkedin.com/in/arinze-elenasulu"""

RECRUITER_NOTE = """Hi {name},

I'm interested in the {role} position at {company} — I hit {score}% on the fit score based on the role requirements.

My closest matches: {match_summary}

I'd love to chat about whether I'd be a good fit for the team. Let me know if you have 10 minutes this week.

Thanks,
Arinze"""


# ── Profile facts for message personalization ──────────────────────

PROFILE_INTRO_LINES = [
    "Over the past 2+ years I've built backend systems at Vigilis, shipped an AI-powered data tool for a food business, and published open-source tools for AI agent governance (Haxaml, FRAME).",
    "My recent work includes building pharmacy operations software at Vigilis, shipping an AI analytics tool for a food business, and maintaining a multi-agent automation platform (Archilles).",
    "I've spent the last 2 years building production Python backends, integrating AI/LLMs into real products, and publishing tools used by AI engineers (Haxaml on PyPI, FRAME architecture).",
]

PROFILE_CLOSING_LINES = [
    "I'm on a Graduate visa (no immediate sponsorship needed) and ready to start.",
    "Based in London, available for hybrid/remote, and can start quickly on a Graduate visa.",
    "London-based, Graduate visa sorted — I can hit the ground running.",
]


def pick_match_bullets(matches_json: str, max_bullets: int = 3) -> list[str]:
    """Extract strongest matches and format as bullets."""
    try:
        matches = json.loads(matches_json) if isinstance(matches_json, str) else matches_json
    except (json.JSONDecodeError, TypeError):
        return ["Python backend engineering", "Production API development", "AI/LLM integration"]

    bullets = []
    for m in matches[:max_bullets]:
        bullets.append(f"- {m}")
    return bullets if bullets else ["- Python backend engineering"]


def pick_match_summary(matches_json: str) -> str:
    """Short comma-separated match summary."""
    try:
        matches = json.loads(matches_json) if isinstance(matches_json, str) else matches_json
    except (json.JSONDecodeError, TypeError):
        return "Python backend, API development, AI integration"

    return ", ".join(m[:60] for m in matches[:3])


def pick_rotating(items: list[str], seed: int) -> str:
    """Pick from a list using a seed for variety."""
    return items[seed % len(items)]


def draft_for_job(job: dict, save: bool = True) -> list[int]:
    """Generate outreach drafts for a single job. Returns list of draft IDs."""
    job_id = job["id"]
    title = job.get("title", "Software Engineer")
    company = job.get("company", "the team")
    score = job.get("fit_score", 0)
    matches = job.get("strongest_matches", "[]")

    match_bullets = pick_match_bullets(matches)
    match_summary = pick_match_summary(matches)
    intro_line = pick_rotating(PROFILE_INTRO_LINES, job_id)
    closing_line = pick_rotating(PROFILE_CLOSING_LINES, job_id)

    draft_ids = []

    # Draft 1: Generic connection note (no specific contact needed)
    note_text = LINKEDIN_CONNECT_NOTE.format(
        name="",
        role=title,
        company=company,
        score=score,
        intro_line=intro_line,
    )
    if save:
        did = insert_draft(job_id, f"{title} at {company} — Connect", note_text)
        draft_ids.append(did)

    # Draft 2: Full InMail format
    inmail_text = INMAIL_SHORT.format(
        name="",
        role=title,
        company=company,
        match_bullets="\n".join(match_bullets),
        closing_line=closing_line,
    )
    if save:
        did = insert_draft(job_id, f"{title} at {company} — InMail", inmail_text)
        draft_ids.append(did)

    # Draft 3: Recruiter-specific note
    recruiter_text = RECRUITER_NOTE.format(
        name="",
        role=title,
        company=company,
        score=score,
        match_summary=match_summary,
    )
    if save:
        did = insert_draft(job_id, f"{title} at {company} — Recruiter", recruiter_text)
        draft_ids.append(did)

    return draft_ids


def main(save: bool = True, job_id: int | None = None):
    schema.init()

    if job_id:
        # Load single job
        import sqlite3
        conn = sqlite3.connect("state/pipeline.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT j.id, j.title, j.company, j.location, j.source_url,
                      e.fit_score, e.fit_verdict, e.strongest_matches, e.major_gaps,
                      e.summary, j.outreach_status
               FROM jobs j
               JOIN evaluations e ON j.id = e.job_id
               WHERE j.id = ?""",
            (job_id,),
        ).fetchone()
        conn.close()
        jobs = [dict(row)] if row else []
    else:
        jobs = get_jobs_for_outreach(min_score=75)

    if not jobs:
        print("No jobs found for outreach drafting")
        return

    total_drafts = 0
    for job in jobs:
        job_id = job["id"]
        title = job.get("title", "")[:50]
        company = job.get("company", "")
        score = job.get("fit_score", 0)
        status = job.get("outreach_status", "none")

        print(f"{score}% | {title} at {company}")

        if save:
            draft_ids = draft_for_job(job, save=True)
            print(f"  {len(draft_ids)} drafts created")
            total_drafts += len(draft_ids)

            # Mark job as having drafts
            from db.outreach import mark_job_outreach_status
            mark_job_outreach_status(job_id, "drafted")
        else:
            draft_ids = draft_for_job(job, save=False)
            print(f"  {len(draft_ids)} drafts previewed")

    if save:
        print(f"\nTotal: {total_drafts} drafts for {len(jobs)} jobs")

        # Show summary
        drafts = get_drafts("draft")
        print(f"Pending review: {len(drafts)} drafts")


if __name__ == "__main__":
    job_arg = None
    dry_run = "--dry-run" in sys.argv
    save = not dry_run

    for i, arg in enumerate(sys.argv):
        if arg == "--job" and i + 1 < len(sys.argv):
            job_arg = int(sys.argv[i + 1])
            break

    main(save=save, job_id=job_arg)
