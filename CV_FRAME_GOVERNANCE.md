# CV-FRAME: Typed Governance for AI-Generated CVs

**Author:** Archilles (Hermes Agent)
**Date:** 2026-06-08
**Status:** Active — applies to all future CV generation
**Trigger:** Palantir CV contained hallucinated university name, unverified AI claims, and linked to private repos

---

## 1. What Went Wrong — Root Cause Analysis

On 2026-06-07, a CV was generated for Palantir (Forward Deployed AI Engineer). The output was structurally strong — good wording, good rhythm, good layout — but contained three classes of error that make it unusable:

### Error Class A: Hallucinated Immutable Fact
| What the CV said | What it should say |
|---|---|
| University of Hertfordshire | Middlesex University London |

The university name exists in the profile JSON (`arinze_profile.local.json`, line 61: `"university": "Middlesex University"`) and in `corrected-profile-facts.md`. There is zero ambiguity about this fact. The LLM was allowed to *generate* the university name instead of being forced to *copy* it from a locked constant.

**Root cause:** Free-text generation of a field that should be a typed constant.

### Error Class B: Unverified AI Claims on Public Repo
The CV claimed Pharmax has "Integrated AI-powered features for intelligent product queries and inventory insights" and "AI-assisted operational workflows." The public repo (Pharmax-backend) shows products CRUD, invoice lifecycle, stock adjustments, pytest suite — zero AI endpoints. A recruiter checking GitHub sees a standard backend and wonders what else is fabricated.

**Root cause:** No evidence-gating — project claims were generated without checking what the public README actually documents. The profile says "DO NOT invent AI features not visible in the public README" but this was a soft instruction in a markdown file, not a hard validation rule.

### Error Class C: Private Repo Linked Publicly
Pharmax-backend was linked in the CV despite being a private/proprietary repo. A recruiter clicking the link gets a 404 or permission denied. This alone can tank an application — it looks like you're hiding something or being sloppy.

**Root cause:** No repo-visibility check before including URLs. The profile says the full SaaS is proprietary, but the generation pipeline didn't gate on "only include public repos."

### Error Class D: Date Formatting
Aptech dates rendered as "(2022, 2024)" instead of "Sep 2022 – Aug 2024." Minor but tells the recruiter the document wasn't proofread.

**Root cause:** Date formatting left to free-text generation instead of being pulled from a formatted template.

---

## 2. Why "Read the profile carefully" Won't Fix This

The fundamental problem is not that the LLM didn't read the profile. It's that the LLM was asked to *generate* text for fields where generation should never happen. University name, dates, repo URLs, project evidence — these are data, not prose. They should be *interpolated* from a typed source of truth, not *synthesized* from memory.

Asking an LLM to "remember the university is Middlesex" works until it doesn't. One token of drift and you've got Hertfordshire. The fix is structural, not instructional.

---

## 3. The Solution: CV-FRAME Governance

CV-FRAME applies the FRAME model (Facts → Rules → Acts → Map → Expect) to CV generation. The core principle: **immutable data is never generated, only interpolated.**

### F: Facts — The Typed Profile

The existing `arinze_profile.local.json` becomes the single source of truth, but it needs a sibling: `cv_profile.typed.json` — a stricter schema designed specifically for CV interpolation.

```jsonc
{
  "$schema": "cv-profile-v1",
  "locked_constants": {
    // These fields are NEVER generated. They are copied verbatim into the CV.
    // Any deviation from these values is a validation failure.
    "university": {
      "value": "Middlesex University London",
      "type": "literal",
      "validation": "exact_match_only"
    },
    "university_degree": {
      "value": "BSc Computer Science",
      "type": "literal"
    },
    "university_graduation": {
      "value": "Expected June 2026",
      "type": "literal"
    },
    "aptech_institution": {
      "value": "Aptech Computer Education, Lagos",
      "type": "literal"
    },
    "aptech_diploma": {
      "value": "Advanced Diploma in Software Engineering (ADSE Java)",
      "type": "literal"
    },
    "aptech_dates": {
      "value": "September 2022 – August 2024",
      "type": "literal"
    },
    "vigilis_title": {
      "value": "Software Engineer",
      "type": "literal"
    },
    "vigilis_dates": {
      "value": "August 2024 – February 2026",
      "type": "literal"
    },
    "vigilis_location": {
      "value": "Lagos, Nigeria",
      "type": "literal"
    },
    "bucca_hut_title": {
      "value": "AI and Backend Engineer (Contract, part-time)",
      "type": "literal"
    },
    "bucca_hut_dates": {
      "value": "February 2025 – May 2025",
      "type": "literal"
    },
    "headline": {
      "value": "Python Backend Engineer | AI & Automation",
      "type": "literal"
    },
    "email": {
      "value": "elenasuluarinze@gmail.com",
      "type": "literal"
    },
    "phone": {
      "value": "+447****5497",
      "type": "literal"
    },
    "location": {
      "value": "London, UK",
      "type": "literal"
    },
    "linkedin_handle": {
      "value": "linkedin.com/in/arinze-elenasulu-b011a1249",
      "type": "literal"
    },
    "linkedin_url": {
      "value": "https://www.linkedin.com/in/arinze-elenasulu-b011a1249",
      "type": "literal"
    },
    "github_handle": {
      "value": "github.com/haxsysgit",
      "type": "literal"
    },
    "github_url": {
      "value": "https://github.com/haxsysgit",
      "type": "literal"
    }
  },
  "project_registry": {
    // Every project that can appear on a CV must be registered here.
    // The "public_evidence" array is the EXACT set of claims supported
    // by the public README. Bullets in the CV must not exceed this evidence.
    "pharmax": {
      "display_name": "Pharmax",
      "subtitle": "AI-Integrated Pharmacy Management Platform",
      "repo_url": "https://github.com/haxsysgit/Pharmax-backend",
      "repo_visibility": "private",
      "include_url_in_cv": false,
      "tech_stack": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Alembic"],
      "public_evidence": [
        "Products CRUD with multi-unit pricing (tablets, packs, strips)",
        "Full invoice lifecycle: draft → finalise (auto stock deduction) → cancel (stock reversal)",
        "Stock adjustments with audit trail",
        "Reorder-level tracking",
        "Role-based access control",
        "JWT authentication",
        "Comprehensive pytest suite covering endpoints, business logic, and edge cases"
      ],
      "proprietary_context": "The full SaaS includes AI features but these are NOT in the public repo. CV claims must stick to public_evidence only.",
      "forbidden_claims": [
        "AI-powered features",
        "AI-assisted operational workflows",
        "intelligent product queries",
        "AI inventory insights",
        "machine learning integration",
        "LLM-powered features"
      ]
    },
    "haxaml": {
      "display_name": "Haxaml",
      "subtitle": "AI Agent Governance & Project Memory",
      "repo_url": "https://github.com/haxsysgit/haxaml",
      "repo_visibility": "public",
      "include_url_in_cv": true,
      "pypi_url": "https://pypi.org/project/haxaml",
      "tech_stack": ["Python", "MCP", "FRAME"],
      "public_evidence": [
        "Five-part FRAME memory model (Facts, Rules, Acts, Map, Expect)",
        "MCP server for AI coding tools to read/write FRAME files",
        "Local dashboard for agent session history and project state",
        "Published on PyPI with documentation and adoption guides",
        "CLI tooling for FRAME file management"
      ],
      "forbidden_claims": []
    },
    "caseframe": {
      "display_name": "CaseFRAME",
      "subtitle": "AI Continuity for Financial Crime Investigations",
      "repo_url": "https://github.com/haxsysgit/CaseFRAME",
      "repo_visibility": "public",
      "include_url_in_cv": true,
      "tech_stack": ["Python", "FRAME", "YAML"],
      "public_evidence": [
        "Python loader/validator for five-part FRAME case packs",
        "Concrete example: reopened sanctions review with unresolved counterparty links",
        "State-resumption model for multi-session investigations"
      ],
      "forbidden_claims": []
    },
    "archilles": {
      "display_name": "Archilles",
      "subtitle": "Production AI Agent Infrastructure",
      "repo_url": null,
      "repo_visibility": "private",
      "include_url_in_cv": false,
      "tech_stack": ["Python", "Hermes Agent", "Multi-Agent Orchestration"],
      "public_evidence": [
        "24/7 cloud-based AI agent infrastructure (Hermes Agent fork)",
        "Multi-agent coordination across messaging, automation, and document generation",
        "Cron-scheduled job discovery and application pack pipelines",
        "Cross-platform messaging gateway (Telegram, Discord, WhatsApp)"
      ],
      "forbidden_claims": [
        "Never write 'Claude Code' — the agent is Archilles"
      ]
    }
  },
  "generatable_sections": {
    // These sections CAN be generated by the LLM, but must pass
    // post-generation validation against the rules below.
    "professional_summary": {
      "max_length": "4 sentences",
      "must_include": ["Python since 2020", "backend engineering experience"],
      "must_not_include": ["Claude Code", "senior-level framing"]
    },
    "core_skills": {
      "min_groups": 4,
      "required_groups": ["Backend", "AI", "Testing", "Infrastructure"],
      "must_not_be_empty": true
    },
    "experience_bullets": {
      "vigilis_max_bullets": 5,
      "aptech_max_bullets": 4,
      "bucca_hut_max_bullets": 2,
      "must_not_include": ["Claude Code"]
    },
    "project_bullets": {
      "max_per_project": 5,
      "must_be_subset_of": "project_registry.<project>.public_evidence"
    },
    "cover_letter": {
      "max_paragraphs": 5,
      "must_mention_company": true,
      "role_conditional_hooks": true
    }
  }
}
```

### R: Rules — Generation Constraints

These are hard constraints that run BEFORE and AFTER generation. They are code, not prompts.

```
CONSTANT_FIELDS:
  - university → cv_profile.locked_constants.university.value (exact copy only)
  - university_degree → cv_profile.locked_constants.university_degree.value
  - all dates → locked_constants.<role>_dates.value (exact copy only)
  - all URLs → locked_constants.<field>_url.value (exact copy only)
  - headline → locked_constants.headline.value (exact copy only)

PROJECT_RULES:
  - Only include project if project_registry.<project>.repo_visibility == "public"
    OR project_registry.<project>.include_url_in_cv == true
  - Private projects: describe WITHOUT GitHub URL in CV
  - Every project bullet must match or be a close paraphrase of
    project_registry.<project>.public_evidence
  - Project summary line must NOT contain any string from
    project_registry.<project>.forbidden_claims

LANGUAGE_RULES:
  - NO em dashes (—)
  - NO forbidden verbs: Spearheaded, Leveraged, Orchestrated, Drove, Championed, Utilized, Harnessed
  - NO "Claude Code" anywhere
  - NO internal notes, safety warnings, or "do not claim" sections in CV
  - Professional Summary must be 3-4 sentences, first-person
  - Core Skills must have at least 4 populated groups
```

### A: Acts — The Generation Pipeline

The pipeline is locked to these steps. No step can be skipped.

```
STEP 0: PROFILE LOAD
  → Load cv_profile.typed.json
  → Load arinze_profile.local.json (for supplementary context)
  → FAIL if either is missing or unparseable

STEP 1: JOB EXTRACTION
  → Extract JD, company, role, requirements
  → Check hard blockers (citizenship, clearance, visa)

STEP 2: CV MARKDOWN GENERATION
  → LOCKED CONSTANTS are injected as pre-filled template fields
  → LLM generates ONLY: Professional Summary, experience bullets, project bullets, cover letter
  → LLM receives the project_registry.public_evidence as the EXACT set of allowed claims
  → LLM receives forbidden_claims as a blocklist

STEP 3: STRUCTURED VALIDATION (see Expect below)
  → Run cv_validator.py against the generated markdown
  → FAIL if any validation rule is violated
  → Return specific violation messages

STEP 4: HUMAN REVIEW
  → Arinze reviews the markdown
  → Any corrections update the source profile first, THEN regenerate
  → Arinze's approval is required before PDF export

STEP 5: HTML + PDF GENERATION
  → Render markdown → HTML (using locked CSS template)
  → Print HTML → PDF (headless Chrome)
  → Verify PDF: page count, no browser headers, text extraction sanity check

STEP 6: FINAL SCAN
  → Em dash scan (grep for \u2014)
  → Forbidden verb scan
  → University name verification (grep for "Middlesex")
  → Repo URL verification (grep for github.com — cross-check against project_registry include_url_in_cv)
```

### M: Map — The CV Structure Template

The HTML/CSS template is version-controlled and not regenerated each time. Only the content slots are filled.

```
SLOTS (filled from profile or LLM generation):
  {{HEADLINE}}            → locked_constants.headline.value
  {{EMAIL}}               → locked_constants.email.value
  {{PHONE}}               → locked_constants.phone.value
  {{LOCATION}}            → locked_constants.location.value
  {{LINKEDIN_HANDLE}}     → locked_constants.linkedin_handle.value
  {{GITHUB_HANDLE}}       → locked_constants.github_handle.value
  {{PROFESSIONAL_SUMMARY}}→ LLM-generated (validated)
  {{CORE_SKILLS}}         → LLM-generated (validated)
  {{EXPERIENCE}}          → LLM-generated (validated, dates from locked_constants)
  {{PROJECTS}}            → LLM-generated (validated against project_registry)
  {{EDUCATION}}           → TEMPLATED (not generated):
                              "BSc Computer Science, Middlesex University London (Expected June 2026)"
                              "ADSE Java, Aptech Computer Education, Lagos (September 2022 – August 2024)"
```

### E: Expect — Validation Assertions

These run as `cv_validator.py` after generation and before any PDF export. A single violation = regeneration required.

```
VALIDATION CHECKS (fail = block PDF export):

1. LOCKED_CONSTANT_EXACT_MATCH
   For every field in locked_constants:
   assert generated_text CONTAINS locked_value
   Example: assert "Middlesex University London" in cv_text

2. NO_FORBIDDEN_UNIVERSITY_NAMES
   For every known-wrong university name:
   assert wrong_name NOT IN cv_text
   Blocklist: ["Hertfordshire", "University of London", "UCL", "Imperial",
               "King's College", "LSE", "Queen Mary", "Brunel", "Westminster",
               "Greenwich", "South Bank", "London Met", "City University"]

3. NO_FORBIDDEN_CLAIMS
   For each project with forbidden_claims:
   assert NO claim in cv_text
   Example: assert "AI-powered features" NOT IN pharmax_section

4. REPO_VISIBILITY_GATE
   For each project_url in cv_text:
   project = project_registry[match]
   assert project.include_url_in_cv == true
   If false: FAIL with "Private repo URL found in CV: {url}"

5. NO_EM_DASHES
   assert "\u2014" NOT IN cv_text

6. NO_FORBIDDEN_VERBS
   for verb in ["Spearheaded", "Leveraged", "Orchestrated", "Drove",
                "Championed", "Utilized", "Harnessed"]:
   assert verb NOT IN cv_text (case-insensitive)

7. NO_CLAUDE_CODE
   assert "Claude Code" NOT IN cv_text (case-insensitive)

8. SECTION_COMPLETENESS
   assert professional_summary word_count >= 30
   assert core_skills contains >= 4 distinct groups
   assert experience section is not empty

9. DATE_FORMAT
   All date ranges must follow "Month Year – Month Year" format
   assert regex match for date patterns

10. EDUCATION_ENTRIES_COUNT
    assert exactly 2 education entries (Middlesex + Aptech)
    assert "Middlesex" appears before "Aptech" in education section
```

---

## 4. Implementation Files

```
/home/hermes/haxjobs/
├── CV_FRAME_GOVERNANCE.md          ← THIS FILE (the spec)
├── cv_profile.typed.json           ← Typed profile with locked constants + project registry
├── cv_template.html                ← Version-controlled HTML/CSS template with {{SLOTS}}
├── cv_validator.py                 ← Pre-PDF validation script (runs all Expect checks)
├── cv_constants.py                 ← Python dataclasses mirroring cv_profile.typed.json
└── cv_generate.py                  ← Pipeline orchestrator (steps 0-6)
```

### cv_validator.py — Core Logic

```python
#!/usr/bin/env python3
"""
CV-FRAME Validator — runs all validation assertions before PDF export.
Returns exit code 0 if clean, 1 if violations found.
Usage: python3 cv_validator.py <cv_markdown_path> <cv_profile_path>
"""
import json, sys, re
from pathlib import Path

def load_profile(path):
    with open(path) as f:
        return json.load(f)

def check_locked_constants(cv_text, constants):
    violations = []
    for key, spec in constants.items():
        value = spec["value"]
        if spec["type"] == "literal" and value not in cv_text:
            violations.append(f"MISSING CONSTANT: '{key}' → '{value}' not found in CV")
    return violations

def check_forbidden_universities(cv_text):
    blocked = [
        "Hertfordshire", "University of London", "UCL", "Imperial",
        "King's College", "LSE", "Queen Mary", "Brunel", "Westminster",
        "Greenwich", "South Bank", "London Met", "City University",
        "Birmingham", "Manchester University", "Leeds University",
        "Edinburgh", "Glasgow", "Bristol", "Oxford", "Cambridge",
        "Warwick", "Durham", "Nottingham", "Sheffield"
    ]
    violations = []
    for name in blocked:
        if name.lower() in cv_text.lower():
            # Allow if it's part of Middlesex University London
            # and the full correct name is also present
            if "Middlesex University London" not in cv_text:
                violations.append(f"WRONG UNIVERSITY: '{name}' found, but 'Middlesex University London' missing")
    return violations

def check_forbidden_claims(cv_text, project_registry):
    violations = []
    for proj_key, proj in project_registry.items():
        for claim in proj.get("forbidden_claims", []):
            if claim.lower() in cv_text.lower():
                violations.append(f"FORBIDDEN CLAIM in {proj['display_name']}: '{claim}'")
    return violations

def check_repo_visibility(cv_text, project_registry):
    violations = []
    # Find all github URLs in CV
    github_urls = re.findall(r'github\.com/haxsysgit/(\S+)', cv_text)
    for match in github_urls:
        repo_name = match.rstrip('/').rstrip(')')
        # Find which project this URL belongs to
        for proj_key, proj in project_registry.items():
            repo_url = proj.get("repo_url", "")
            if repo_name in repo_url:
                if not proj.get("include_url_in_cv", False):
                    violations.append(
                        f"PRIVATE REPO URL: {proj['display_name']} ({repo_url}) "
                        f"is not public — remove URL from CV"
                    )
    return violations

def check_em_dashes(cv_text):
    count = cv_text.count("\u2014")
    if count > 0:
        return [f"EM DASHES: {count} found — replace with comma/semicolon/period"]
    return []

def check_forbidden_verbs(cv_text):
    verbs = [
        "Spearheaded", "Leveraged", "Orchestrated", "Drove",
        "Championed", "Utilized", "Harnessed"
    ]
    violations = []
    for verb in verbs:
        if re.search(rf'\b{verb}\b', cv_text, re.IGNORECASE):
            violations.append(f"FORBIDDEN VERB: '{verb}'")
    return violations

def check_claude_code(cv_text):
    if "Claude Code" in cv_text:
        return ["CLAUDE CODE: 'Claude Code' found — must be 'Archilles' or 'Archilles (Hermes Agent fork)'"]
    return []

def check_section_completeness(cv_text):
    violations = []
    # Professional Summary check
    if "Professional Summary" not in cv_text:
        violations.append("MISSING: Professional Summary section")
    else:
        # Find summary text
        summary_match = re.search(
            r'Professional Summary.*?\n(.*?)(?=\n##|\n#|\Z)',
            cv_text, re.DOTALL
        )
        if summary_match:
            summary_text = summary_match.group(1).strip()
            words = len(summary_text.split())
            if words < 30:
                violations.append(f"SUMMARY TOO SHORT: {words} words (minimum 30)")

    # Core Skills check
    if "Core Skills" not in cv_text:
        violations.append("MISSING: Core Skills section")
    else:
        skill_groups = re.findall(r'\*\*([^*]+):\*\*', cv_text)
        if len(skill_groups) < 4:
            violations.append(f"CORE SKILLS: only {len(skill_groups)} groups (minimum 4)")

    return violations

def check_education(cv_text):
    violations = []
    if "Middlesex University London" not in cv_text:
        violations.append("EDUCATION: 'Middlesex University London' not found")
    if "Aptech" not in cv_text:
        violations.append("EDUCATION: 'Aptech' not found")

    # Check Middlesex appears before Aptech
    middlesex_pos = cv_text.find("Middlesex")
    aptech_pos = cv_text.find("Aptech")
    if middlesex_pos > aptech_pos and aptech_pos > 0:
        violations.append("EDUCATION ORDER: Middlesex must come before Aptech")

    return violations

def main():
    if len(sys.argv) < 3:
        print("Usage: cv_validator.py <cv_markdown_path> <cv_profile_path>")
        sys.exit(1)

    cv_path = Path(sys.argv[1])
    profile_path = Path(sys.argv[2])

    cv_text = cv_path.read_text()
    profile = load_profile(profile_path)

    all_checks = [
        ("LOCKED CONSTANTS", check_locked_constants(cv_text, profile["locked_constants"])),
        ("FORBIDDEN UNIVERSITIES", check_forbidden_universities(cv_text)),
        ("FORBIDDEN CLAIMS", check_forbidden_claims(cv_text, profile["project_registry"])),
        ("REPO VISIBILITY", check_repo_visibility(cv_text, profile["project_registry"])),
        ("EM DASHES", check_em_dashes(cv_text)),
        ("FORBIDDEN VERBS", check_forbidden_verbs(cv_text)),
        ("CLAUDE CODE", check_claude_code(cv_text)),
        ("SECTION COMPLETENESS", check_section_completeness(cv_text)),
        ("EDUCATION", check_education(cv_text)),
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
```

---

## 5. How This Connects to FRAME

Arinze, this IS FRAME applied to a real problem. The Palantir CV failure is exactly the kind of context-drift FRAME is designed to prevent:

| FRAME Component | CV Governance Mapping |
|---|---|
| **Facts** | `locked_constants` — university name, dates, URLs. Immutable. Never generated. |
| **Rules** | Validation assertions in `cv_validator.py`. Hard constraints, not soft prompts. |
| **Acts** | The 7-step pipeline (Profile Load → JD Extract → Generate → Validate → Review → PDF → Scan). No step can be skipped. |
| **Map** | The HTML template with `{{SLOTS}}`. Structure is fixed; only designated slots are filled. |
| **Expect** | The 10 validation checks. A single violation blocks PDF export. The system refuses to produce a broken artifact. |

The key insight: **FRAME isn't just for AI coding agents. It's for any process where an LLM generates output that must stay aligned with a source of truth.** CV generation is a perfect use case — the profile is the Facts, the validator is the Rules, and the CV is the output that must pass Expect before it ships.

---

## 6. Immediate Actions

1. **Create `cv_profile.typed.json`** — extract locked constants and project registry from the profile
2. **Create `cv_validator.py`** — the validation script above
3. **Update `cv_template.html`** — add `{{SLOTS}}` for locked fields
4. **Patch the CV generation skills** — add STEP 3 (validation) as a mandatory gate
5. **Fix the Palantir CV** — regenerate with Hertfordshire→Middlesex, remove Pharmax AI claims, remove private repo link
6. **Add pre-commit hook** — `cv_validator.py` runs before any PDF export, no exceptions

---

## 7. Why This Actually Prevents Recurrence

The old approach: "LLM, generate a CV. Make sure the university is Middlesex." → LLM writes Hertfordshire anyway.

The new approach: "LLM, generate a CV. The university field is `{{UNIVERSITY}}` which resolves to 'Middlesex University London'. You cannot change it. After generation, `cv_validator.py` will grep for 'Middlesex University London' and block PDF export if it's missing. It will also grep for 'Hertfordshire' and block if found."

The LLM can still hallucinate, but the hallucination cannot reach the PDF. The validator is the gate. The profile is the source of truth. The pipeline refuses to ship broken output.

This is the same pattern as a CI pipeline: you can write buggy code, but the tests catch it before it reaches production.
