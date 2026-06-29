"""Shared evaluation utilities — prompt building, JSON extraction, validation.

Extracted from the old ``evaluate_with_hermes.py`` so the agent adapter and
the prompt logic are independent.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from haxjobs_config import HAXJOBS_HOME, PROFILE_PATH

EXPECTED_SCHEMA = {
    "fit_score": int,
    "fit_verdict": str,
    "level": int,
    "level_name": str,
    "strongest_matches": list,
    "major_gaps": list,
    "sponsorship_risk": str,
    "summary": str,
    "decision": str,
    "skip_reason": str,
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def build_profile_blurb(company: str = "") -> str:
    """Build the profile section of the evaluation prompt.

    Reads from the local profile JSON for confirmed facts, evaluation context,
    and company-specific notes.
    """
    if not os.path.exists(PROFILE_PATH):
        return "Profile not found."

    p = load_json(PROFILE_PATH)
    up = p.get("user_profile", {})
    facts = p.get("confirmed_profile_facts", [])
    eval_context = p.get("evaluation_context", {})
    company_notes = p.get("company_notes", {})

    by_cat: dict[str, list[str]] = {}
    for f in facts:
        cat = f.get("category", "other")
        by_cat.setdefault(cat, []).append(f.get("claim", ""))

    lines = [
        f"Name: {up.get('name', 'Arinze Elenasulu')}",
        f"Headline: {up.get('preferred_headline', 'Python Backend Engineer | AI & Automation')}",
        f"Location: {up.get('location', 'London, UK')}",
        f"Sponsorship: {up.get('work_authorization_summary', 'UK work authorization, requires sponsorship for non-UK roles')}",
        f"Salary range: {up.get('salary_preference', '£35,000-£60,000')}",
        f"University: {up.get('university', 'Middlesex University London')}",
        f"Preferred roles: {', '.join(up.get('preferred_roles', ['AI Engineer', 'Backend Engineer', 'Full Stack Engineer', 'Software Developer']))}",
        f"Preferred locations: {', '.join(up.get('preferred_locations', ['London', 'Manchester', 'Leeds', 'Remote UK']))}",
        f"Preferred work: {', '.join(up.get('preferred_work_modes', ['Hybrid', 'Remote', 'On-site']))}",
        f"Target levels: {', '.join(up.get('experience_levels', ['junior', 'mid-level', 'graduate', 'intern']))}",
        f"Excluded levels: {', '.join(up.get('excluded_levels', ['senior', 'lead', 'principal', 'staff', 'director', 'VP', 'head of', 'manager']))}",
    ]

    if by_cat:
        lines.append("\nProfile facts:")
        for cat, claims in by_cat.items():
            lines.append(f"  [{cat}]")
            for c in claims:
                lines.append(f"    - {c}")

    # ── Evaluation Context (behavioral guardrails) ──
    guardrails = eval_context.get("behavioral_guardrails", [])
    if guardrails:
        lines.append("\n## Behavioral Guardrails (READ BEFORE SCORING)")
        for g in guardrails:
            lines.append(f"  - {g}")

    scoring = eval_context.get("scoring_guidance", {})
    if scoring:
        lines.append("\n## Scoring Guidance")
        for role_type, guidance in scoring.items():
            lines.append(f"  [{role_type}] {guidance}")

    # ── Company-specific notes ──
    if company:
        company_lower = company.strip().lower()
        matched_notes = []
        for key, cn in company_notes.items():
            pattern = cn.get("pattern", "").lower()
            match_type = cn.get("match_type", "company_name_contains")
            if match_type == "company_name_contains" and pattern in company_lower:
                matched_notes.append(cn.get("note", ""))

        if matched_notes:
            lines.append("\n## Company-Specific Notes (IMPORTANT)")
            for note in matched_notes:
                lines.append(f"  - {note}")

    return "\n".join(lines)


def _build_whitelist_context(company: str, title: str) -> str:
    """Build whitelist context from DB for the evaluation prompt."""
    try:
        import pipeline_db as db
        whitelist = db.get_whitelist_for_eval(company, title) if hasattr(db, 'get_whitelist_for_eval') else []
    except Exception:
        whitelist = []

    if not whitelist:
        return "No whitelist entries match this job."

    lines = ["The following whitelist entries apply to this job. DO NOT auto-skip if any match:"]
    for w in whitelist:
        lines.append(f"  - Pattern: {w.get('pattern_value', 'N/A')} (type: {w.get('pattern_type', 'unknown')})")
        lines.append(f"    Reason: {w.get('reason', 'No reason recorded')}")
    return "\n".join(lines)


def build_prompt(title: str, company: str, location: str,
                 jd_text: str, source_url: str) -> str:
    """Build the evaluation prompt from job data."""
    profile = build_profile_blurb(company)
    whitelist_context = _build_whitelist_context(company, title)
    return f"""You are evaluating a job for Arinze Elenasulu. Your output must be ONLY valid JSON — no markdown, no commentary, no code fences.

## Arinze's Profile
{profile}

## Whitelist / Learning Context
{whitelist_context}

## Job to Evaluate
- Title: {title}
- Company: {company}
- Location: {location}
- URL: {source_url}
- Description:
{jd_text[:4000]}

## Scoring Rules (LENIENT MODE, v3.0.0)
- 75+: Strong fit. Arinze hits most requirements. Recommend full per-job prep pack using the reusable CV variant chosen by role_family.
- 50-74: Good fit. Some gaps but worth applying. Recommend quick per-job prep pack using the reusable CV variant.
- 30-49: Weak fit. Significant gaps. Report only, no pack.
- <30: Skip. Wrong role, wrong level, or hard blocker.

## Hard Blockers (auto-score ≤10 if any)
- Role requires citizenship or security clearance Arinze doesn't have
- Non-engineering role (sales, marketing, legal, HR, finance, admin)
- Location is outside UK and not remote

## NOT Hard Blockers (these are FINE to pass)
- "Senior" in title: Arinze can still apply if the JD is reasonable. Evaluate the actual JD, not the title.
- "Lead" or "Manager" in title: Evaluate the actual role, not the title keyword.
- Years of experience: Arinze has 2+ years hands-on (Python since 2020, Vigilis 2024-2026, Aptech 2022-2024). Do NOT auto-skip based on years. Evaluate the actual skills asked for.
- Skill adjacencies count: Python → AI/ML, backend → full-stack, FastAPI → Django.

## Level Assignment
- Level 1 (Standard): 75%+. Use the reusable CV variant, plus cover letter + form answers + interview prep.
- Level 2 (Quick Apply): 50-74%. Use the reusable CV variant, plus cover letter + field answers.
- Level 3 (Lite): 30-49%. Fit report only.
- Level 4 (Skip): <30%. Skip reason only.

## Output Format (EXACT — no extra text, no markdown fences)
{{
  "fit_score": <0-100>,
  "fit_verdict": "<STRONG_FIT|GOOD_FIT|WEAK_FIT|SKIP>",
  "level": <1-4>,
  "level_name": "<Standard|Quick Apply|Lite|Skip>",
  "strongest_matches": ["<2-3 specific, truthful match points>"],
  "major_gaps": ["<2-3 honest gap points>"],
  "sponsorship_risk": "<low|medium|high>",
  "summary": "<1-2 sentence fit summary mentioning the role, company, score, and key reason>",
  "decision": "<completed|skipped>",
  "skip_reason": "<why skipped, or empty string if completed>"
}}

CRITICAL: No em dashes. No corporate verbs (spearheaded, leveraged, orchestrated). Simple human voice. Be truthful — do not inflate fit. Arinze is junior/mid, not senior."""


def extract_json(text: str) -> dict | None:
    """Extract JSON object from agent output. Handles box chars and \\r\\n."""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Hermes CLI wraps output: ╭─ ⚕ Hermes ──...──╮\\n    <content>\\n╰──...──╯
    m = re.search(r'╭─[^\n]*\n\s*(.+?)\n╰─', text, re.DOTALL)
    if m:
        inner = m.group(1).strip()
        if inner.startswith("{") or inner.startswith("```"):
            text = inner

    # Try triple-backtick fences (with or without json tag)
    m = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any { ... } block in the output
    brace_depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start >= 0:
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = -1
                    continue

    # Try the whole text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    return None


def validate_result(result: dict) -> list[str]:
    """Validate an evaluation result dict against EXPECTED_SCHEMA.

    Returns a list of issue strings (empty if valid).
    """
    issues = []
    for key, expected_type in EXPECTED_SCHEMA.items():
        if key not in result:
            issues.append(f"Missing key: {key}")
        elif not isinstance(result[key], expected_type):
            issues.append(f"Wrong type for {key}: got {type(result[key]).__name__}")
    if "fit_score" in result and isinstance(result["fit_score"], (int, float)):
        if not (0 <= result["fit_score"] <= 100):
            issues.append(f"fit_score out of range: {result['fit_score']}")
    if "level" in result and isinstance(result["level"], int):
        if not (1 <= result["level"] <= 4):
            issues.append(f"level out of range: {result['level']}")
    return issues
