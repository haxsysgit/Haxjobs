"""Seed database from intake JSON files."""
import json
import os
import glob
from .schema import init as _init, get_db
from .jobs import insert_job
from .evaluations import save_evaluation
from .activity import _log


def seed_from_intake():
    from haxjobs_config import INTAKE_DIR
    if not os.path.isdir(INTAKE_DIR):
        return 0

    seeded = 0
    for fpath in glob.glob(f"{INTAKE_DIR}/*.json"):
        try:
            d = json.load(open(fpath))
            fname = os.path.basename(fpath)
            job_id = insert_job(
                title=d.get("title", "Unknown"),
                company=d.get("company", "Unknown"),
                location=d.get("location", ""),
                jd_text=d.get("jd_text", ""),
                source_url=d.get("source_url", ""),
                source=d.get("source", "unknown"),
                external_id=fname,
            )
            if job_id:
                seeded += 1
                fr = d.get("fit_report")
                if fr and fr.get("fit_score"):
                    save_evaluation(job_id, {
                        "fit_score": fr["fit_score"],
                        "fit_verdict": fr.get("fit_verdict", "SKIP"),
                        "level": d.get("level", 4),
                        "level_name": d.get("level_name", "Skip"),
                        "strongest_matches": fr.get("strongest_matches", []),
                        "major_gaps": fr.get("major_gaps", []),
                        "sponsorship_risk": fr.get("sponsorship_risk", "medium"),
                        "summary": fr.get("summary", ""),
                        "decision": d.get("status", "skipped"),
                        "skip_reason": d.get("skip_reason", ""),
                        "evaluated_by": d.get("evaluated_by", "local"),
                    })
        except Exception:
            pass

    _log("system", f"Seeded {seeded} jobs from intake JSON files")
    return seeded
