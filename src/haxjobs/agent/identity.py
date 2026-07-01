"""User-editable identity and memory files for the HaxJobs agent."""
from pathlib import Path

HAXJOBS_HOME = Path.home() / ".haxjobs"

DEFAULT_IDENTITY = """You are HaxJobs, a job search agent. Your purpose is to help a candidate find and apply to jobs they are qualified for.
Be honest: false hope wastes the candidate's time. When a job is a poor fit, say so clearly. When it is a good fit, cite evidence from the profile.
Never submit applications or send outreach without explicit user approval."""


def _read(name: str) -> str:
    path = HAXJOBS_HOME / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def load_identity() -> str:
    return _read("soul.md") or DEFAULT_IDENTITY


def load_memory() -> str:
    return _read("memory.md")


def load_user_profile() -> str:
    return _read("user.md")
