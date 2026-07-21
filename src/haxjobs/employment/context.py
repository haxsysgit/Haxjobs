"""Employment context assembly — select career facts from CareerStore for each turn.

Plan 003 Phase 6: volatile career context projected into the model request,
never copied into session history.
"""

from __future__ import annotations

import json
from typing import Any

from haxjobs.model.types import ModelMessage

# ── Stable Hax identity ──

_HAX_IDENTITY = """You are Hax, a career agent. You help people get interviews and become more employable.
You speak naturally, like a helpful colleague who knows the market — not a recruiter, not an automated scorer, not an academic reviewer.

Your job is to give honest, evidence-based career guidance. You are not here to sell roles or to generate generic encouragement."""

_TRUTH_RULES = """Follow these rules in every response:

1. Never invent skills, metrics, experience, contacts, or company facts. If you do not know something, say so.
2. Distinguish clearly between supported facts, user-reported claims, your own inferences, and genuine unknowns.
3. Check hard constraints first: role type, primary language, location, and any non-negotiable requirements the user has set. If a hard constraint fails, say so directly before discussing softer fit.
4. When evidence is thin, do not guess. Explain what information is missing and what the next useful check would be.
5. Return a natural answer, not a scorecard. No numeric scores, no verdict labels, no tables of pros and cons."""

_CONVERSATION_INSTRUCTIONS = """You are having a conversation with the user about their career. You have access to their career profile, skills, evidence, constraints, and preferences.

You can use the inspect_job_source tool to look up job descriptions from trusted sources when the user asks about a specific job reference.

Stay focused on the user's actual career direction and evidence. Do not fabricate details about jobs or companies."""


def build_system_prompt() -> str:
    """Assemble the stable system prompt for employment conversations."""
    return "\n\n".join([_HAX_IDENTITY, _TRUTH_RULES, _CONVERSATION_INSTRUCTIONS])


def build_career_context(
    person: dict[str, Any],
    track: dict[str, Any],
    skills_tree: dict[str, Any],
    skills_flat: list[dict[str, Any]],
    evidence_by_skill: dict[str, list[dict[str, Any]]],
    gaps: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
) -> list[ModelMessage]:
    """Build volatile career context messages for the current turn.

    These are projected into the model request but never stored in session history.
    """
    blocks: list[str] = []

    # Person profile
    blocks.append("## Career Profile\n")
    blocks.append(f"**Name:** {person.get('name', 'Unknown')}")
    blocks.append(f"**Location:** {person.get('location', 'Unknown')}")
    if person.get("work_authorization"):
        blocks.append(f"**Work Authorization:** {person['work_authorization']}")
    if person.get("notice_period"):
        blocks.append(f"**Notice Period:** {person['notice_period']}")
    if person.get("salary_range"):
        blocks.append(f"**Salary Range:** {person['salary_range']}")

    # Active track
    blocks.append(f"\n## Active Career Track: {track.get('name', 'Unknown')}")
    target_roles = _parse_json_list(track.get("target_role_families", "[]"))
    if target_roles:
        blocks.append(f"**Target Roles:** {', '.join(target_roles)}")

    # Hard constraints
    if constraints:
        blocks.append("\n## Hard Constraints\n")
        for c in constraints:
            blocks.append(f"- {c['constraint_text']}")

    # Preferences
    if preferences:
        blocks.append("\n## Preferences\n")
        for p in preferences:
            weight = p.get("weight", "strong")
            blocks.append(f"- {p['key']}: {p['value']} ({weight})")

    # Skills with proficiency and evidence
    blocks.append("\n## Skills\n")
    for skill in skills_flat:
        prof = skill.get("proficiency", "working")
        parent = f" (parent: {skill['parent_skill_id']})" if skill.get("parent_skill_id") else ""
        blocks.append(f"- **{skill['name']}** [{prof}]{parent}")

        # Evidence linked to this skill
        ev_items = evidence_by_skill.get(skill["skill_id"], [])
        if ev_items:
            blocks.append("  Evidence:")
            for ev in ev_items:
                blocks.append(f"    - {ev['label']} (source: {ev['source']}, verified: {ev.get('verified_at', 'never')})")

    # Skill gaps
    if gaps:
        blocks.append("\n## Skill Gaps\n")
        for g in gaps:
            note = f" — {g['note']}" if g.get("note") else ""
            blocks.append(f"- {g['skill_name']} → target: {g['target_proficiency']}{note}")

    context_text = "\n".join(blocks)
    return [ModelMessage(role="system", content=context_text)]


def _parse_json_list(raw: str | list | None) -> list[str]:
    """Parse a JSON list string or return the list directly."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
