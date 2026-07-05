"""Product tool service layer — shared by agent tools and FastAPI routes.

All functions return {"ok": True, ...} or {"ok": False, "code": "...", "error": "..."}.
The agent tool handlers in tools_product.py wrap these with json.dumps().
FastAPI feature services call these directly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from haxjobs.config import AUTO_PACK_LEVELS, EVALUATION_AGENT, PACKS_DIR, PROFILE_PATH


# ── helpers ──────────────────────────────────────────────────────────────────


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "error": message}


def _job_or_error(job_id: int) -> tuple[dict | None, dict | None]:
    from haxjobs.db.jobs import get_job
    job = get_job(job_id)
    if not job:
        return None, _error("job_not_found", f"Job {job_id} not found")
    return job, None


def _normalize_decision(decision: str) -> str | None:
    mapping = {"apply": "apply", "maybe": "maybe", "save": "save", "skip": "skip", "reject": "reject"}
    return mapping.get(str(decision).lower().strip())


STATUS_MAP: dict[str, str] = {
    "apply": "applied",
    "maybe": "maybe",
    "save": "saved",
    "skip": "skipped",
    "reject": "rejected",
}


def _slugify(text: str) -> str:
    """Safe directory slug from arbitrary text."""
    slug = re.sub(r"[^a-zA-Z0-9._-]", "_", text).strip("_").lower()
    return slug[:64] or "unknown"


# ── evaluate_fit ─────────────────────────────────────────────────────────────


def evaluate_fit(job_id: int, auto_generate_pack: bool = True) -> dict[str, Any]:
    """Score a job against the profile, save evaluation, optionally generate pack."""
    from haxjobs.agent import Agent
    from haxjobs.db.evaluations import save_evaluation
    from haxjobs.evaluate.common import build_prompt, extract_json

    job, err = _job_or_error(job_id)
    if err:
        return err

    prompt = build_prompt(
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", ""),
        jd_text=job.get("jd_text", ""),
        source_url=job.get("source_url", ""),
    )

    try:
        response = Agent().run(prompt, temperature=0.2)
    except Exception as exc:
        return _error("agent_error", f"Agent call failed: {exc}")

    parsed = extract_json(response)
    if parsed is None:
        return _error("invalid_agent_json", "Agent returned no parseable JSON")

    # Validate minimally — extract_json already did the heavy lifting
    if "fit_score" not in parsed:
        return _error("invalid_agent_json", "Agent JSON missing fit_score")

    parsed.setdefault("agent", EVALUATION_AGENT)
    save_evaluation(job_id, parsed)

    pack_result = None
    level = parsed.get("level", 4)
    if auto_generate_pack and level in AUTO_PACK_LEVELS:
        pack_result = generate_pack(job_id)

    return {
        "ok": True,
        "job_id": job_id,
        "fit_score": parsed["fit_score"],
        "level": parsed.get("level", 4),
        "level_name": parsed.get("level_name", ""),
        "fit_verdict": parsed.get("fit_verdict", ""),
        "strongest_matches": parsed.get("strongest_matches", []),
        "major_gaps": parsed.get("major_gaps", []),
        "sponsorship_risk": parsed.get("sponsorship_risk", ""),
        "summary": parsed.get("summary", ""),
        "pack": pack_result,
    }


# ── record_decision ──────────────────────────────────────────────────────────


def record_decision(job_id: int, decision: str, reason: str = "") -> dict[str, Any]:
    """Record a user decision. Normalizes Apply→apply, Maybe→maybe, etc."""
    from haxjobs.db.jobs import update_job_status

    canonical = _normalize_decision(decision)
    if not canonical:
        return _error(
            "invalid_decision",
            f"Unknown decision '{decision}'. Must be apply, maybe, save, skip, or reject.",
        )

    _, err = _job_or_error(job_id)
    if err:
        return err

    from haxjobs.db.decisions import record_decision as _db_record

    try:
        decision_id = _db_record(job_id, canonical, reason)
    except Exception as exc:
        return _error("db_error", f"Failed to record decision: {exc}")

    if decision_id is None:
        return _error("db_error", "Failed to record decision — no id returned")

    update_job_status(job_id, STATUS_MAP[canonical])

    return {"ok": True, "job_id": job_id, "decision": canonical, "decision_id": decision_id}


# ── generate_pack ────────────────────────────────────────────────────────────


def _cv_metadata_for_job(job: dict) -> dict[str, Any]:
    """Build CV variant metadata for a job, falling back gracefully."""
    from haxjobs.cv_variants.registry import build_pack_cv_metadata, load_cv_variant_registry

    recommended = job.get("recommended_cv_variant") or "backend_python"

    # Try the canonical registry path
    registry_path = Path(__file__).resolve().parent / "cv_variants" / "registry.json"
    if registry_path.exists():
        registry = load_cv_variant_registry(str(registry_path))
        return build_pack_cv_metadata(recommended, registry)

    # Fallback: minimal metadata that preserves pack_owns_cv=False
    return {
        "recommended_cv_variant": recommended,
        "role_family": "unknown",
        "cv_variant_dir": recommended,
        "cv_pdf": f"{recommended}/cv.pdf",
        "cv_html": f"{recommended}/cv.html",
        "pack_owns_cv": False,
    }


def generate_pack(job_id: int, force: bool = False) -> dict[str, Any]:
    """Generate an application pack for a job. L1/L2 by default, L3/L4 with force."""
    from haxjobs.db.evaluations import get_evaluation
    from haxjobs.db.jobs import update_job_pack_status
    from haxjobs.packs_builder.job_pack import build_job_pack

    job, err = _job_or_error(job_id)
    if err:
        return err

    evaluation = get_evaluation(job_id)
    if not evaluation:
        return _error("evaluation_required", "Evaluate job before generating pack")

    level = evaluation.get("level", 4)
    if level >= 3 and not force:
        return _error(
            "manual_review_required",
            f"Level {level} requires manual review. Use force=True to override.",
        )

    profile = {}
    if Path(PROFILE_PATH).exists():
        profile = json.loads(Path(PROFILE_PATH).read_text(encoding="utf-8"))

    cv_meta = _cv_metadata_for_job(job)

    company_slug = _slugify(job.get("company", "unknown"))
    variant_slug = _slugify(cv_meta.get("recommended_cv_variant", "unknown"))
    pack_dir_name = f"{company_slug}_{variant_slug}"
    output_dir = Path(PACKS_DIR) / pack_dir_name

    try:
        pack = build_job_pack(job, evaluation, profile, cv_meta, output_root=str(output_dir))
    except Exception as exc:
        return _error("pack_error", f"Pack generation failed: {exc}")

    update_job_pack_status(job_id, "generated", pack_dir=str(output_dir))

    return {
        "ok": True,
        "job_id": job_id,
        "pack_dir": str(output_dir),
        "files": pack.get("files", []),
        "metadata": pack.get("metadata", {}),
    }


# ── discover_jobs ────────────────────────────────────────────────────────────


def _is_likely_match(job: dict) -> bool:
    """Quick heuristic for whether a promoted job is worth auto-evaluating."""
    role_family = job.get("role_family") or "unknown"
    status = job.get("status") or "pending"
    return role_family != "unknown" and status in {"pending", "evaluated"}


def discover_jobs(
    roles: list[str] | None = None,
    locations: list[str] | None = None,
    sources: list[str] | None = None,
    auto_evaluate: bool = True,
) -> dict[str, Any]:
    """Run ATS scrapers, promote new jobs, optionally auto-evaluate likely matches.

    Args:
        roles: Filter by preferred roles (not enforced in v1).
        locations: Filter by preferred locations (not enforced in v1).
        sources: Scraper names to run (default: all — greenhouse, ashby, lever).
        auto_evaluate: Auto-evaluate likely matches after promotion.
    """
    from haxjobs.db.discovered_jobs import promote_discovered_job
    from haxjobs.db.schema import get_db

    all_sources = ["greenhouse", "ashby", "lever"]
    selected = sources or all_sources
    invalid = [s for s in selected if s not in all_sources]
    if invalid:
        return _error("invalid_source", f"Unknown sources: {invalid}. Valid: {all_sources}")

    scraper_map = {}
    try:
        from haxjobs.discovery.scrapers.ashby import scrape_ashby
        from haxjobs.discovery.scrapers.lever import scrape_lever
        from haxjobs.discovery.scrapers.orchestrator import scrape_greenhouse
        scraper_map = {
            "greenhouse": scrape_greenhouse,
            "ashby": scrape_ashby,
            "lever": scrape_lever,
        }
    except ImportError as exc:
        return _error("scraper_error", f"Could not import scrapers: {exc}")

    found_total = 0
    new_total = 0
    promoted_total = 0
    evaluated = 0
    packed = 0
    errors: list[str] = []
    promoted_jobs: list[dict] = []

    for name in selected:
        runner = scraper_map.get(name)
        if not runner:
            continue
        try:
            result = runner()
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue

        scraper_results = result.get("results", result) if isinstance(result, dict) else {}
        if isinstance(scraper_results, list):
            scraper_results = {"jobs": scraper_results}

        found = scraper_results.get("found", 0)
        new_count = scraper_results.get("new", 0)
        found_total += found
        new_total += new_count
        errors.extend(scraper_results.get("errors", []))

    # Promote accepted discovered jobs
    conn = get_db()
    try:
        new_rows = conn.execute(
            "SELECT id FROM discovered_jobs WHERE discovery_status='new' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    for row in new_rows:
        discovered_id = row["id"]
        try:
            job_id = promote_discovered_job(discovered_id)
        except Exception as exc:
            errors.append(f"promote id={discovered_id}: {exc}")
            continue
        if job_id:
            promoted_total += 1
            from haxjobs.db.jobs import get_job
            job = get_job(job_id)
            if job:
                promoted_jobs.append(job)

    # Auto-evaluate likely matches
    for job in promoted_jobs:
        if not auto_evaluate:
            break
        if not _is_likely_match(job):
            continue
        try:
            eval_result = evaluate_fit(job["id"], auto_generate_pack=True)
            if eval_result.get("ok"):
                evaluated += 1
                if eval_result.get("pack", {}).get("ok"):
                    packed += 1
            else:
                errors.append(f"evaluate job {job['id']}: {eval_result.get('error')}")
        except Exception as exc:
            errors.append(f"evaluate job {job['id']}: {exc}")

    job_list = [
        {
            "id": j["id"],
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "url": j.get("source_url", ""),
            "location": j.get("location", ""),
            "source": j.get("source", ""),
        }
        for j in promoted_jobs[:50]  # ponytail: cap at 50 to keep output manageable
    ]

    return {
        "ok": True,
        "found": found_total,
        "new": new_total,
        "promoted": promoted_total,
        "evaluated": evaluated,
        "packed": packed,
        "errors": errors[:20],  # ponytail: cap errors
        "jobs": job_list,
    }
