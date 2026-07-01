"""Evaluation orchestrator — agent selection, job evaluation, and CLI.

Reads agent chain from ``haxjobs.toml`` ``[evaluation].agent`` + ``fallback_agents``,
falls back to auto-discovery if config is empty.

Usage:
  python3 -m evaluate.run --next           # Process next pending job
  python3 -m evaluate.run --batch 1        # Process 1 pending job
  python3 -m evaluate.run --all-pending    # Process all (one at a time)
"""
from __future__ import annotations

import sys
from pathlib import Path

from haxjobs.config import EVALUATION_AGENT, AUTO_PACK_LEVELS
from haxjobs.evaluate.chain import evaluate_one_job as chain_evaluate_one_job, _resolve_order


def evaluate_one_job(job_data: dict, agent_name: str | None = None) -> dict | None:
    """Evaluate a single job via the configured agent chain."""
    title = job_data.get("title", "Unknown")
    company = job_data.get("company", "Unknown")
    print(f"  Evaluating: {company} — {title[:60]}")
    agent_order = [agent_name] if agent_name else None
    return chain_evaluate_one_job(job_data, agent_order=agent_order)


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
        from haxjobs.config import PROFILE_PATH
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
        "cv_pdf": f"src/haxjobs/cv_variants/{variant}/cv.pdf",
        "cv_html": f"src/haxjobs/cv_variants/{variant}/cv.html",
    }

    # CV review: generate a per-job improved CV before building the pack
    reviewed_cv_path = None
    try:
        from haxjobs.evaluate.cv_review import review_cv_for_job
        jd_text = job.get("jd_text", "")
        if jd_text and len(jd_text) > 100:
            reviewed_cv = review_cv_for_job(variant, jd_text)
            pack_dir = Path("packs") / job.get("company", "unknown").replace(" ", "_").lower() / variant
            pack_dir.mkdir(parents=True, exist_ok=True)
            reviewed_cv_path = pack_dir / "cv_reviewed.md"
            reviewed_cv_path.write_text(reviewed_cv)
            cv_metadata["reviewed_cv"] = str(reviewed_cv_path)
            print(f"  → CV reviewed for {variant} ({len(reviewed_cv)} chars)")
    except Exception as e:
        print(f"  → CV review skipped: {e}")

    from haxjobs.packs_builder.job_pack import build_job_pack
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
    from haxjobs.db.evaluations import save_evaluation
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
