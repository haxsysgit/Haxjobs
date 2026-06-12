# buildnext.md — CV Governance Build Plan

**For:** Arinze
**Date:** 2026-06-08
**Status:** Ready to build

---

## What Happened

On June 7, a CV was generated for Palantir. It had three bugs:

1. **Wrong university:** said "University of Hertfordshire" instead of "Middlesex University London"
2. **Unverified AI claims:** said Pharmax has "AI-powered features for intelligent product queries" — the public GitHub repo shows none of that
3. **Private repo linked:** Pharmax-backend URL was in the CV despite being a private repo

The CV structure, wording, and layout were otherwise good. The errors are all the same class: **the LLM generated text for fields where generation should never happen.** University name, dates, repo URLs, and project evidence are data — they should be copied from a source of truth, not synthesized from memory.

Asking an LLM to "remember Middlesex" works until one token drifts and you get Hertfordshire. The fix must be structural, not instructional.

---

## The Approach

Three layers, each one catches what the previous one misses:

```
SOURCE OF TRUTH  →  LLM GENERATION  →  VALIDATOR  →  PDF
   (JSON)            (Markdown)         (script)      (output)
```

- **Source of truth:** A JSON file with every immutable fact (university, dates, URLs) and every allowed project claim
- **LLM generation:** The LLM writes prose BUT immutable fields are pre-filled as template slots — the LLM never touches them. For projects, the LLM receives only the allowed evidence list and a blocklist of forbidden claims.
- **Validator:** A Python script that runs after generation and before PDF export. It greps for wrong universities, forbidden claims, private repo URLs, em dashes, forbidden verbs. One violation = PDF blocked.

The validator is the gate. The LLM can still hallucinate, but the hallucination cannot reach the PDF.

---

## What to Build

### File 1: `cv_profile.typed.json`

**Path:** `/home/hermes/haxjobs/profile/cv_profile.typed.json`

**Purpose:** The single source of truth for every immutable CV field. This file is hand-maintained by Arinze. The LLM never edits it.

**What it contains:**

```jsonc
{
  "locked": {
    // These values are NEVER generated — only copied verbatim into the CV.
    // If any of these differ in the output, validation fails.
    "headline":    "Python Backend Engineer | AI & Automation",
    "email":       "elenasuluarinze@gmail.com",
    "phone":       "+447****5497",
    "location":    "London, UK",
    "linkedin":    "linkedin.com/in/arinze-elenasulu-b011a1249",
    "github":      "github.com/haxsysgit",
    
    "university":       "Middlesex University London",
    "degree":            "BSc Computer Science",
    "graduation":        "Expected June 2026",
    
    "aptech_institution": "Aptech Computer Education, Lagos",
    "aptech_diploma":     "Advanced Diploma in Software Engineering (ADSE Java)",
    "aptech_dates":       "September 2022 – August 2024",
    
    "vigilis_title":     "Software Engineer",
    "vigilis_company":   "Vigilis",
    "vigilis_dates":     "August 2024 – February 2026",
    "vigilis_location":  "Lagos, Nigeria",
    
    "bucca_hut_title":    "AI and Backend Engineer (Contract, part-time)",
    "bucca_hut_company":  "Bucca Hut",
    "bucca_hut_dates":    "February 2025 – May 2025"
  },
  
  "projects": {
    // Every project that can appear in a CV. The LLM can only use
    // claims from "allowed_bullets". Anything in "blocked_claims"
    // triggers validation failure if found in the output.
    "pharmax": {
      "name": "Pharmax",
      "subtitle": "Pharmacy Management Platform",
      "stack": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Alembic"],
      "repo_url": null,
      "show_url": false,
      "allowed_bullets": [
        "Products CRUD with multi-unit pricing (tablets, packs, strips)",
        "Full invoice lifecycle: draft → finalise (auto stock deduction) → cancel (stock reversal)",
        "Stock adjustments with audit trail",
        "Reorder-level tracking",
        "Role-based access with JWT authentication",
        "Comprehensive pytest suite covering endpoints, business logic, and edge cases",
        "Sat with pharmacy staff to understand manual processes and turned them into software"
      ],
      "blocked_claims": [
        "AI-powered", "AI-assisted", "intelligent queries", "inventory insights",
        "machine learning", "LLM-powered", "AI features"
      ]
    },
    "haxaml": {
      "name": "Haxaml",
      "subtitle": "AI Agent Governance & Project Memory",
      "stack": ["Python", "MCP", "FRAME"],
      "repo_url": "https://github.com/haxsysgit/haxaml",
      "pypi_url": "https://pypi.org/project/haxaml",
      "show_url": true,
      "allowed_bullets": [
        "Five-part memory model (Facts, Rules, Acts, Map, Expect) for AI agent context",
        "MCP server so AI coding tools can read/write project memory during sessions",
        "Local dashboard for inspecting agent session history and project state",
        "Published on PyPI with documentation, setup flow, and adoption guides",
        "CLI tooling for managing project memory files"
      ],
      "blocked_claims": []
    },
    "caseframe": {
      "name": "CaseFRAME",
      "subtitle": "AI Continuity for Financial Crime Investigations",
      "stack": ["Python", "YAML"],
      "repo_url": "https://github.com/haxsysgit/CaseFRAME",
      "show_url": true,
      "allowed_bullets": [
        "Python loader and validator for structured case packs from YAML",
        "Concrete example: reopened sanctions review with unresolved counterparty links",
        "State-resumption model — investigation reopens from real case state, not from zero"
      ],
      "blocked_claims": []
    },
    "archilles": {
      "name": "Archilles",
      "subtitle": "Production AI Agent Infrastructure",
      "stack": ["Python", "Hermes Agent", "Multi-Agent Orchestration"],
      "repo_url": null,
      "show_url": false,
      "allowed_bullets": [
        "24/7 cloud-based AI agent running on Hermes Agent framework (fork)",
        "Multi-agent coordination across messaging, automation, and document generation",
        "Cron-scheduled job discovery and application pack pipelines",
        "Cross-platform messaging gateway (Telegram, Discord, WhatsApp)"
      ],
      "blocked_claims": [
        "Claude Code"
      ]
    }
  },
  
  "language_rules": {
    "blocked_verbs": [
      "Spearheaded", "Leveraged", "Orchestrated", "Drove", "Championed",
      "Utilized", "Harnessed", "Synergized", "Optimized"
    ],
    "blocked_phrases": [
      "Claude Code", "cutting-edge", "production-grade", "robust enterprise"
    ],
    "blocked_chars": ["—"]
  }
}
```

**Why this exists:** Before this file, the LLM generated university names, dates, and project claims from memory. Now those are locked constants and allowed-evidence lists. The LLM fills prose (summary, skill descriptions) but copies data.

---

### File 2: `cv_validator.py`

**Path:** `/home/hermes/haxjobs/cv_validator.py`

**Purpose:** Runs after the LLM generates a CV markdown file. Checks every rule that can be checked mechanically. Exit code 0 = clean, 1 = violations found. PDF export is blocked on exit code 1.

**What it checks (each check is a ~10-line function):**

| # | Check | What it catches | Example violation |
|---|---|---|---|
| 1 | `LOCKED_FIELDS` | Every locked value from the profile appears verbatim in the CV | CV says "Hertfordshire", profile says "Middlesex" |
| 2 | `WRONG_UNIVERSITIES` | Known-wrong university names are absent | "University of London", "UCL", "Hertfordshire" etc. |
| 3 | `BLOCKED_CLAIMS` | No forbidden project claim appears | Pharmax section says "AI-powered features" |
| 4 | `PRIVATE_REPOS` | No URL for a project with `show_url: false` | Pharmax-backend link in CV |
| 5 | `EM_DASHES` | Zero em dashes in the text | Any `—` character |
| 6 | `BLOCKED_VERBS` | No forbidden verb appears | "Spearheaded", "Leveraged" |
| 7 | `BLOCKED_PHRASES` | No blocked phrase appears | "Claude Code", "cutting-edge" |
| 8 | `SECTION_COMPLETENESS` | Summary has substance, skills has 4+ groups | Summary is 5 words, skills is empty |
| 9 | `EDUCATION_ORDER` | Middlesex listed before Aptech in education section | Aptech appears first |
| 10 | `DATE_FORMAT` | Date ranges use correct format | `(2022, 2024)` instead of `September 2022 – August 2024` |

**Key design decisions:**

- Each check function returns a list of violation strings (empty = pass)
- The main loop runs all checks regardless of failures — you get the full report, not just the first error
- Violations print to stdout with the exact text that failed
- The script takes two args: `cv_validator.py <cv_markdown.md> <cv_profile.typed.json>`

**The ~100 lines of actual validation logic are in the governance doc** (`CV_FRAME_GOVERNANCE.md`, section 4). Copy those functions into the script.

**Why this exists:** Without this, there's no gate between LLM output and PDF. The LLM can write anything and it ships. With this, violations are caught mechanically before they become a PDF that costs you an interview.

---

### File 3: `cv_template.html`

**Path:** `/home/hermes/haxjobs/cv_template.html`

**Purpose:** The HTML/CSS template for CV rendering. This file does NOT get regenerated each time — only the content slots are filled.

**What it contains:** The existing Palantir CV HTML (at `haxjobs/packs/Palantir_Forward_Deployed_AI_Engineer/Arinze_Elenasulu_Palantir_Tailored_CV.html`) is already good. Use it as the base template, but replace the hardcoded values with `{{SLOTS}}`:

```html
<!-- Header: locked values, never generated -->
<h1>Arinze Elenasulu</h1>
<h2>{{HEADLINE}}</h2>
<div>London, UK · {{EMAIL}} · {{PHONE}}</div>
<div>{{LINKEDIN}} · {{GITHUB}}</div>

<!-- Education: locked values, never generated -->
<div>{{DEGREE}}, {{UNIVERSITY}} ({{GRADUATION}})</div>
<div>{{APTECH_DIPLOMA}}, {{APTECH_INSTITUTION}} ({{APTECH_DATES}})</div>
```

The LLM fills: Professional Summary, Core Skills, experience bullets, project bullets. Everything else is template interpolation.

**Why this exists:** Even if the LLM hallucinates the university in the markdown, the HTML template overrides it with the locked value. Defense in depth.

---

### File 4: `cv_generate.py` (pipeline orchestrator)

**Path:** `/home/hermes/haxjobs/cv_generate.py`

**Purpose:** A Python script that runs the full pipeline in order. No step can be skipped.

**Pipeline:**

```
1. LOAD  → Read cv_profile.typed.json → fail if missing
2. BUILD → Fill template slots from locked values
3. GEN   → Call LLM to generate prose sections (summary, skills, bullets)
           LLM receives: allowed_bullets per project, blocked_claims, language_rules
4. MERGE → Combine template HTML + LLM prose → full markdown
5. VALIDATE → Run cv_validator.py → fail if violations
6. EXPORT → Convert markdown → HTML → PDF (headless Chrome)
7. SCAN   → Final grep for em dashes, wrong universities, blocked phrases in PDF text
```

**Why this exists:** Without a locked pipeline, steps get skipped. "I'll validate later" → never happens. The orchestrator enforces the sequence.

---

## What NOT to Build

- **Don't build a web UI or dashboard.** This is a CLI pipeline. Arinze runs it, reviews output, submits.
- **Don't build a new profile format.** Extend `arinze_profile.local.json` or create the typed profile as a sibling. Don't replace what already works.
- **Don't build auto-apply.** The pipeline stops at PDF generation. Arinze reviews and submits manually.
- **Don't over-engineer the validator.** 10 checks, ~150 lines of Python, exit code 0 or 1. No config files, no plugins, no YAML DSL for rules.
- **Don't rebuild the HTML template from scratch.** The existing Palantir CV HTML is the template. Just add `{{SLOTS}}`.

---

## Build Order

1. **`cv_profile.typed.json`** first — everything else depends on it
2. **`cv_validator.py`** second — test it against the broken Palantir CV to confirm it catches all 3 errors
3. **`cv_template.html`** third — add slots to the existing HTML
4. **`cv_generate.py`** last — the orchestrator that ties steps 1-3 together

---

## Why This Matters Beyond CVs

This is the same class of problem that shows up everywhere LLMs touch real data:

- Generating an email with a wrong meeting time
- Writing a contract with a hallucinated clause
- Producing a report with fabricated statistics

The pattern is always: **immutable data + LLM prose = risk of hallucination in the data.** The fix is always: **lock the data, validate the output, block on failure.**

CV generation is the first place you're applying this, but the validator pattern (`source of truth → generate → validate → ship`) works for any document where some fields are data and some are prose.

---

## Success Criteria

After building, the following should be true:

```bash
# Run against the broken Palantir CV (the one with Hertfordshire):
python3 cv_validator.py Palantir_broken_CV.md cv_profile.typed.json
# → Exit code 1, at minimum these violations:
#   - MISSING: "Middlesex University London"
#   - FORBIDDEN: "Hertfordshire" found
#   - FORBIDDEN CLAIM: "AI-powered features" in Pharmax
#   - PRIVATE REPO: Pharmax-backend URL with show_url=false

# Run against a corrected CV:
python3 cv_validator.py Palantir_fixed_CV.md cv_profile.typed.json
# → Exit code 0, "ALL CHECKS PASSED"
```

---

## Questions for Arinze — ANSWERED

1. **Pharmax repo visibility:** Treat as `show_url: false` — never include the link in any CV. The completed code is private. ✓

2. **Project evidence maintenance:** Build a helper script (`cv_profile_helper.py`) for adding/editing projects. ✓

3. **Cover letter validation:** CV-only for now. ✓
