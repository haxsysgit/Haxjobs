#!/usr/bin/env python3
"""
CV-FRAME Validator — runs all validation assertions before PDF export.
Returns exit code 0 if clean, 1 if violations found.
Usage: python3 cv_validator.py <cv_markdown_or_html_path> <cv_profile_path>
"""
import json
import sys
import re
from pathlib import Path
from html import unescape


def load_profile(path):
    with open(path) as f:
        return json.load(f)


def _normalize(text):
    """Normalize text for comparison: decode HTML entities, collapse whitespace."""
    return unescape(text)


def _date_flexible_contains(cv_text, date_value):
    """Check if a date range appears in the CV, accepting both en-dash and 'to' forms."""
    if date_value in cv_text:
        return True
    # Accept "to" as equivalent to en-dash
    dash_variants = [date_value, date_value.replace("–", "to"), date_value.replace("–", "-")]
    for variant in dash_variants:
        if variant in cv_text:
            return True
    return False


def check_locked_constants(cv_text, constants):
    violations = []
    cv_normalized = _normalize(cv_text)
    for key, spec in constants.items():
        value = spec["value"]
        if spec.get("type") != "literal":
            continue
        # Skip empty/optional fields (phone removed, etc.)
        if not value or spec.get("validation") == "optional":
            continue

        # Date fields: accept flexible forms
        if "dates" in key or key.endswith("_dates"):
            if _date_flexible_contains(cv_normalized, value):
                continue

        # Title fields: only require the core title, not exact match
        # (CV may split title and "(Contract, part-time)" into separate HTML elements)
        elif key in ("bucca_hut_title", "vigilis_title"):
            core_title = value.split(" (")[0] if " (" in value else value
            if core_title in cv_normalized:
                continue

        # Standard literal check
        elif value in cv_normalized:
            continue

        violations.append(f"MISSING CONSTANT: '{key}' → '{value}' not found in CV")
    return violations


# ──────────────────────────────────────────────
# CHECK 2: FORBIDDEN UNIVERSITY NAMES
# Known-wrong university names must be absent.
# The correct name "Middlesex University London" must be present.
# ──────────────────────────────────────────────
FORBIDDEN_UNIVERSITIES = [
    "Hertfordshire", "University of London", "UCL", "Imperial",
    "King's College", "LSE", "Queen Mary", "Brunel", "Westminster",
    "Greenwich", "South Bank", "London Met", "City University",
    "Birmingham", "Manchester University", "Leeds University",
    "Edinburgh", "Glasgow", "Bristol", "Oxford", "Cambridge",
    "Warwick", "Durham", "Nottingham", "Sheffield"
]


def check_forbidden_universities(cv_text):
    violations = []
    correct = "Middlesex University London"
    for name in FORBIDDEN_UNIVERSITIES:
        if name.lower() in cv_text.lower():
            # Only flag if the correct name is ALSO missing
            if correct not in cv_text:
                violations.append(f"WRONG UNIVERSITY: '{name}' found, but '{correct}' missing")
    return violations


# ──────────────────────────────────────────────
# CHECK 3: FORBIDDEN PROJECT CLAIMS
# No claim from a project's forbidden_claims list may appear.
# ──────────────────────────────────────────────
def check_forbidden_claims(cv_text, project_registry):
    violations = []
    cv_normalized = _normalize(cv_text).lower()
    for proj_key, proj in project_registry.items():
        display_name = proj["display_name"]
        # Find the project's section in the CV (from its title to the next project or section boundary)
        # Look for the project name as it appears in a heading or title element
        name_pattern = re.escape(display_name.lower())
        # Find position of this project's name
        name_match = re.search(rf'(?:project-title|project-item).*?{name_pattern}', cv_normalized, re.DOTALL)
        if not name_match:
            continue
        start = name_match.start()
        # Find the next project-item or section boundary
        next_boundary = re.search(r'(?:class="project-item|class="section")', cv_normalized[start+1:])
        end = start + 1 + next_boundary.start() if next_boundary else len(cv_normalized)
        section = cv_normalized[start:end]
        for claim in proj.get("forbidden_claims", []):
            if claim.lower() in section:
                violations.append(
                    f"FORBIDDEN CLAIM in {proj['display_name']}: '{claim}'"
                )
    return violations


# ──────────────────────────────────────────────
# CHECK 4: REPO VISIBILITY
# No URL for a project with include_url_in_cv == false.
# ──────────────────────────────────────────────
def check_repo_visibility(cv_text, project_registry):
    violations = []
    seen = set()
    cv_normalized = _normalize(cv_text)
    # Match github.com/haxsysgit/REPO-NAME — stop at first whitespace, quote, <, or >
    github_urls = re.findall(r'github\.com/haxsysgit/([a-zA-Z0-9_.-]+)', cv_normalized)
    for repo_name in github_urls:
        if repo_name in seen:
            continue
        seen.add(repo_name)
        for proj_key, proj in project_registry.items():
            repo_url = proj.get("repo_url") or ""
            if repo_name in repo_url:
                if not proj.get("include_url_in_cv", False):
                    violations.append(
                        f"PRIVATE REPO URL: {proj['display_name']} ({repo_url}) "
                        f"has include_url_in_cv=false — remove URL from CV"
                    )
    return violations


# ──────────────────────────────────────────────
# CHECK 5: EM DASHES
# Zero em dashes allowed.
# ──────────────────────────────────────────────
def check_em_dashes(cv_text):
    count = cv_text.count("\u2014")
    if count > 0:
        return [f"EM DASHES: {count} found — replace with comma, semicolon, or period"]
    return []


# ──────────────────────────────────────────────
# CHECK 6: FORBIDDEN VERBS
# No corporate/AI-tell verbs allowed.
# ──────────────────────────────────────────────
FORBIDDEN_VERBS = [
    "Spearheaded", "Leveraged", "Orchestrated", "Drove",
    "Championed", "Utilized", "Harnessed", "Synergized"
]


def check_forbidden_verbs(cv_text):
    violations = []
    for verb in FORBIDDEN_VERBS:
        if re.search(rf'\b{verb}\b', cv_text, re.IGNORECASE):
            violations.append(f"FORBIDDEN VERB: '{verb}'")
    return violations


# ──────────────────────────────────────────────
# CHECK 7: BLOCKED PHRASES
# Specific phrases must never appear.
# ──────────────────────────────────────────────
BLOCKED_PHRASES = [
    "Claude Code", "cutting-edge", "production-grade", "robust enterprise"
]


def check_blocked_phrases(cv_text):
    violations = []
    for phrase in BLOCKED_PHRASES:
        if phrase.lower() in cv_text.lower():
            violations.append(f"BLOCKED PHRASE: '{phrase}' found")
    return violations


# ──────────────────────────────────────────────
# CHECK 8: SECTION COMPLETENESS
# Professional Summary >= 30 words, Core Skills >= 4 groups.
# ──────────────────────────────────────────────
def check_section_completeness(cv_text):
    violations = []

    # Professional Summary — find text between section-title and next section boundary
    # Works for both HTML (<div class="section-title">) and markdown (## Professional Summary)
    summary_match = re.search(
        r'(?:section-title["\'>]\s*>|##\s*)Professional Summary.*?'
        r'(?:<p>|<div class="summary">)\s*(.*?)\s*(?:</p>|</div>)',
        cv_text, re.DOTALL | re.IGNORECASE
    )
    if not summary_match:
        # Fallback: try finding any text after the heading until next section-title
        summary_match = re.search(
            r'(?:>|##\s*)Professional Summary[^>]*>?\s*\n?\s*(.*?)(?=\n\s*(?:<div class="section-title"|##\s*(?:Core Skills|Experience)))',
            cv_text, re.DOTALL | re.IGNORECASE
        )
    if not summary_match:
        violations.append("MISSING: Professional Summary section not found")
    else:
        summary_text = summary_match.group(1).strip()
        summary_clean = re.sub(r'<[^>]+>', ' ', summary_text)
        words = len(summary_clean.split())
        if words < 30:
            violations.append(f"SUMMARY TOO SHORT: {words} words (minimum 30)")

    # Core Skills — count bold-labeled groups (markdown: **Group:** or HTML: <strong>Group:</strong>)
    skill_groups_md = re.findall(r'\*\*([^*]+):\*\*', cv_text)
    skill_groups_html = re.findall(r'<strong>([^<]+):</strong>', cv_text)
    skill_groups = skill_groups_md + skill_groups_html
    if len(skill_groups) < 4:
        violations.append(f"CORE SKILLS: only {len(skill_groups)} groups found (minimum 4)")

    return violations


# ──────────────────────────────────────────────
# CHECK 9: EDUCATION
# Middlesex must appear, Aptech must appear, Middlesex before Aptech.
# ──────────────────────────────────────────────
def check_education(cv_text):
    violations = []
    correct_university = "Middlesex University London"
    cv_normalized = _normalize(cv_text)

    if correct_university not in cv_normalized:
        violations.append("EDUCATION: 'Middlesex University London' not found")
    if "Aptech" not in cv_normalized:
        violations.append("EDUCATION: 'Aptech' not found")

    # Check Middlesex appears before Aptech WITHIN the education section
    edu_match = re.search(
        r'(?:section-title["\'>]\s*>|##\s*)Education.*',
        cv_normalized, re.DOTALL | re.IGNORECASE
    )
    if edu_match:
        edu_section = edu_match.group(0)
        middlesex_pos = edu_section.find("Middlesex")
        aptech_pos = edu_section.find("Aptech")
        if middlesex_pos > aptech_pos and aptech_pos > 0:
            violations.append("EDUCATION ORDER: Middlesex must come before Aptech")

    return violations


# ──────────────────────────────────────────────
# CHECK 10: DATE FORMAT
# Date ranges should follow "Month Year – Month Year" or "Month Year to Month Year".
# Bad patterns include "(2022, 2024)" parenthetical date ranges.
# ──────────────────────────────────────────────
def check_date_format(cv_text):
    violations = []
    # Bad: parenthetical year ranges like "(2022, 2024)" or "(2024 - 2026)"
    paren_dates = re.findall(r'\(\d{4}[,\-–—\s]+\d{4}\)', cv_text)
    for bad in paren_dates:
        violations.append(f"BAD DATE FORMAT: '{bad}' — use 'Month Year – Month Year' instead")
    return violations


# ──────────────────────────────────────────────
# MAIN — run all checks, report all violations, exit 0 or 1
# ──────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("Usage: cv_validator.py <cv_markdown_or_html_path> <cv_profile_path>")
        sys.exit(1)

    cv_path = Path(sys.argv[1])
    profile_path = Path(sys.argv[2])

    if not cv_path.exists():
        print(f"ERROR: CV file not found: {cv_path}")
        sys.exit(1)
    if not profile_path.exists():
        print(f"ERROR: Profile file not found: {profile_path}")
        sys.exit(1)

    cv_text = cv_path.read_text()
    profile = load_profile(profile_path)

    all_checks = [
        ("LOCKED CONSTANTS",        check_locked_constants(cv_text, profile["locked_constants"])),
        ("FORBIDDEN UNIVERSITIES",  check_forbidden_universities(cv_text)),
        ("FORBIDDEN CLAIMS",        check_forbidden_claims(cv_text, profile["project_registry"])),
        ("REPO VISIBILITY",         check_repo_visibility(cv_text, profile["project_registry"])),
        ("EM DASHES",               check_em_dashes(cv_text)),
        ("FORBIDDEN VERBS",         check_forbidden_verbs(cv_text)),
        ("BLOCKED PHRASES",         check_blocked_phrases(cv_text)),
        ("SECTION COMPLETENESS",    check_section_completeness(cv_text)),
        ("EDUCATION",               check_education(cv_text)),
        ("DATE FORMAT",             check_date_format(cv_text)),
    ]

    total_violations = 0
    for check_name, violations in all_checks:
        if violations:
            print(f"\n{'='*60}")
            print(f"FAILED: {check_name} ({len(violations)} violations)")
            print(f"{'='*60}")
            for v in violations:
                print(f"  ✗ {v}")
            total_violations += len(violations)

    if total_violations == 0:
        print("\n✓ ALL CHECKS PASSED — CV is clean for PDF export")
        sys.exit(0)
    else:
        print(f"\n✗ {total_violations} TOTAL VIOLATIONS — fix before PDF export")
        sys.exit(1)


if __name__ == "__main__":
    main()
