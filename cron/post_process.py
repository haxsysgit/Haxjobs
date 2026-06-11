#!/usr/bin/env python3
"""Pipeline post-processor: matches packs to intake files, backfills metadata.
Phase 1: Process PENDING jobs — find matching packs, mark completed/skipped.
Phase 2: Backfill skip_reason for SKIPPED jobs that don't have one.
Phase 3: Backfill pack_dir for COMPLETED jobs missing pack_dir.
Runs after the main pipeline to fix LLM sessions that forget to update status.
"""
import json, os, glob, sys
from datetime import datetime, timezone

INTAKE_DIR = "/home/hermes/haxjobs/intake"
PACKS_DIR = "/home/hermes/haxjobs/packs"

def normalize(s):
    return s.lower().replace(" ", "_").replace("/", "_").replace("-", "_")[:40]

def find_pack_dir(company, title):
    """Try to find a matching pack directory."""
    cn = normalize(company)
    tn = normalize(title)
    for d in glob.glob(os.path.join(PACKS_DIR, "*")):
        dn = os.path.basename(d).lower()
        if cn in dn and tn[:15] in dn:
            return d
    return None

def count_pdfs(pack_dir):
    return len(glob.glob(os.path.join(pack_dir, "**", "*.pdf"), recursive=True))

def derive_skip_reason(data):
    """Derive a meaningful skip_reason from fit data when none is set."""
    fit_score = data.get("fit_score", data.get("fit_report", {}).get("fit_score", 0))
    verdict = data.get("fit_verdict", data.get("fit_report", {}).get("fit_verdict", ""))
    
    if fit_score < 40:
        return "Poor fit — score below threshold for pack generation"
    elif fit_score < 60:
        return "Marginal fit — review manually before generating pack"
    elif verdict == "SKIP":
        return "Marked as SKIP by fit evaluator"
    elif not fit_score:
        return "No fit evaluation data available"
    return "Skipped during pipeline processing"

pending_to_completed = 0
pending_to_skipped = 0
backfill_skip_reason = 0
backfill_pack_dir = 0
already = 0
pending_no_pack = 0

for fpath in sorted(glob.glob(os.path.join(INTAKE_DIR, "*.json"))):
    try:
        with open(fpath) as f:
            data = json.load(f)
    except:
        continue

    status = data.get("status", "")
    company = data.get("company", "")
    title = data.get("title", "")
    modified = False

    # === Phase 1: Process pending jobs ===
    if status == "pending":
        pack_dir = find_pack_dir(company, title)

        if pack_dir and count_pdfs(pack_dir) > 0:
            data["status"] = "completed"
            data["pack_dir"] = pack_dir
            data["processed_at"] = datetime.now(timezone.utc).isoformat()
            print(f"FIXED (pending→completed): {os.path.basename(fpath)} → pack: {os.path.basename(pack_dir)}")
            pending_to_completed += 1
            modified = True
        elif pack_dir:
            # Pack dir exists but no PDFs — pack generation failed
            data["status"] = "skipped"
            if not data.get("skip_reason"):
                data["skip_reason"] = "Pack directory exists but no PDFs generated"
            print(f"FIXED (pending→skipped): {os.path.basename(fpath)} → no PDFs in pack dir")
            pending_to_skipped += 1
            modified = True
        else:
            # No pack found — keep as pending for next cycle
            pending_no_pack += 1

    # === Phase 2: Backfill skip_reason for skipped jobs ===
    elif status == "skipped":
        if not data.get("skip_reason"):
            data["skip_reason"] = derive_skip_reason(data)
            print(f"BACKFILL skip_reason: {os.path.basename(fpath)} → \"{data['skip_reason'][:60]}\"")
            backfill_skip_reason += 1
            modified = True

    # === Phase 3: Backfill pack_dir for completed jobs ===
    elif status == "completed":
        if not data.get("pack_dir"):
            pack_dir = find_pack_dir(company, title)
            if pack_dir:
                data["pack_dir"] = pack_dir
                print(f"BACKFILL pack_dir: {os.path.basename(fpath)} → {os.path.basename(pack_dir)}")
                backfill_pack_dir += 1
                modified = True
    else:
        already += 1
        continue

    if modified:
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)

print(f"\n=== Post-Process Results ===")
print(f"  Pending → Completed:  {pending_to_completed}")
print(f"  Pending → Skipped:    {pending_to_skipped} (pack dir exists, no PDFs)")
if pending_no_pack:
    print(f"  Pending (no pack):    {pending_no_pack} — left pending for next cycle")
print(f"  Backfill skip_reason: {backfill_skip_reason}")
print(f"  Backfill pack_dir:    {backfill_pack_dir}")
print(f"  Already processed:    {already}")
print(f"  TOTAL modified:       {pending_to_completed + pending_to_skipped + backfill_skip_reason + backfill_pack_dir}")
print("Post-processing complete.")
