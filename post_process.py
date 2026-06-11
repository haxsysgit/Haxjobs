#!/usr/bin/env python3
"""Pipeline post-processor: auto-marks intakes as completed when packs exist.
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

fixed = 0
already = 0
not_found = 0

for fpath in sorted(glob.glob(os.path.join(INTAKE_DIR, "*.json"))):
    try:
        with open(fpath) as f:
            data = json.load(f)
    except:
        continue

    status = data.get("status", "")
    if status != "pending":
        already += 1
        continue

    company = data.get("company", "")
    title = data.get("title", "")
    pack_dir = find_pack_dir(company, title)

    if pack_dir and count_pdfs(pack_dir) > 0:
        data["status"] = "completed"
        data["pack_dir"] = pack_dir
        data["processed_at"] = datetime.now(timezone.utc).isoformat()
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"FIXED: {os.path.basename(fpath)} -> completed (pack: {os.path.basename(pack_dir)})")
        fixed += 1
    elif pack_dir:
        # Pack dir exists but no PDFs — mark as skipped (pack gen failed)
        data["status"] = "skipped"
        data["skip_reason"] = "Pack directory exists but no PDFs generated"
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"FIXED: {os.path.basename(fpath)} -> skipped (no PDFs in pack)")
        fixed += 1
    else:
        not_found += 1

print(f"\nResults: {fixed} fixed, {already} already done, {not_found} still pending (no pack found)")
print("Post-processing complete.")
