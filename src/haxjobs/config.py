"""HaxJobs runtime paths — global home, no checkout dependency.

All durable state lives under HAXJOBS_HOME (default ~/.haxjobs).
Override HAXJOBS_HOME for isolated tests and alternate profiles.
Environment variables HAXJOBS_CAREER_DB and HAXJOBS_SESSION_DB
override individual paths.
"""
from __future__ import annotations

import os
from pathlib import Path

HAXJOBS_HOME = (
    Path(os.environ.get("HAXJOBS_HOME", Path.home() / ".haxjobs"))
    .expanduser()
    .resolve()
)

PROVIDER_CONFIG_PATH = HAXJOBS_HOME / "haxjobs.toml"
STATE_DIR = HAXJOBS_HOME / "state"
CAREER_DB_PATH = Path(
    os.environ.get("HAXJOBS_CAREER_DB", str(STATE_DIR / "career_graph.db"))
)
SESSION_DB_PATH = Path(
    os.environ.get("HAXJOBS_SESSION_DB", str(STATE_DIR / "sessions.db"))
)


def ensure_runtime_home() -> None:
    """Create runtime directories. Safe to call multiple times.

    Creates the home directory and state directory with restrictive
    POSIX permissions when the platform supports them.
    """
    HAXJOBS_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE_DIR.mkdir(mode=0o700, exist_ok=True)
