"""3-tier system prompt assembly: stable → context → volatile."""
from __future__ import annotations

from datetime import datetime, timezone


def build_system_prompt(
    identity: str,
    memory: str = "",
    user_profile: str = "",
    skills_index: str = "",
    context_files: str = "",
    platform: str = "web",
) -> str:
    parts = [_stable_tier(identity, skills_index, platform)]
    if context_files:
        parts.append(f"# Project context\n{context_files}")

    volatile = []
    if memory:
        volatile.append(f"## Memory\n{memory}")
    if user_profile:
        volatile.append(f"## User profile\n{user_profile}")
    volatile.append(f"Current time: {datetime.now(timezone.utc).isoformat()}")
    parts.append("\n\n".join(volatile))
    return "\n\n".join(parts)


def _stable_tier(identity: str, skills_index: str, platform: str) -> str:
    hints = {
        "web": "You are serving HaxJobs results to a web dashboard.",
        "cli": "You are running from the command line. Be concise.",
        "cron": "Running unattended. Write results to durable storage.",
    }
    parts = [identity, hints.get(platform, hints["web"])]
    if skills_index:
        parts.append(f"## Available skills\n{skills_index}")
    return "\n\n".join(parts)
