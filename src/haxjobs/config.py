"""HaxJobs configuration — thin parser over haxjobs.toml.

Canonical config: haxjobs.toml
Environment variables override any value.
Import this module everywhere; never hardcode paths.
"""
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

_CANDIDATES = [
    Path("haxjobs.toml"),                        # CWD first
    Path(__file__).resolve().parent / "haxjobs.toml",  # package dir
]
_TOML_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[1])

with open(_TOML_PATH, "rb") as f:
    _cfg = tomllib.load(f)

def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)

# ── Home ──
HAXJOBS_HOME = Path(_env("HAXJOBS_HOME", _cfg["paths"]["home"]))

# ── State (database + logs) ──
STATE_DIR = HAXJOBS_HOME / _cfg["paths"]["state"]["dir"]
DB_PATH = Path(_env("HAXJOBS_DB", str(STATE_DIR / _cfg["paths"]["state"]["db"])))
PIPELINE_LOG = STATE_DIR / _cfg["paths"]["state"]["log"]

# ── Runtime directories ──
PACKS_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["packs"]
REPORTS_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["reports"]
OUTREACH_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["outreach"]

# ── Profile ──
PROFILE_DIR = HAXJOBS_HOME / _cfg["paths"]["profile"]["dir"]
PROFILE_PATH = Path(_env("HAXJOBS_PROFILE", str(STATE_DIR / "profile.json")))
CV_PROFILE_PATH = Path(_env("HAXJOBS_CV_PROFILE",
    str(HAXJOBS_HOME / _cfg["paths"]["profile"]["cv_typed"])))

# ── Career graph ──
CAREER_DB_PATH = Path(_env("HAXJOBS_CAREER_DB", str(STATE_DIR / "career_graph.db")))

# ── Registry ──
REGISTRY_PATH = HAXJOBS_HOME / _cfg["paths"]["registry"]["cv_variants"]

# ── Dashboard ──
DASHBOARD_DIR = HAXJOBS_HOME / _cfg["paths"]["dashboard"]["dir"]

# ── Email ──
EMAIL_IMAP_HOST = _env("HAXJOBS_EMAIL_IMAP_HOST", _cfg["email"]["imap_host"])
EMAIL_IMAP_PORT = int(_env("HAXJOBS_EMAIL_IMAP_PORT", str(_cfg["email"]["imap_port"])))
EMAIL_ADDRESS = _env("HAXJOBS_EMAIL_ADDRESS", _cfg["email"]["address"])
EMAIL_ALLOWED_SENDERS = _env("HAXJOBS_EMAIL_ALLOWED_SENDERS",
    ",".join(_cfg["email"]["allowed_senders"])).split(",")

# ── User profile (plan 016) ──
USER_PROFILE: dict = _cfg.get("user", {})

# ── Job search preferences (plan 016) ──
JOB_SEARCH_CONFIG: dict = _cfg.get("job_search", {})

# ── Discovery scraper settings (plan 023) ──
DISCOVERY_CONFIG: dict = _cfg.get("discovery", {})

# ── Role profiles for classification (plan 016) ──
# TOML [[roles]] arrays become a list of dicts keyed by "roles"
ROLE_PROFILES: list[dict] = _cfg.get("roles", [])

# ── Evaluation config (plan 016) ──
EVALUATION_CONFIG: dict = _cfg.get("evaluation", {})
EVALUATION_AGENT: str = EVALUATION_CONFIG.get("agent", "hermes")
EVALUATION_FALLBACK_AGENTS: list[str] = EVALUATION_CONFIG.get("fallback_agents", [])
AUTO_PACK_LEVELS: frozenset[int] = frozenset(EVALUATION_CONFIG.get("levels", {}).get("auto_pack", [1, 2]))
MANUAL_REVIEW_LEVELS: frozenset[int] = frozenset(EVALUATION_CONFIG.get("levels", {}).get("manual_review", [3]))
SKIP_LEVELS: frozenset[int] = frozenset(EVALUATION_CONFIG.get("levels", {}).get("skip", [4]))

# ── Delivery config (plan 016) ──
DELIVERY_CONFIG: dict = _cfg.get("delivery", {})
DELIVERY_CHANNELS: list[str] = DELIVERY_CONFIG.get("channels", ["email"])

# ── Cron config (plan 026) ──
CRON_CONFIG: dict = _cfg.get("cron", {})


def haxjobs_home_str() -> str:
    return str(HAXJOBS_HOME)

def db_path_str() -> str:
    return str(DB_PATH)

def profile_path_str() -> str:
    return str(PROFILE_PATH)

def load_config() -> dict:
    """Return the parsed haxjobs.toml config."""
    return dict(_cfg)
