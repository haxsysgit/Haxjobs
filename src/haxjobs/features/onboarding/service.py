"""Onboarding business logic — uses native agent for extraction and questions."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from haxjobs.agent import Agent, get_prompt
from haxjobs.evaluate.common import extract_json

PROFILE_PATH = Path.home() / ".haxjobs" / "profile.json"

# Temporary in-memory profile during wizard flow.
# ponytail: dict on module, reset on new upload. Replace with session/DB
# when onboarding spans multiple browser tabs or server restarts.
_pending_profile: dict | None = None
_answered_questions: list[str] = []


# ── file extraction ──


def extract_text_from_upload(content: bytes, filename: str) -> str:
    """Extract readable text from uploaded CV file.

    Tries UTF-8 decode first (plain text, markdown). Falls back to
    pdftotext for PDFs. No Python PDF dependency — uses system tool.
    """
    try:
        return content.decode("utf-8").strip()
    except UnicodeDecodeError:
        pass

    if filename.lower().endswith(".pdf"):
        return _extract_pdf(content)

    raise ValueError(
        f"Cannot read {filename}. Upload a PDF or paste text directly."
    )


def _extract_pdf(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(content)
        tmp_path = tf.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise ValueError(f"pdftotext failed: {result.stderr.strip()}")
        text = result.stdout.strip()
        if not text:
            raise ValueError("PDF appears empty or is image-only.")
        return text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ── profile extraction ──


def extract_profile_from_cv(cv_text: str) -> dict:
    """Extract structured profile from CV text using native agent."""
    system, user = get_prompt("extract_cv", cv_text=cv_text)
    raw = Agent().run(prompt=user, system=system)
    result = extract_json(raw)
    if not result or not isinstance(result, dict):
        raise ValueError("Agent failed to extract structured profile from CV")
    return result


# ── wizard ──

_GAP_FIELDS = [
    "user_profile.phone",
    "user_profile.salary_preference",
    "user_profile.requires_sponsorship",
    "user_profile.work_authorization_summary",
    "preferred_roles",
    "preferred_locations",
    "preferred_work_modes",
]


def get_next_question(profile: dict, answered: list[str]) -> dict | None:
    """Return the next wizard question, or None if done."""
    unanswered = [f for f in _GAP_FIELDS if f not in answered]
    if not unanswered:
        return None
    field = unanswered[0]
    label = field.replace("_", " ").replace(".", " → ")
    return {
        "field": field,
        "question": f"What is your {label}?",
        "type": "text",
    }


def apply_answer(profile: dict, question_id: str, answer: str) -> dict:
    """Merge answer into profile at the dot-path."""
    parts = question_id.split(".")
    target = profile
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = answer
    return profile


# ── persist ──


def save_profile(profile: dict):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def load_profile() -> dict | None:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            return json.load(f)
    return None


# ── session helpers ──


def start_session(profile: dict):
    global _pending_profile, _answered_questions
    _pending_profile = profile
    _answered_questions = []


def get_session() -> tuple[dict | None, list[str]]:
    return _pending_profile, _answered_questions


def clear_session():
    global _pending_profile, _answered_questions
    _pending_profile = None
    _answered_questions = []
