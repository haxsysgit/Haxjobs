"""Central configuration for HaxJobs.

Every path and default that was previously hardcoded lives here.
Import this module instead of repeating "/home/hermes/haxjobs" or
"arinze_profile.local.json".

Environment variables override every default.

Quick start on a new machine:

    export HAXJOBS_HOME="$HOME/.local/share/haxjobs"
    export HAXJOBS_PROFILE="$PWD/profile/me.local.json"
    mkdir -p "$HAXJOBS_HOME/state"
"""

import os
from pathlib import Path

# ── Home directory ──
# Everything HaxJobs owns derives from this one path.
# Override with HAXJOBS_HOME env var. Default: auto-detect from config location
# if the legacy Archilles path doesn't exist.
_home_env = os.environ.get("HAXJOBS_HOME", "")
if _home_env:
    HAXJOBS_HOME = Path(_home_env)
else:
    _legacy = Path("/home/hermes/haxjobs")
    HAXJOBS_HOME = _legacy if _legacy.exists() else Path(__file__).resolve().parent

# ── State / runtime directories (derived from HAXJOBS_HOME) ──
STATE_DIR = HAXJOBS_HOME / "state"
INTAKE_DIR = HAXJOBS_HOME / "intake"
PACKS_DIR = HAXJOBS_HOME / "packs"
REPORTS_DIR = HAXJOBS_HOME / "reports"
OUTREACH_DIR = HAXJOBS_HOME / "outreach"
PROFILE_DIR = HAXJOBS_HOME / "profile"
DISCOVERY_DIR = HAXJOBS_HOME / "discovery"
DASHBOARD_DIR = HAXJOBS_HOME / "dashboard"

# ── Database ──
# HAXJOBS_DB overrides the default location under STATE_DIR.
_db_env = os.environ.get("HAXJOBS_DB", "")
DB_PATH = Path(_db_env) if _db_env else (STATE_DIR / "pipeline.db")

# ── Pipeline log ──
PIPELINE_LOG = STATE_DIR / "pipeline.log"

# ── Profile ──
# The path to the user's private profile JSON.
# Must be a real file — HaxJobs does not invent profile facts.
_profile_env = os.environ.get("HAXJOBS_PROFILE", "")
if _profile_env:
    PROFILE_PATH = Path(_profile_env)
else:
    PROFILE_PATH = PROFILE_DIR / "arinze_profile.local.json"

# ── CV profile (typed JSON used by CV renderer/validator) ──
_cv_profile_env = os.environ.get("HAXJOBS_CV_PROFILE", "")
CV_PROFILE_PATH = Path(_cv_profile_env) if _cv_profile_env else (HAXJOBS_HOME / "cv_profile.typed.json")

# ── Registry ──
REGISTRY_PATH = HAXJOBS_HOME / "cv_variants" / "registry.json"

# ── Discovery helpers ──
JOB_CLASSIFICATION_FILE = STATE_DIR / "job_classifications.json"
DISCOVERY_LOG = STATE_DIR / "discovery.log"

# ── Email intake ──
EMAIL_IMAP_HOST = os.environ.get("HAXJOBS_EMAIL_IMAP_HOST", "imap.gmail.com")
EMAIL_IMAP_PORT = int(os.environ.get("HAXJOBS_EMAIL_IMAP_PORT", "993"))
EMAIL_ADDRESS = os.environ.get("HAXJOBS_EMAIL_ADDRESS", "archilleshaxsys@gmail.com")
EMAIL_ALLOWED_SENDERS = os.environ.get(
    "HAXJOBS_EMAIL_ALLOWED_SENDERS",
    "elenasuluarinze@gmail.com,pentacker@gmail.com",
).split(",")

# ── Telegram ──
TELEGRAM_CHAT_ID = os.environ.get("HAXJOBS_TELEGRAM_CHAT_ID", "-1003991695885")
TELEGRAM_THREAD_ID = int(os.environ.get("HAXJOBS_TELEGRAM_THREAD_ID", "18"))


def haxjobs_home_str() -> str:
    """Return HAXJOBS_HOME as a plain string (for shell-subprocess consumers)."""
    return str(HAXJOBS_HOME)


def db_path_str() -> str:
    """Return the database path as a plain string."""
    return str(DB_PATH)


def profile_path_str() -> str:
    """Return the profile path as a plain string."""
    return str(PROFILE_PATH)
