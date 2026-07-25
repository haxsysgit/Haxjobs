"""HaxJobs runtime paths — global home, no checkout dependency.

All durable state lives under HAXJOBS_HOME (default ~/.haxjobs).
Override HAXJOBS_HOME for isolated tests and alternate profiles.
Environment variables HAXJOBS_CAREER_DB and HAXJOBS_SESSION_DB
override individual paths.

When running from a development checkout (pyproject.toml or .git
detected in CWD, or PYTHONPATH=src set) and HAXJOBS_HOME is not
explicitly set, home defaults to dev-home/ inside the checkout.
"""
from __future__ import annotations

import os
from pathlib import Path


def _is_dev_checkout() -> bool:
    """Detect a development checkout of the HaxJobs repo."""
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() or (cwd / ".git").exists():
        return True
    if "src" in os.environ.get("PYTHONPATH", ""):
        return True
    return False


_home_env = os.environ.get("HAXJOBS_HOME")
if _home_env is not None:
    _home = Path(_home_env)
    _dev = False
elif _is_dev_checkout():
    _home = Path.cwd() / "dev-home"
    _dev = True
else:
    _home = Path.home() / ".haxjobs"
    _dev = False

HAXJOBS_HOME = _home.expanduser().resolve()

if _dev and _home_env is None:
    print(f"Dev mode: using {HAXJOBS_HOME} for runtime data. Set HAXJOBS_HOME to override.", file=__import__("sys").stderr)

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
