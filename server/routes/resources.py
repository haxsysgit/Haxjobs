"""Packs, whitelist, profile, discovery, activity routes."""
import os
import json
import subprocess
import glob
from datetime import datetime, timezone

from haxjobs_config import (
    HAXJOBS_HOME as PIPELINE_DIR,
    PACKS_DIR,
    PROFILE_DIR,
    STATE_DIR,
    PROFILE_PATH,
)


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


# ── Packs ──

def list_packs():
    packs = []
    if not os.path.isdir(PACKS_DIR):
        return packs
    for d in sorted(glob.glob(os.path.join(PACKS_DIR, "*")), reverse=True):
        if os.path.isdir(d):
            files = [f for f in os.listdir(d) if f.endswith(".pdf")]
            packs.append({
                "dir": d,
                "name": os.path.basename(d),
                "files": files,
                "count": len(files),
            })
    return packs


def serve_pack_file(pack_dir_name, filename):
    """Serve a specific pack file for download.

    Looks only inside the named pack directory under PACKS_DIR.
    Returns the full file path or None.
    """
    target_dir = os.path.join(PACKS_DIR, pack_dir_name)
    if not os.path.isdir(target_dir):
        return None
    filepath = os.path.join(target_dir, filename)
    if os.path.isfile(filepath):
        return filepath
    return None


# ── Whitelist ──

def handle_whitelist_get():
    from db import whitelist as db_wl
    return [dict(r) for r in db_wl.get_whitelist(active_only=False)]


def handle_whitelist_post(body):
    from db import whitelist as db_wl
    pattern_type = body.get("pattern_type", "")
    pattern_value = body.get("pattern_value", "")
    if not pattern_type or not pattern_value:
        return 400, {"error": "pattern_type and pattern_value required"}
    wl_id = db_wl.add_whitelist(
        pattern_type=pattern_type,
        pattern_value=pattern_value,
        reason=body.get("reason", ""),
        source_job_id=body.get("source_job_id"),
    )
    return 200, {"ok": wl_id is not None, "id": wl_id}


def handle_whitelist_remove(body):
    from db import whitelist as db_wl
    wl_id = body.get("id")
    if not wl_id:
        return 400, {"error": "id required"}
    db_wl.remove_whitelist(int(wl_id))
    return 200, {"ok": True}


# ── Profile ──

def get_profile():
    profile = load_json(PROFILE_PATH)
    if not profile:
        return {}
    up = profile.get("user_profile", {})
    return {
        "name": up.get("name", ""),
        "headline": up.get("preferred_headline", ""),
        "email": up.get("email", ""),
        "location": up.get("location", ""),
        "visa": up.get("work_authorization_summary", ""),
        "university": up.get("university", ""),
        "experience_levels": up.get("experience_levels", []),
        "preferred_roles": up.get("preferred_roles", []),
        "preferred_locations": up.get("preferred_locations", []),
        "preferred_work_modes": up.get("preferred_work_modes", []),
        "salary_preference": up.get("salary_preference", ""),
        "skills": up.get("skills", []),
        "fact_count": len(profile.get("confirmed_profile_facts", [])),
        "platform_count": len(profile.get("platform_accounts", [])),
        "saved_answer_count": len(profile.get("saved_answers", [])),
    }


def save_profile(body):
    name = body.get("name", "")
    headline = body.get("headline", "")
    if not name:
        return 400, {"error": "name required"}
    try:
        p = load_json(PROFILE_PATH)
        if p:
            p["user_profile"]["name"] = name
            p["user_profile"]["preferred_headline"] = headline
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            with open(PROFILE_PATH, "w") as f:
                json.dump(p, f, indent=2)
            return 200, {"ok": True, "name": name, "headline": headline}
        else:
            return 500, {"error": "Profile file not found"}
    except Exception as e:
        return 500, {"error": str(e)}


# ── Discovery ──

def get_discovery():
    """ponytail: discovery scrapers deleted, return DB stats."""
    from db.stats import get_stats
    s = get_stats()
    return {
        "total_jobs": s["total_jobs"],
        "pending": s["pending"],
        "evaluated": s["evaluated"],
        "skipped": s["skipped"],
        "last_pipeline_run": _get_last_log_time(),
    }


def _get_last_log_time():
    log = os.path.join(STATE_DIR, "pipeline.log")
    if os.path.exists(log):
        return datetime.fromtimestamp(os.path.getmtime(log), tz=timezone.utc).isoformat()
    return None


# ── Activity ──

def get_activity():
    from db import activity as db_act
    activity = db_act.get_recent_activity(30)
    return [{
        "time": a.get("created_at", ""),
        "type": a.get("event_type", ""),
        "message": a.get("message", ""),
    } for a in activity]


# ── Pipeline trigger ──

def trigger_pipeline():
    script = os.path.join(PIPELINE_DIR, "evaluate", "run.py")
    try:
        result = subprocess.run(
            ["python3", script, "--batch", "1"],
            capture_output=True, text=True, timeout=300,
            cwd=PIPELINE_DIR
        )
        return 200, {"ok": True, "message": "Pipeline triggered", "output": result.stdout[-200:]}
    except Exception as e:
        return 500, {"ok": False, "message": str(e)}
