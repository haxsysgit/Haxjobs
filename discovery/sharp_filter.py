#!/usr/bin/env python3
"""Loose pre-filter for HaxJobs discovery scrapers.
Only blocks OBVIOUS non-matches (HR, Finance, Legal, Sales, Senior+).
Everything else passes through to Hermes for actual fit evaluation.
"""
import json, os, re
from datetime import datetime, timezone, timedelta

INTAKE_DIR = "/home/hermes/haxjobs/intake"
DEDUP_WINDOW_DAYS = 7

# === ONLY BLOCK THESE — everything else passes ===

# Clearly non-engineering roles (word-boundary, case-insensitive)
NON_ENGINEERING = [
    r"\bfinancial?\s*(crime|analyst|advis)", r"\bcompliance\b", r"\blegal\b",
    r"\bcounsel\b", r"\battorney\b", r"\bmarketing\b", r"\bsales\b",
    r"\brecruit(er|ment)\b", r"\bhr\b", r"\bhuman resources\b",
    r"\bexecutive assistant\b", r"\b(ea|pa)\b.*\b(manager|director)\b",
    r"\baccount\s*(executive|manager)\b", r"\bcustomer success\b",
    r"\btechnical (writer|author)\b", r"\boffice manager\b",
    r"\boperations (analyst|specialist)\b", r"\bfincrime\b",
    r"\banti.money.laundering\b", r"\bprocurement\b",
    r"\b(registered|staff|charge)\s+nurse\b", r"\bphysician\b",
    r"\bchef\b", r"\bwaiter\b", r"\bdriver\b", r"\bsecurity guard\b",
]

# Senior+ roles Arinze explicitly excludes
# Split into: NEVER allowed, and SOMETIMES allowed (if in MANAGER_OK)
EXCLUDED_LEVELS_NEVER = [
    r"\bsenior\b", r"\bprincipal\b", r"\bstaff\b",
    r"\bhead of\b", r"\bdirector\b", r"\bvp\b", r"\bvice president\b",
    r"\barchitect\b",
]
EXCLUDED_LEVELS_SOMETIMES = [
    r"\bmanager\b", r"\blead\b",
]

# Manager/lead titles that are actually engineering roles (allowed)
MANAGER_OK = [
    r"engineering manager", r"tech(nical)? lead", r"team lead",
]

def is_manager_ok(title):
    """Some 'manager'/'lead' titles are actually engineering roles."""
    for pattern in MANAGER_OK:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False

def check(title, location="", description=""):
    """Returns (passes, skip_reason). True = pass to evaluation, False = skip."""
    combined = f"{title} {location} {description[:300]}"

    # Check absolute non-engineering roles
    for pattern in NON_ENGINEERING:
        if re.search(pattern, combined, re.IGNORECASE):
            return False, f"non_engineering: {pattern}"

    # Never-allowed levels (senior, principal, staff, director, VP, architect)
    # — these are always blocked regardless of MANAGER_OK
    for pattern in EXCLUDED_LEVELS_NEVER:
        if re.search(pattern, title, re.IGNORECASE):
            # Exception: "senior" is allowed in the context of "Senior Software Engineer"
            # if the role is explicitly targetable (junior/mid level, specific JD match).
            # Arinze explicitly wants these blocked — keep it strict.
            return False, f"excluded_level: {pattern}"

    # Sometimes-allowed levels (manager, lead) — blocked unless in MANAGER_OK
    for pattern in EXCLUDED_LEVELS_SOMETIMES:
        if re.search(pattern, title, re.IGNORECASE):
            if not is_manager_ok(title):
                return False, f"excluded_level: {pattern}"

    return True, ""


def save_intake(company, title, description, location, source, url):
    """Save a job as a pending intake JSON file. Returns filename on success, None on skip."""
    passes, reason = check(title, location, description)
    if not passes:
        return None
    if already_queued(title, company, url):
        return None

    os.makedirs(INTAKE_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_company = re.sub(r'[^a-zA-Z0-9]', '_', company)[:40]
    safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:60]
    fname = f"{ts}_{source}_{safe_company}_{safe_title}.json"

    intake = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_url": url,
        "company": company,
        "title": title,
        "location": location,
        "jd_text": description,
        "status": "pending",
    }

    with open(os.path.join(INTAKE_DIR, fname), "w") as f:
        json.dump(intake, f, indent=2)

    return fname


def already_queued(title, company, url=""):
    """Check if this job was queued recently."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_WINDOW_DAYS)
    if not os.path.isdir(INTAKE_DIR):
        return False
    for fname in os.listdir(INTAKE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(INTAKE_DIR, fname)) as f:
                d = json.load(f)
            if d.get("title") == title and d.get("company") == company:
                received = d.get("received_at", "")
                if received > cutoff.isoformat():
                    return True
            # URL-based dedup
            if url and d.get("source_url") == url:
                return True
        except:
            pass
    return False


# === CLI (called by scrapers) ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: sharp_filter.py check <title> [<loc>] [<desc>]")
        print("       sharp_filter.py save <company> <title> <desc> <location> <source> <url>")
        sys.exit(0)

    action = sys.argv[1]

    if action == "check":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        location = sys.argv[3] if len(sys.argv) > 3 else ""
        desc = sys.argv[4] if len(sys.argv) > 4 else ""
        passes, reason = check(title, location, desc)
        if passes:
            print("PASS")
        else:
            print(f"SKIP: {reason}")
        sys.exit(0 if passes else 1)

    elif action == "save":
        if len(sys.argv) < 8:
            print("Usage: sharp_filter.py save <company> <title> <desc> <location> <source> <url>")
            sys.exit(1)

        company = sys.argv[2]
        title = sys.argv[3]
        desc = sys.argv[4]
        location = sys.argv[5]
        source = sys.argv[6]
        url = sys.argv[7]

        # Run loose filter
        passes, reason = check(title, location, desc)
        if not passes:
            print(f"SKIPPED:{reason}")
            sys.exit(0)

        # Check dedup
        if already_queued(title, company, url):
            print("SKIPPED:dedup")
            sys.exit(0)

        # Save intake file
        os.makedirs(INTAKE_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        safe_company = re.sub(r'[^a-zA-Z0-9]', '_', company)[:40]
        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:60]
        fname = f"{ts}_{source}_{safe_company}_{safe_title}.json"

        intake = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "source_url": url,
            "company": company,
            "title": title,
            "location": location,
            "jd_text": desc,
            "status": "pending",
        }

        with open(os.path.join(INTAKE_DIR, fname), "w") as f:
            json.dump(intake, f, indent=2)

        # Log to discovery log
        log_file = os.path.join(os.path.dirname(INTAKE_DIR), "state", "discovery.log")
        with open(log_file, "a") as lf:
            lf.write(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}]   → QUEUED: {title[:60]} at {company}\n")

        print(f"SAVED={fname}")

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
