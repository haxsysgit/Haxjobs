"""Persist role-family classifications on jobs.

The role-family classifier chooses the stable CV variant for a job. This module
keeps that decision in SQLite so the dashboard and pipeline can
all read the same answer.
"""
from __future__ import annotations

import json
from typing import Any

from evaluation.role_family import classify_role_family
from .schema import get_db, init as init_db


DIRECT_SOURCE_PREFIXES = ("lever", "ashby", "greenhouse", "company")
THIRD_PARTY_SOURCES = ("experis", "mongoose", "reed", "cwjobs")


def classify_job_payload(title: str, jd_text: str = "", source: str = "unknown") -> dict[str, Any]:
    """Classify a job payload before it is inserted or backfilled."""
    result = classify_role_family(title, jd_text)
    return {
        "source_quality": infer_source_quality(source),
        "role_family": result["role_family"],
        "role_family_confidence": result["confidence"],
        "recommended_cv_variant": result["cv_variant"],
        "role_family_terms": json.dumps(result.get("matched_terms", [])),
    }


def infer_source_quality(source: str) -> str:
    """Classify discovery source quality for ranking/reporting.

    This is intentionally simple for now. Later LinkedIn jobs can be split into
    company-direct, easy-apply, recruiter, or unknown after URL resolution.
    """
    source_lower = (source or "unknown").lower()
    if source_lower.startswith(DIRECT_SOURCE_PREFIXES):
        return "direct"
    if source_lower.startswith("linkedin"):
        return "linkedin"
    if source_lower.startswith(THIRD_PARTY_SOURCES):
        return "third_party"
    if source_lower in {"dashboard", "manual"}:
        return "manual"
    return "unknown"


def update_job_role_classification(job_id: int, classification: dict[str, Any]) -> None:
    """Store one classification result on a job row."""
    conn = get_db()
    conn.execute(
        """
        UPDATE jobs
        SET source_quality=?, role_family=?, role_family_confidence=?,
            recommended_cv_variant=?, role_family_terms=?,
            classified_at=datetime('now'), updated_at=datetime('now')
        WHERE id=?
        """,
        (
            classification.get("source_quality", "unknown"),
            classification.get("role_family", "unknown"),
            float(classification.get("role_family_confidence", 0) or 0),
            classification.get("recommended_cv_variant", "unknown"),
            classification.get("role_family_terms", "[]"),
            job_id,
        ),
    )
    conn.commit()
    conn.close()


def classify_existing_jobs(limit: int | None = None) -> dict[str, int]:
    """Backfill role-family fields for jobs missing a stable CV family."""
    init_db()
    conn = get_db()
    query = """
        SELECT id, title, jd_text, source
        FROM jobs
        WHERE role_family IS NULL OR role_family='' OR role_family='unknown'
           OR recommended_cv_variant IS NULL OR recommended_cv_variant='' OR recommended_cv_variant='unknown'
        ORDER BY discovered_at DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()

    classified = 0
    unknown = 0
    for row in rows:
        classification = classify_job_payload(
            title=row["title"],
            jd_text=row["jd_text"],
            source=row["source"],
        )
        update_job_role_classification(row["id"], classification)
        classified += 1
        if classification["role_family"] == "unknown":
            unknown += 1

    return {"scanned": len(rows), "classified": classified, "unknown": unknown}
