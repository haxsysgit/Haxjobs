"""Evaluation orchestrator — agent selection, job evaluation, and CLI.

Selects the configured agent from ``haxjobs.toml`` ``[evaluation].agent``
and runs evaluation via the appropriate adapter.

Usage:
  python3 -m evaluate.run --next           # Process next pending job
  python3 -m evaluate.run --batch 1        # Process 1 pending job
  python3 -m evaluate.run --all-pending    # Process all (one at a time)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from haxjobs_config import EVALUATION_AGENT, AUTO_PACK_LEVELS

from .common import build_prompt, extract_json, validate_result


def select_agent(agent_name: str | None = None) -> Callable[..., str | None]:
    """Return a ``call_agent(prompt, *, timeout_seconds) -> str`` function.

    Args:
        agent_name: Agent identifier from config. Defaults to ``EVALUATION_AGENT``.

    Returns:
        A callable matching the agent adapter interface.

    Raises:
        ValueError: If the agent name is unknown.
    """
    name = (agent_name or EVALUATION_AGENT).strip().lower()

    if name == "hermes":
        from evaluate.agents.hermes import call_agent
        return call_agent

    raise ValueError(
        f"Unknown evaluation agent: {name!r}. "
        f"Set [evaluation].agent in haxjobs.toml to a supported agent."
    )


def evaluate_one_job(job_data: dict, agent_name: str | None = None) -> dict | None:
    """Evaluate a single job dict. Returns the parsed result or None on failure."""
    call_agent = select_agent(agent_name)

    title = job_data.get("title", "Unknown")
    company = job_data.get("company", "Unknown")
    location = job_data.get("location", "")
    jd_text = job_data.get("jd_text", "")
    source_url = job_data.get("source_url", "")

    print(f"  Evaluating: {company} — {title[:60]}")

    prompt = build_prompt(title, company, location, jd_text, source_url)
    raw_output = call_agent(prompt, timeout_seconds=180)

    if not raw_output:
        print(f"  FAILED: Agent returned no output")
        return None

    parsed = extract_json(raw_output)
    if not parsed:
        print(f"  FAILED: Could not extract JSON from agent output")
        return None

    issues = validate_result(parsed)
    if issues:
        # Try a fixup prompt
        fix_prompt = f"Your previous JSON had issues: {', '.join(issues)}. Return ONLY valid JSON with all fields."
        retry_prompt = prompt + "\n\n" + fix_prompt
        retry_output = call_agent(retry_prompt, timeout_seconds=180)
        if retry_output:
            retry_parsed = extract_json(retry_output)
            if retry_parsed and not validate_result(retry_parsed):
                parsed = retry_parsed
            else:
                print(f"  FAILED: Validation issues after retry: {issues}")
                return None
        else:
            print(f"  FAILED: Validation issues: {issues}")
            return None

    return parsed


def evaluate_from_db(agent_name: str | None = None) -> bool:
    """Get next pending job from DB, evaluate it, save result.

    L1/L2 jobs automatically get packs generated (per AUTO_PACK_LEVELS config).
    L3/L4 jobs are saved without packs.

    Returns True if a job was evaluated, False if none pending.
    """
    import pipeline_db as db
    db.init()
    pending = db.get_pending_jobs(1)
    if not pending:
        print("No pending jobs in DB.")
        return False

    job = pending[0]
    job_id = job["id"]
    print(f"Evaluating job DB#{job_id}: {job['company']} — {job['title'][:60]}")

    result = evaluate_one_job(job, agent_name=agent_name)
    if not result:
        return False

    # Save to DB
    result["agent"] = agent_name or EVALUATION_AGENT
    db.save_evaluation(job_id, result)
    print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")

    # Auto-pack L1/L2
    if result["level"] in AUTO_PACK_LEVELS:
        _auto_pack(job, result)
    else:
        print(f"  → Level {result['level']} — no auto-pack (manual review)")

    return True


def _auto_pack(job: dict, result: dict) -> None:
    """Auto-generate a pack for a job and save the path to the evaluation."""
    import json

    variant = job.get("recommended_cv_variant") or job.get("role_family") or "backend_python"

    profile_path = None
    try:
        from haxjobs_config import PROFILE_PATH
        profile_path = PROFILE_PATH
    except Exception:
        pass

    profile = {
        "name": "Arinze Elenasulu",
        "email": "elenasuluarinze@gmail.com",
        "linkedin": "https://www.linkedin.com/in/arinze-elenasulu/",
    }
    if profile_path:
        try:
            raw = json.loads(Path(profile_path).read_text())
            up = raw.get("user_profile", raw)
            profile = {
                "name": up.get("name", profile["name"]),
                "email": up.get("email", profile["email"]),
                "linkedin": up.get("linkedin_url") or up.get("linkedin", profile["linkedin"]),
            }
        except Exception:
            pass

    cv_metadata = {
        "pack_owns_cv": False,
        "recommended_cv_variant": variant,
        "role_family": variant,
        "cv_pdf": f"cv_variants/{variant}/cv.pdf",
        "cv_html": f"cv_variants/{variant}/cv.html",
    }

    from packs_builder.job_pack import build_job_pack
    pack_result = build_job_pack(
        job=job,
        evaluation=result,
        profile=profile,
        cv_variant=cv_metadata,
        output_root="packs",
    )

    print(f"  → Pack generated: {pack_result['pack_dir']}")

    # Save pack path back to evaluation and job
    import pipeline_db as db
    db.init()
    from db.evaluations import save_evaluation
    result["pack_dir"] = pack_result["pack_dir"]
    result["pack_template_id"] = variant
    save_evaluation(job["id"], result)
    db.update_job_pack_status(job["id"], "generated", pack_dir=pack_result["pack_dir"])


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the pluggable evaluation system."""
    if argv is None:
        argv = sys.argv

    import pipeline_db as db
    db.init()

    if len(argv) < 2:
        print("Usage:")
        print("  evaluate/run.py --next           # Next pending job from DB")
        print("  evaluate/run.py --batch 1        # Process N pending")
        print("  evaluate/run.py --all-pending    # Process all (one at a time)")
        return 1

    arg = argv[1]

    if arg == "--next":
        ok = evaluate_from_db()
        return 0 if ok else 1

    elif arg == "--batch":
        limit = int(argv[2]) if len(argv) > 2 else 1
        db.init()
        pending = db.get_pending_jobs(limit)
        if pending:
            for job in pending:
                result = evaluate_one_job(job)
                if result:
                    result["agent"] = EVALUATION_AGENT
                    db.save_evaluation(job["id"], result)
                    print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")
                    if result["level"] in AUTO_PACK_LEVELS:
                        _auto_pack(job, result)
                else:
                    print(f"  FAILED for job #{job['id']}")
        else:
            print("No pending jobs.")
            return 0

    elif arg == "--all-pending":
        total = 0
        while True:
            db.init()
            pending = db.get_pending_jobs(1)
            if not pending:
                break
            result = evaluate_one_job(pending[0])
            if result:
                result["agent"] = EVALUATION_AGENT
                db.save_evaluation(pending[0]["id"], result)
                print(f"  → {result['fit_verdict']} (score={result['fit_score']})")
                if result["level"] in AUTO_PACK_LEVELS:
                    _auto_pack(pending[0], result)
                total += 1
            else:
                print("  FAILED — stopping")
                break
        print(f"\nDone. {total} jobs evaluated.")

    else:
        print(f"Unknown argument: {arg}")
        print("Usage: evaluate/run.py --next | --batch N | --all-pending")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
