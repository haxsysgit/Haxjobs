"""Onboarding business logic — two-phase wizard.

Phase 1 (required): fill REQUIRED_FIELDS deterministically.
Phase 2 (deep):    agent generates personalized questions to flesh out profile.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from haxjobs.agent import Agent, get_prompt
from haxjobs.evaluate.common import extract_json

from .schemas import AGENT_INFERRED_FIELDS, REQUIRED_FIELDS, FieldQuestion

PROFILE_PATH = Path.home() / ".haxjobs" / "profile.json"

# In-memory session state (ponytail: module globals, reset on new upload).
_pending_profile: dict | None = None
_answered_fields: set[str] = set()
_phase: str = "required"
_deep_questions: list[dict] = []


# ── file extraction ──


def extract_text_from_upload(content: bytes, filename: str) -> str:
    try:
        return content.decode("utf-8").strip()
    except UnicodeDecodeError:
        pass
    if filename.lower().endswith(".pdf"):
        return _extract_pdf(content)
    raise ValueError(f"Cannot read {filename}. Upload a PDF or paste text directly.")


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
            stderr = result.stderr.strip()
            if "not found" in stderr.lower() or "No such file" in stderr:
                raise ValueError(
                    "pdftotext not found. Install it:\n"
                    "  Linux: sudo apt install poppler-utils\n"
                    "  macOS: brew install poppler\n"
                    "  Windows: install poppler from "
                    "https://github.com/oschwartz10612/poppler-windows/releases\n"
                    "Or paste your CV as plain text instead."
                )
            raise ValueError(f"pdftotext failed: {stderr}")
        text = result.stdout.strip()
        if not text:
            raise ValueError("PDF appears empty or is image-only. Try pasting your CV as plain text.")
        return text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ── profile extraction ──


def extract_profile_from_cv(cv_text: str) -> dict:
    system, user = get_prompt("extract_cv", cv_text=cv_text)
    raw = Agent().run(prompt=user, system=system)
    result = extract_json(raw)
    if not result or not isinstance(result, dict):
        raise ValueError("Agent failed to extract structured profile from CV")
    return result


# ── gap detection ──


def _get_field_value(profile: dict, field_path: str):
    """Get value at dot-path, e.g. 'user_profile.email' → profile['user_profile']['email']."""
    parts = field_path.split(".")
    target = profile
    for part in parts:
        if isinstance(target, dict):
            target = target.get(part)
        else:
            return None
    return target


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _check_required_gaps(profile: dict) -> list[str]:
    """Return ordered list of required fields still missing from profile."""
    gaps = []
    for field in REQUIRED_FIELDS:
        val = _get_field_value(profile, field)
        if _is_empty(val):
            gaps.append(field)
    return gaps


def _build_question(field: str, profile: dict) -> FieldQuestion:
    spec = REQUIRED_FIELDS[field]
    current = _get_field_value(profile, field)
    return FieldQuestion(
        field=field,
        question=spec["question"],
        type=spec["type"],
        description=spec["description"],
        current_value=current if not _is_empty(current) else None,
    )


# ── agent deep questions ──


def _generate_deep_questions(profile: dict) -> list[dict]:
    """Ask the agent to generate personalized deep-dive questions."""
    prompt = (
        "You are an expert career coach and recruiter. Given this candidate profile, "
        "generate 3-5 specific questions that will add depth and detail useful for "
        "job matching — things a good recruiter would ask in a screening call.\n\n"
        "Focus on: specific technologies used and proficiency, project impact and metrics, "
        "team structures worked in, career trajectory preferences, non-obvious skills, "
        "industry preferences, company culture fit, and anything that distinguishes "
        "this candidate from a generic CV.\n\n"
        "Profile:\n" + json.dumps(profile, indent=2) + "\n\n"
        "Return JSON array of {field, question, type, description} objects. "
        "field should use dot-path notation to the profile location, e.g. "
        "'work_experience.0.highlights', 'user_profile.salary_preference'. "
        "type is 'text' or 'list'. description is one line explaining why this matters."
    )
    raw = Agent().run(prompt=prompt, temperature=0.7)
    questions = extract_json(raw)
    if isinstance(questions, list):
        return questions
    return []


# ── wizard flow ──


def get_next_question(profile: dict) -> FieldQuestion | None:
    """Determine next wizard question based on current phase."""
    global _phase, _deep_questions, _answered_fields

    if _phase == "required":
        gaps = [f for f in _check_required_gaps(profile) if f not in _answered_fields]
        if gaps:
            return _build_question(gaps[0], profile)
        # all required fields filled → switch to deep phase
        _phase = "deep"
        _deep_questions = _generate_deep_questions(profile)

    if _phase == "deep":
        pending = [q for q in _deep_questions if q["field"] not in _answered_fields]
        if pending:
            dq = pending[0]
            return FieldQuestion(
                field=dq["field"],
                question=dq["question"],
                type=dq.get("type", "text"),
                description=dq.get("description", ""),
            )
        _phase = "complete"

    return None


def apply_answer(profile: dict, question_id: str, answer: str) -> dict:
    """Merge answer into profile. List fields are comma-split."""
    global _answered_fields
    _answered_fields.add(question_id)

    spec = REQUIRED_FIELDS.get(question_id)
    if spec and spec["type"] == "list":
        value = [item.strip() for item in answer.split(",") if item.strip()]
    else:
        value = answer

    parts = question_id.split(".")
    target = profile
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value
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
    global _pending_profile, _answered_fields, _phase, _deep_questions
    _pending_profile = profile
    _answered_fields = set()
    _phase = "required"
    _deep_questions = []

    # Mark fields found during CV extraction as already answered
    for field in AGENT_INFERRED_FIELDS:
        val = _get_field_value(profile, field)
        if not _is_empty(val):
            _answered_fields.add(field)


def get_session() -> tuple[dict | None, str, int]:
    remaining = (
        len([f for f in _check_required_gaps(_pending_profile or {})
             if f not in _answered_fields])
        if _pending_profile and _phase == "required"
        else len([q for q in _deep_questions if q["field"] not in _answered_fields])
        if _phase == "deep"
        else 0
    )
    return _pending_profile, _phase, remaining


def clear_session():
    global _pending_profile, _answered_fields, _phase, _deep_questions
    _pending_profile = None
    _answered_fields = set()
    _phase = "required"
    _deep_questions = []
