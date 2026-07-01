"""Generate per-job markdown packs for evaluated jobs that are ready.

This script is intentionally separate from the evaluator. Evaluation scores jobs;
this module turns already-scored jobs into prep packs when the score is high
enough and the job has a reusable CV variant.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from haxjobs.cv_variants.registry import build_pack_cv_metadata, load_cv_variant_registry
from haxjobs.db.evaluations import get_jobs_with_evaluations
from haxjobs.db.jobs import update_job_pack_status
from haxjobs.db.schema import init as init_db
from haxjobs.packs_builder.job_pack import build_job_pack

ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY_PATH = ROOT / "src" / "haxjobs" / "cv_variants" / "registry.json"
from haxjobs.config import AUTO_PACK_LEVELS, PROFILE_PATH as DEFAULT_PROFILE_PATH
DEFAULT_OUTPUT_ROOT = ROOT / "packs"
DEFAULT_THRESHOLD = 50


def generate_ready_packs(
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
    threshold: int = DEFAULT_THRESHOLD,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build packs for evaluated jobs that do not already have a pack."""
    init_db()
    registry = load_cv_variant_registry(registry_path)
    profile = _load_profile(profile_path)

    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for job in get_jobs_with_evaluations():
        decision = _should_generate(job, threshold)
        if decision:
            skipped.append({"job_id": job.get("id"), "reason": decision})
            continue

        cv_metadata = build_pack_cv_metadata(job.get("recommended_cv_variant"), registry)
        result = build_job_pack(
            job=job,
            evaluation=job,
            profile=profile,
            cv_variant=cv_metadata,
            output_root=output_root,
        )
        update_job_pack_status(job["id"], "generated", pack_dir=result["pack_dir"])
        generated.append(result)

        if limit is not None and len(generated) >= limit:
            break

    return {
        "generated_count": len(generated),
        "skipped_count": len(skipped),
        "generated": generated,
        "skipped": skipped,
    }


def generate_pack_for_job(
    job_id: int,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    profile_path: str | Path | None = None,
    threshold: int = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """Build one pack for one explicitly requested job.

    This is the manual gate used by API/dashboard/CLI. It intentionally does
    not walk the whole ready queue.
    """
    if profile_path is None:
        from haxjobs.config import PROFILE_PATH  # resolve at call time
        profile_path = PROFILE_PATH
    init_db()
    registry = load_cv_variant_registry(registry_path)
    profile = _load_profile(profile_path)

    matching_job = None
    for job in get_jobs_with_evaluations():
        if int(job.get("id")) == int(job_id):
            matching_job = job
            break

    if matching_job is None:
        return {"ok": False, "error": "job not found", "job_id": job_id}

    decision = _should_generate(matching_job, threshold)
    if decision:
        return {
            "ok": False,
            "error": decision,
            "job_id": job_id,
            "generated_count": 0,
        }

    cv_metadata = build_pack_cv_metadata(
        matching_job.get("recommended_cv_variant"), registry
    )
    result = build_job_pack(
        job=matching_job,
        evaluation=matching_job,
        profile=profile,
        cv_variant=cv_metadata,
        output_root=output_root,
    )
    update_job_pack_status(matching_job["id"], "generated", pack_dir=result["pack_dir"])
    return {
        "ok": True,
        "job_id": matching_job["id"],
        "generated_count": 1,
        "pack_dir": result["pack_dir"],
        "metadata": result["metadata"],
    }



def _should_generate(job: dict[str, Any], threshold: int) -> str | None:
    """Return a skip reason, or None when a pack can be generated.

    Checks config-driven AUTO_PACK_LEVELS and falls back to threshold.
    """
    if job.get("pack_status") not in (None, "", "none"):
        return "pack already exists or is in progress"

    fit_score = job.get("fit_score")
    if fit_score is None:
        return "job has no evaluation score"

    level = job.get("level")
    if level is not None and level not in AUTO_PACK_LEVELS:
        return f"level {level} not in auto-pack levels {AUTO_PACK_LEVELS}"

    if fit_score < threshold:
        return f"fit score below {threshold}"

    variant = job.get("recommended_cv_variant")
    if not variant or variant == "unknown":
        return "missing recommended CV variant"

    return None


def _load_profile(profile_path: str | Path) -> dict[str, Any]:
    path = Path(profile_path)
    raw = json.loads(path.read_text())
    user_profile = raw.get("user_profile", raw)
    return {
        "name": user_profile.get("name", "Arinze Elenasulu"),
        "email": user_profile.get("email", "elenasuluarinze@gmail.com"),
        "linkedin": user_profile.get("linkedin_url") or user_profile.get("linkedin", ""),
        "headline": user_profile.get("preferred_headline") or user_profile.get("headline", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ready HaxJobs markdown packs")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE_PATH))
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    result = generate_ready_packs(
        output_root=args.output_root,
        registry_path=args.registry,
        profile_path=args.profile,
        threshold=args.threshold,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
