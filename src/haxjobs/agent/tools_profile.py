"""Profile tools — read, write, inspect, and find gaps in the user profile."""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from haxjobs.agent.registry import register
from haxjobs.config import PROFILE_PATH


def _load_profile() -> dict[str, Any] | None:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            return _json.load(f)
    return None


def _get_nested(data: dict, path: str) -> Any:
    parts = path.split(".")
    for p in parts:
        if isinstance(data, dict):
            data = data.get(p)
        elif isinstance(data, list) and p.isdigit():
            idx = int(p)
            data = data[idx] if 0 <= idx < len(data) else None
        else:
            return None
    return data


def _set_nested(data: dict, path: str, value: Any) -> dict:
    parts = path.split(".")
    target = data
    for p in parts[:-1]:
        if isinstance(target, dict):
            target = target.setdefault(p, {})
        elif isinstance(target, list) and p.isdigit():
            idx = int(p)
            while len(target) <= idx:
                target.append({})
            target = target[idx]
        else:
            return data
    if isinstance(target, dict):
        target[parts[-1]] = value
    return data


def profile_read(field_path: str | None = None) -> dict[str, Any]:
    """Read the user profile. If field_path is given, return only that dot-path field."""
    profile = _load_profile()
    if profile is None:
        return {"error": "No profile found. Complete onboarding first."}
    if field_path:
        value = _get_nested(profile, field_path)
        return {field_path: value}
    return {"profile": profile}


def profile_write(field_path: str, value: str) -> dict[str, Any]:
    """Write a value to a specific profile field using dot-path notation."""
    profile = _load_profile()
    if profile is None:
        return {"error": "No profile found. Complete onboarding first."}
    # Parse value — try JSON first, fall back to string
    try:
        parsed = _json.loads(value)
    except (_json.JSONDecodeError, TypeError):
        parsed = value
    profile = _set_nested(profile, field_path, parsed)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        _json.dump(profile, f, indent=2)
    PROFILE_PATH.chmod(0o600)
    return {"ok": True, "field": field_path}


# ponytail: read the schema file on each call so changes are live without restart
SCHEMA_CACHE_PATH = Path(__file__).resolve().parent.parent / "profile" / "profile_schema.json"


def profile_schema() -> dict[str, Any]:
    """Return the HaxJobs profile JSON Schema so the agent knows what fields exist."""
    if SCHEMA_CACHE_PATH.exists():
        with open(SCHEMA_CACHE_PATH) as f:
            return {"schema": _json.load(f)}
    return {"error": "Profile schema file not found"}


register(
    "profile_read",
    {
        "name": "profile_read",
        "description": (
            "Read the user's HaxJobs profile. Call without arguments for the full profile, "
            "or pass a dot-path like 'personal.email' or 'skills.languages' for a specific field. "
            "Use this before asking questions the profile already answers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field_path": {
                    "type": "string",
                    "description": "Dot-path to a field, e.g. 'personal.name' or 'work_experience'. Omit for full profile.",
                },
            },
            "required": [],
        },
    },
    profile_read,
)
register(
    "profile_write",
    {
        "name": "profile_write",
        "description": (
            "Write a value to the user's HaxJobs profile. Use dot-path notation to target a specific field. "
            "The value can be a plain string or a JSON string for arrays/objects. "
            "Examples: profile_write('personal.phone', '+447...') or "
            "profile_write('skills.ai_ml', '[{\"name\": \"PyTorch\", \"proficiency\": \"advanced\"}]'). "
            "ONLY write fields the user has explicitly confirmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field_path": {"type": "string", "description": "Dot-path to the field to update"},
                "value": {"type": "string", "description": "Value to write (string or JSON-encoded)"},
            },
            "required": ["field_path", "value"],
        },
    },
    profile_write,
)
register(
    "profile_schema",
    {
        "name": "profile_schema",
        "description": (
            "Return the full HaxJobs profile JSON Schema — all fields, types, descriptions, and required flags. "
            "Call this when you need to know what fields exist in the profile before reading or writing."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    profile_schema,
)


# ponytail: required fields are a copy of what's in the schema — keep in sync manually
REQUIRED_FIELDS = [
    "personal.name",
    "personal.email",
    "personal.location",
    "work_authorization.summary",
    "preferences.preferred_roles",
    "preferences.preferred_locations",
    "preferences.preferred_work_modes",
]


def _detect_gaps(profile: dict) -> list[dict]:
    """Find unexplained employment gaps >= 6 months."""
    roles = profile.get("work_experience") or []
    if len(roles) < 2:
        return []
    sorted_roles = sorted(
        [r for r in roles if r.get("start_date")],
        key=lambda r: r["start_date"],
    )
    gaps = []
    for i in range(len(sorted_roles) - 1):
        prev_end = sorted_roles[i].get("end_date", "")
        next_start = sorted_roles[i + 1]["start_date"]
        if not prev_end or prev_end == "present":
            continue
        months = _months_between(prev_end, next_start)
        if months and months >= 6:
            gaps.append({
                "between": f"{sorted_roles[i]['company']} → {sorted_roles[i+1]['company']}",
                "start": prev_end,
                "end": next_start,
                "duration_months": months,
            })
    return gaps


def _months_between(d1: str, d2: str) -> int | None:
    """Approximate months between two YYYY-MM or YYYY strings."""

    def _ym(s: str) -> tuple[int, int]:
        parts = s.split("-")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 1

    try:
        y1, m1 = _ym(d1)
        y2, m2 = _ym(d2)
    except (ValueError, IndexError):
        return None
    return (y2 - y1) * 12 + (m2 - m1)


def profile_gaps() -> dict[str, Any]:
    """Return which required fields are missing and which enrichments are weak."""
    profile = _load_profile()
    if profile is None:
        return {"error": "No profile found. Complete onboarding first."}

    filled: list[str] = []
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        val = _get_nested(profile, field)
        if val is None or val == "" or val == []:
            missing.append(field)
        else:
            filled.append(field)

    # Skill stats
    total_skills = 0
    skills_with_evidence = 0
    for cat in ("languages", "frameworks", "databases", "devops", "ai_ml", "tools"):
        for s in profile.get("skills", {}).get(cat, []) or []:
            total_skills += 1
            if s.get("evidence"):
                skills_with_evidence += 1

    # Achievement stats
    roles = profile.get("work_experience") or []
    total_roles = len(roles)
    roles_with_achievements = sum(1 for r in roles if r.get("achievements"))

    # Employment gaps
    gaps = _detect_gaps(profile)

    return {
        "required_filled": filled,
        "required_missing": missing,
        "total_skills": total_skills,
        "skills_with_evidence": skills_with_evidence,
        "total_roles": total_roles,
        "roles_with_achievements": roles_with_achievements,
        "employment_gaps": gaps,
    }


register(
    "profile_gaps",
    {
        "name": "profile_gaps",
        "description": (
            "Return a summary of profile gaps: which required fields are still empty, "
            "how many skills lack evidence, how many roles lack achievements, "
            "and detected employment gaps. Use this at the start of the enrichment loop "
            "to decide what to ask about."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    profile_gaps,
)
