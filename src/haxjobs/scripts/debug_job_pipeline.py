#!/usr/bin/env python3
"""Inspect one HaxJobs job through every pipeline stage.

Usage:
    python3 scripts/debug_job_pipeline.py 126

This is a practical debugging tool, not a test fixture. It reads the real
local SQLite database and pack directory configured for this checkout.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from haxjobs.config import DB_PATH, PACKS_DIR

API_BASE_URL = "http://127.0.0.1:8800"


def print_stage(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row | None) -> dict:
    if row is None:
        return {}
    return dict(row)


def print_json(data: dict | list) -> None:
    print(json.dumps(data, indent=2, default=str))


def fetch_api_json(path: str) -> dict | list:
    url = f"{API_BASE_URL}{path}"
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def inspect_servers() -> None:
    print_stage("Stage 0 — Servers")
    try:
        status = fetch_api_json("/api/status")
    except Exception as error:
        print_json({"api_ok": False, "error": str(error)})
        return

    print_json(
        {
            "api_ok": True,
            "api_url": API_BASE_URL,
            "dashboard_dev_url": "http://127.0.0.1:5173",
            "status": status,
        }
    )


def inspect_job_row(connection: sqlite3.Connection, job_id: int) -> dict:
    print_stage("Stage 1/2 — Intake + SQLite job row")
    row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    job = row_to_dict(row)

    if not job:
        print_json({"found": False, "job_id": job_id})
        return {}

    print_json(
        {
            "found": True,
            "id": job.get("id"),
            "company": job.get("company"),
            "title": job.get("title"),
            "location": job.get("location"),
            "status": job.get("status"),
            "source": job.get("source"),
            "source_url": job.get("source_url"),
            "discovered_at": job.get("discovered_at"),
            "updated_at": job.get("updated_at"),
        }
    )
    return job


def inspect_role_routing(job: dict) -> None:
    print_stage("Stage 3 — Role-family routing")
    print_json(
        {
            "role_family": job.get("role_family"),
            "role_family_confidence": job.get("role_family_confidence"),
            "recommended_cv_variant": job.get("recommended_cv_variant"),
            "role_family_terms": job.get("role_family_terms"),
        }
    )


def inspect_evaluation(connection: sqlite3.Connection, job_id: int) -> None:
    print_stage("Stage 4/5 — Fit evaluation + persistence")
    row = connection.execute(
        """
        SELECT *
        FROM evaluations
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()
    evaluation = row_to_dict(row)

    if not evaluation:
        print_json({"evaluated": False, "job_id": job_id})
        return

    print_json(
        {
            "evaluated": True,
            "fit_score": evaluation.get("fit_score"),
            "fit_verdict": evaluation.get("fit_verdict"),
            "level": evaluation.get("level"),
            "level_name": evaluation.get("level_name"),
            "decision": evaluation.get("decision"),
            "skip_reason": evaluation.get("skip_reason"),
            "evaluated_by": evaluation.get("evaluated_by"),
            "evaluated_at": evaluation.get("evaluated_at"),
            "summary": evaluation.get("summary"),
        }
    )


def inspect_decisions(connection: sqlite3.Connection, job_id: int) -> None:
    print_stage("Stage 6 — Manual decision / approval history")
    rows = connection.execute(
        """
        SELECT decision, reason, decided_at
        FROM decisions
        WHERE job_id = ?
        ORDER BY id DESC
        """,
        (job_id,),
    ).fetchall()
    decisions = [dict(row) for row in rows]
    print_json({"decision_count": len(decisions), "decisions": decisions})


def inspect_pack(job: dict) -> None:
    print_stage("Stage 7/8 — Pack generation + pack inspection")
    pack_dir = job.get("pack_dir") or ""

    if not pack_dir:
        print_json({"pack_generated": False, "reason": "job.pack_dir is empty"})
        return

    pack_path = Path(pack_dir)
    files = []
    if pack_path.exists():
        files = sorted(path.name for path in pack_path.iterdir() if path.is_file())

    metadata_path = pack_path / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())

    print_json(
        {
            "pack_generated": pack_path.exists(),
            "pack_dir": str(pack_path),
            "configured_packs_dir": PACKS_DIR,
            "files": files,
            "metadata": {
                "job_id": metadata.get("job_id"),
                "company": metadata.get("company"),
                "fit_score": metadata.get("fit_score"),
                "recommended_cv_variant": metadata.get("recommended_cv_variant"),
                "role_family": metadata.get("role_family"),
                "pack_owns_cv": metadata.get("pack_owns_cv"),
            },
        }
    )

    try:
        pack_detail = fetch_api_json(f"/api/pack-detail?dir={quote(str(pack_path))}")
    except Exception as error:
        print_json({"pack_detail_api_ok": False, "error": str(error)})
        return

    if not isinstance(pack_detail, dict):
        print_json({"pack_detail_api_ok": False, "error": "pack detail API returned a non-object response"})
        return

    print("\nPack detail API:")
    print_json(
        {
            "ok": pack_detail.get("ok"),
            "packDir": pack_detail.get("packDir"),
            "files": sorted((pack_detail.get("files") or {}).keys()),
        }
    )


def inspect_api_job(job_id: int) -> None:
    print_stage("Stage 9 — Dashboard/API view")
    try:
        jobs = fetch_api_json(f"/api/jobs?limit=200&offset=0")
    except Exception as error:
        print_json({"api_jobs_ok": False, "error": str(error)})
        return

    target_job = None
    for job in jobs:
        if str(job.get("id")) == str(job_id):
            target_job = job
            break

    if not target_job:
        print_json({"api_jobs_ok": True, "found_in_api_page": False, "job_id": job_id})
        return

    print_json(
        {
            "api_jobs_ok": True,
            "found_in_api_page": True,
            "id": target_job.get("id"),
            "status": target_job.get("status"),
            "fitScore": target_job.get("fitScore"),
            "roleFamily": target_job.get("roleFamily"),
            "recommendedCvVariant": target_job.get("recommendedCvVariant"),
            "packStatus": target_job.get("packStatus"),
            "packDir": target_job.get("packDir"),
        }
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/debug_job_pipeline.py JOB_ID")
        return 1

    job_id = int(sys.argv[1])

    print(f"Inspecting HaxJobs pipeline for job_id={job_id}")
    print(f"DB_PATH={DB_PATH}")

    inspect_servers()

    connection = connect_db()
    try:
        job = inspect_job_row(connection, job_id)
        if not job:
            return 1

        inspect_role_routing(job)
        inspect_evaluation(connection, job_id)
        inspect_decisions(connection, job_id)
        inspect_pack(job)
        inspect_api_job(job_id)
    finally:
        connection.close()

    print_stage("Done")
    print("Use this output to debug exactly where a job is stuck.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
