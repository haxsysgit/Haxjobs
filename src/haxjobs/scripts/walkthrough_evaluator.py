#!/usr/bin/env python3
"""HaxJobs evaluator walkthrough — see how evaluation actually works.

Usage:
  python3 scripts/walkthrough_evaluator.py              # full walkthrough with real LLM calls
  python3 scripts/walkthrough_evaluator.py --job 625    # specific job
  python3 scripts/walkthrough_evaluator.py --dry-run    # show prompt without calling LLMs
  python3 scripts/walkthrough_evaluator.py --adapter hermes  # use hermes instead of codex
  python3 scripts/walkthrough_evaluator.py --quick      # skip explanations, just evaluate

Steps:
  1. Fetch a job from state/haxjobs.db
  2. build_prompt() — merges profile JSON + JD into 17K-char string
  3. Adapter subprocess — send prompt, capture LLM output
  4. extract_json() — regex out the JSON from raw stdout
  5. validate_result() — check keys, types, ranges
  6. Return normalized dict
"""

import sqlite3
import json
import sys
import time
from pathlib import Path

# Ensure repo root is on path so imports work regardless of how script is invoked
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def explain(msg: str = None) -> None:
    """Print explanation or blank line. All explanations go through this."""
    if EXPLAIN:
        if msg:
            print(f"  {msg}")
        else:
            print()


def header(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}\n")


def step1_fetch_job(job_id: int) -> dict:
    """Fetch a job from the database."""
    db = sqlite3.connect("state/haxjobs.db")
    db.row_factory = sqlite3.Row

    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    db.close()

    if not row:
        print(f"No job with id={job_id}")
        # fall back to first job with a real JD
        db = sqlite3.connect("state/haxjobs.db")
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT * FROM jobs WHERE jd_text IS NOT NULL AND length(jd_text) > 200 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        db.close()
        if row:
            print(f"Using job #{row['id']} instead")
        else:
            sys.exit("No jobs in DB at all")

    job = dict(row)
    explain(f"Table: jobs  →  Row #{job['id']}")
    explain(f"Columns used: title, company, location, jd_text, source_url")
    explain(f"Title:   {job['title']}")
    explain(f"Company: {job['company']}")
    explain(f"JD:      {len(job['jd_text'])} chars")
    explain(f"Source:  {job['source_url']}")
    explain()
    return job


def step2_build_prompt(job: dict) -> str:
    """Build the evaluation prompt from job data + profile JSON."""
    from haxjobs.evaluate.common import build_prompt

    prompt = build_prompt(
        job["title"],
        job["company"],
        job["location"],
        job["jd_text"],
        job["source_url"],
    )

    explain(f"build_prompt(title, company, location, jd_text, source_url)")
    explain(f"  ├─ build_profile_blurb(company)")
    explain(f"  │   reads profile/arinze_profile.local.json")
    explain(f"  │   extracts: user_profile, confirmed_profile_facts, evaluation_context")
    explain(f"  │   builds: basics + skills + facts (with CV wording) + guardrails + scoring")
    explain(f"  ├─ _build_whitelist_context(company, title)")
    explain(f"  │   queries DB for whitelist patterns matching this job")
    explain(f"  └─ assembles: Profile + Whitelist + JD + Output format instructions")
    explain(f"")
    explain(f"Result: {len(prompt)} chars (~{len(prompt)//4} tokens)")
    explain(f"Lines:  {len(prompt.split(chr(10)))}")
    explain()

    # Show prompt sections
    sections = []
    current = []
    for line in prompt.split("\n"):
        if line.startswith("## ") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)

    explain("Prompt structure:")
    for sec in sections:
        title_line = sec[0] if sec else "(empty)"
        char_count = sum(len(l) for l in sec)
        explain(f"  {title_line[:70]:<72} {char_count:>6} chars")
    explain()

    return prompt


def step3_run_adapter(job: dict, prompt: str, adapter_name: str) -> dict | None:
    """Run the evaluation through the chosen adapter."""
    from haxjobs.evaluate.chain import evaluate_one_job

    explain(f"evaluate_one_job(job, agent_order=['{adapter_name}'])")
    explain(f"  ├─ looks up '{adapter_name}' in evaluate.agents.AGENT_LIST")
    explain(f"  ├─ gets {adapter_name.title()}Adapter instance")
    explain(f"  └─ calls adapter.evaluate_job(job_dict)")

    from haxjobs.evaluate.agents import AGENT_LIST
    adapter = AGENT_LIST.get(adapter_name)
    if adapter:
        explain(f"      can_evaluate_headless() = {adapter.can_evaluate_headless()}")
        explain(f"      can_evaluate_session()  = {adapter.can_evaluate_session()}")
        explain()

    start = time.time()
    result = evaluate_one_job(job, agent_order=[adapter_name])
    elapsed = time.time() - start
    explain(f"Completed in {elapsed:.1f}s")

    return result


def step4_parse_validate(result: dict | None) -> None:
    """Show how parsing and validation work."""
    from haxjobs.evaluate.common import extract_json, validate_result

    if result is None:
        explain("FAILED — adapter returned None")
        return

    explain("Adapter already parsed + validated via BaseAdapter.evaluate_job().")
    explain("Here's what happens inside:")
    explain()
    explain("1. Adapter subprocess returns raw stdout string")
    explain("   e.g. codex returns:  {\"fit_score\":76,\"fit_verdict\":\"STRONG_FIT\",...}")
    explain("   e.g. pi returns:     JSONL event stream (parsed by _extract_json_from_jsonl)")
    explain()
    explain("2. extract_json(raw) — finds JSON object containing 'fit_score'")
    explain("   Uses regex:  r'\\{[^{}]*\"fit_score\"[^{}]*\\}'")
    explain("   Falls back to: stripping ``` fences, finding first {")
    explain()
    explain("3. validate_result(parsed) — checks 10 required keys:")
    explain("   fit_score (int, 0-100)     fit_verdict (str)")
    explain("   level (int, 1-4)           level_name (str)")
    explain("   strongest_matches (list)   major_gaps (list)")
    explain("   sponsorship_risk (str)     summary (str)")
    explain("   decision (str)             skip_reason (str)")
    explain()
    explain("4. If any key missing or wrong type → returns list of issues")
    explain("5. If issues is empty → VALID, result returned to caller")
    explain()


def step5_show_result(result: dict | None) -> None:
    """Display the final evaluation result."""
    if result is None:
        print("  ❌ No result")
        return

    print(f"\n  ┌{'─' * 40}")
    print(f"  │ Score:  {result['fit_score']} / 100")
    print(f"  │ Level:  {result['level']} — {result['level_name']}")
    print(f"  │ Verdict: {result['fit_verdict']}")
    print(f"  │ Agent:  {result.get('evaluated_by', '?')}")
    print(f"  ├{'─' * 40}")
    print(f"  │ Sponsor risk: {result['sponsorship_risk']}")
    print(f"  │ Summary: {result['summary'][:120]}...")
    print(f"  ├{'─' * 40}")
    print(f"  │ Strongest matches ({len(result['strongest_matches'])}):")
    for m in result["strongest_matches"]:
        print(f"  │   + {m[:100]}")
    print(f"  │ Major gaps ({len(result['major_gaps'])}):")
    for g in result["major_gaps"]:
        print(f"  │   - {g[:100]}")
    print(f"  └{'─' * 40}")


def flow_diagram() -> None:
    print(f"""

  state/haxjobs.db                 profile/arinze_profile.local.json
       │                                      │
       │ SELECT * FROM jobs WHERE id=?        │ json.load()
       │                                      │
       └────────────┬─────────────────────────┘
                    │
                    ▼
             build_prompt(title, company, location, jd_text, url)
                    │
                    │ 17K-char string
                    │
                    ▼
             chain.evaluate_one_job(job, agent_order=["codex"])
                    │
                    │ AGENT_LIST lookup  →  CodexAdapter
                    │
                    ▼
             CodexAdapter.evaluate_headless(prompt)
                    │
                    │ subprocess.run(["codex", "exec", "--output-schema", ...])
                    │   stdin=prompt
                    │   capture_output=True
                    │
                    ▼
             stdout = '{{"fit_score":76,...}}'    ← GPT-5.5
                    │
                    ▼
             extract_json(stdout)  →  dict
                    │
                    ▼
             validate_result(dict)  →  []  (no issues)
                    │
                    ▼
             result["evaluated_by"] = "codex"
                    │
                    ▼
             return {{"fit_score": 76, "fit_verdict": "STRONG_FIT", ...}}
""")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    JOB_ID = 625          # default: Sequence AI Engineer
    ADAPTER = "codex"     # default: Codex (fastest, schema-validated)
    DRY_RUN = False
    EXPLAIN = True

    i = 0
    while i < len(args):
        if args[i] == "--job" and i + 1 < len(args):
            JOB_ID = int(args[i + 1])
            i += 2
        elif args[i] == "--adapter" and i + 1 < len(args):
            ADAPTER = args[i + 1]
            i += 2
        elif args[i] == "--dry-run":
            DRY_RUN = True
            i += 1
        elif args[i] == "--quick":
            EXPLAIN = False
            i += 1
        else:
            print(f"Unknown flag: {args[i]}")
            print(__doc__)
            sys.exit(1)

    print("=" * 60)
    print("  HAXJOBS EVALUATOR WALKTHROUGH")
    print(f"  Job: #{JOB_ID}  |  Adapter: {ADAPTER}")
    if DRY_RUN:
        print("  MODE: dry-run (no LLM calls)")
    elif not EXPLAIN:
        print("  MODE: quick (no explanations)")
    print("=" * 60)

    header("STEP 1: Fetch job from DB")
    job = step1_fetch_job(JOB_ID)

    header("STEP 2: build_prompt() — profile + JD → text")
    prompt = step2_build_prompt(job)

    if DRY_RUN:
        # Show full prompt so user can inspect it
        out = Path("research/adapter-reports/pipeline-tests/walkthrough_prompt.txt")
        out.write_text(prompt)
        print(f"\n  Full prompt saved to: {out}")
        print(f"  Run without --dry-run to evaluate this job.\n")
        flow_diagram()
        sys.exit(0)

    header(f"STEP 3: Run {ADAPTER} adapter")
    result = step3_run_adapter(job, prompt, ADAPTER)

    header("STEP 4: Parse + validate output")
    step4_parse_validate(result)

    header("STEP 5: Final evaluation result")
    step5_show_result(result)

    flow_diagram()
