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

CONFIG_PATH = Path(__file__).resolve().parent / "haxjobs.toml"

with open(CONFIG_PATH, "rb") as f:
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
INTAKE_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["intake"]
PACKS_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["packs"]
REPORTS_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["reports"]
OUTREACH_DIR = HAXJOBS_HOME / _cfg["paths"]["runtime"]["outreach"]

# ── Profile ──
PROFILE_DIR = HAXJOBS_HOME / _cfg["paths"]["profile"]["dir"]
PROFILE_PATH = Path(_env("HAXJOBS_PROFILE",
    str(PROFILE_DIR / _cfg["paths"]["profile"]["local"])))
CV_PROFILE_PATH = Path(_env("HAXJOBS_CV_PROFILE",
    str(HAXJOBS_HOME / _cfg["paths"]["profile"]["cv_typed"])))

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

# ── Telegram ──
TELEGRAM_CHAT_ID = _env("HAXJOBS_TELEGRAM_CHAT_ID", _cfg["telegram"]["chat_id"])
TELEGRAM_THREAD_ID = int(_env("HAXJOBS_TELEGRAM_THREAD_ID",
    str(_cfg["telegram"]["thread_id"])))


def haxjobs_home_str() -> str:
    return str(HAXJOBS_HOME)

def db_path_str() -> str:
    return str(DB_PATH)

def profile_path_str() -> str:
    return str(PROFILE_PATH)
