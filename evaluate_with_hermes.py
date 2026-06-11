#!/usr/bin/env python3
"""
Hermes-based structured job fit evaluator — v2.0.
Evaluates ONE job at a time against Arinze's profile using Hermes.
Saves results to both pipeline_db AND intake JSON file.

Usage:
  python3 evaluate_with_hermes.py --next           # Process next pending job
  python3 evaluate_with_hermes.py --batch 1        # Process 1 pending job
  python3 evaluate_with_hermes.py intake/file.json # Process specific intake file
  python3 evaluate_with_hermes.py --all-pending    # Process all (one at a time)
"""
import json, os, sys, glob, re, subprocess
from datetime import datetime, timezone

BASE_DIR = "/home/hermes/haxjobs"
INTAKE_DIR = os.path.join(BASE_DIR, "intake")
PROFILE_PATH = os.path.join(BASE_DIR, "profile", "arinze_profile.local.json")
HERMES_BIN = "hermes"

# Import pipeline_db
sys.path.insert(0, BASE_DIR)
import pipeline_db as db

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


def build_profile_blurb(company=""):
    if not os.path.exists(PROFILE_PATH):
        return "Profile not found."

    p = load_json(PROFILE_PATH)
    up = p.get("user_profile", {})
    facts = p.get("confirmed_profile_facts", [])
    eval_context = p.get("evaluation_context", {})
    company_notes = p.get("company_notes", {})

    by_cat = {}
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


def build_prompt(title, company, location, jd_text, source_url):
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


def _build_whitelist_context(company, title):
    """Build whitelist context from DB for the evaluation prompt."""
    try:
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


def extract_json(text):
    """Extract JSON object from Hermes output. Handles box chars and \\r\\n."""
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
    # (more robust: find all brace pairs and try each)
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


def validate_result(result):
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


def call_hermes(prompt, retries=2):
    """Call hermes chat with the evaluation prompt."""
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                [HERMES_BIN, "chat", "--yolo", "-q", prompt],
                capture_output=True, text=True, timeout=180,
                env={**os.environ, "HOME": os.path.expanduser("~")}
            )
            output = result.stdout.strip()

            # Log raw output
            log_path = os.path.join(BASE_DIR, "state", "hermes_eval.log")
            with open(log_path, "a") as lf:
                lf.write(f"\n--- {datetime.now(timezone.utc).isoformat()} (attempt {attempt+1}) ---\n")
                lf.write(f"EXIT: {result.returncode}\n")
                lf.write(f"STDOUT ({len(output)} chars):\n{output[:2000]}\n")
                if result.stderr:
                    lf.write(f"STDERR:\n{result.stderr[:500]}\n")

            parsed = extract_json(output)
            if parsed:
                issues = validate_result(parsed)
                if not issues:
                    return parsed

                fix_prompt = f"Your previous JSON had issues: {', '.join(issues)}. Return ONLY valid JSON with all fields."
                prompt = prompt + "\n\n" + fix_prompt

        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue

    return None


def evaluate_one_job(job_data):
    """Evaluate a single job dict. Returns Hermes result or None."""
    title = job_data.get("title", "Unknown")
    company = job_data.get("company", "Unknown")
    location = job_data.get("location", "")
    jd_text = job_data.get("jd_text", "")
    source_url = job_data.get("source_url", "")

    print(f"  Evaluating: {company} — {title[:60]}")

    prompt = build_prompt(title, company, location, jd_text, source_url)
    result = call_hermes(prompt)

    if not result:
        print(f"  FAILED: Hermes did not return valid JSON")
        return None

    return result


def evaluate_from_db():
    """Get next pending job from DB, evaluate it, save result."""
    db.init()
    pending = db.get_pending_jobs(1)
    if not pending:
        print("No pending jobs in DB.")
        return False

    job = pending[0]
    job_id = job["id"]
    print(f"Evaluating job DB#{job_id}: {job['company']} — {job['title'][:60]}")

    result = evaluate_one_job(job)
    if not result:
        return False

    # Save to DB
    result["evaluated_by"] = "hermes"
    db.save_evaluation(job_id, result)
    print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")

    # Also update the intake JSON file if it exists
    ext_id = job.get("external_id")
    if ext_id:
        fpath = os.path.join(INTAKE_DIR, ext_id)
        if os.path.exists(fpath):
            try:
                intake = json.load(open(fpath))
                intake["status"] = "evaluated" if result["decision"] == "completed" else "skipped"
                intake["fit_report"] = {
                    "fit_score": result["fit_score"],
                    "fit_verdict": result["fit_verdict"],
                    "strongest_matches": result.get("strongest_matches", []),
                    "major_gaps": result.get("major_gaps", []),
                    "sponsorship_risk": result.get("sponsorship_risk", "medium"),
                    "summary": result.get("summary", ""),
                }
                intake["level"] = result["level"]
                intake["level_name"] = result["level_name"]
                intake["evaluated_by"] = "hermes"
                intake["evaluated_at"] = datetime.now(timezone.utc).isoformat()
                if result.get("skip_reason"):
                    intake["skip_reason"] = result["skip_reason"]
                with open(fpath, "w") as f:
                    json.dump(intake, f, indent=2)
            except Exception as e:
                print(f"  WARNING: Could not update intake JSON: {e}")

    return True


def evaluate_intake_file(fpath):
    """Evaluate a single intake JSON file. Legacy path — prefer DB path."""
    try:
        job = load_json(fpath)
    except Exception:
        print(f"  ERROR: Cannot read {fpath}")
        return False

    if job.get("status") not in ("pending",):
        print(f"  SKIP: Already {job.get('status')} — {os.path.basename(fpath)}")
        return False

    # Ensure job exists in DB
    fname = os.path.basename(fpath)
    db_job = db.get_job(db.insert_job(
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", ""),
        jd_text=job.get("jd_text", ""),
        source_url=job.get("source_url", ""),
        source=job.get("source", "unknown"),
        external_id=fname,
    ))

    if not db_job:
        print(f"  WARNING: Could not sync to DB, evaluating from file only")

    result = evaluate_one_job(job)
    if not result:
        return False

    # Save to DB if possible
    db_jobs = db.get_pending_jobs(1)
    if db_jobs:
        result["evaluated_by"] = "hermes"
        db.save_evaluation(db_jobs[0]["id"], result)

    # Write back to intake file
    job["fit_report"] = {
        "fit_score": result["fit_score"],
        "fit_verdict": result["fit_verdict"],
        "strongest_matches": result.get("strongest_matches", []),
        "major_gaps": result.get("major_gaps", []),
        "sponsorship_risk": result.get("sponsorship_risk", "medium"),
        "summary": result.get("summary", ""),
    }
    job["status"] = "evaluated" if result["decision"] == "completed" else "skipped"
    job["level"] = result["level"]
    job["level_name"] = result["level_name"]
    if result.get("skip_reason"):
        job["skip_reason"] = result["skip_reason"]
    job["evaluated_at"] = datetime.now(timezone.utc).isoformat()
    job["evaluated_by"] = "hermes"

    with open(fpath, "w") as f:
        json.dump(job, f, indent=2)

    print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")
    return True


def get_pending_from_intake(limit=None):
    """Get pending intake files, oldest first."""
    files = sorted(glob.glob(os.path.join(INTAKE_DIR, "*.json")))
    pending = []
    for f in files:
        try:
            d = load_json(f)
            if d.get("status") == "pending":
                pending.append(f)
        except Exception:
            pass
    if limit:
        pending = pending[:limit]
    return pending


if __name__ == "__main__":
    db.init()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  evaluate_with_hermes.py --next           # Next pending job from DB")
        print("  evaluate_with_hermes.py --batch 1        # Process 1 pending")
        print("  evaluate_with_hermes.py --all-pending    # Process all (one at a time)")
        print("  evaluate_with_hermes.py intake/file.json # Specific file")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--next":
        ok = evaluate_from_db()
        sys.exit(0 if ok else 1)

    elif arg == "--batch":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        # Prefer DB path
        db.init()
        pending = db.get_pending_jobs(limit)
        if pending:
            for job in pending:
                result = evaluate_one_job(job)
                if result:
                    result["evaluated_by"] = "hermes"
                    db.save_evaluation(job["id"], result)
                    print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")
                    # Also update the intake JSON file if it exists
                    ext_id = job.get("external_id")
                    if ext_id:
                        fpath = os.path.join(INTAKE_DIR, ext_id)
                        if os.path.exists(fpath):
                            try:
                                intake = json.load(open(fpath))
                                intake["status"] = "evaluated" if result["decision"] == "completed" else "skipped"
                                intake["fit_report"] = {
                                    "fit_score": result["fit_score"],
                                    "fit_verdict": result["fit_verdict"],
                                    "strongest_matches": result.get("strongest_matches", []),
                                    "major_gaps": result.get("major_gaps", []),
                                    "sponsorship_risk": result.get("sponsorship_risk", "medium"),
                                    "summary": result.get("summary", ""),
                                }
                                intake["level"] = result["level"]
                                intake["level_name"] = result["level_name"]
                                intake["evaluated_by"] = "hermes"
                                intake["evaluated_at"] = datetime.now(timezone.utc).isoformat()
                                if result.get("skip_reason"):
                                    intake["skip_reason"] = result["skip_reason"]
                                with open(fpath, "w") as f:
                                    json.dump(intake, f, indent=2)
                            except Exception as e:
                                print(f"  WARNING: Could not update intake JSON: {e}")
                else:
                    print(f"  FAILED for job #{job['id']}")
        else:
            # Fall back to intake files
            files = get_pending_from_intake(limit)
            if not files:
                print("No pending jobs.")
                sys.exit(0)
            ok = 0
            for fpath in files:
                if evaluate_intake_file(fpath):
                    ok += 1
            print(f"\nDone. {ok}/{len(files)} evaluated.")

    elif arg == "--all-pending":
        # Process all, one at a time
        total = 0
        while True:
            db.init()
            pending = db.get_pending_jobs(1)
            if not pending:
                break
            result = evaluate_one_job(pending[0])
            if result:
                result["evaluated_by"] = "hermes"
                db.save_evaluation(pending[0]["id"], result)
                print(f"  → {result['fit_verdict']} (score={result['fit_score']})")
                total += 1
            else:
                print("  FAILED — stopping")
                break
        print(f"\nDone. {total} jobs evaluated.")

    else:
        # Assume it's a file path
        ok = evaluate_intake_file(arg)
        sys.exit(0 if ok else 1)
