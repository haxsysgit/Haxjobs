#!/usr/bin/env python3
"""Outreach draft review — CLI tool for Archilles to present drafts.

When Arinze tells Archilles to review outreach, the agent runs this to
fetch drafts and present them. The agent handles the Telegram UI;
this script is the data layer.

Usage:
  python3 cron/review_outreach.py              # List all draft statuses
  python3 cron/review_outreach.py --pending    # Show pending drafts with full text
  python3 cron/review_outreach.py --approve 5  # Approve draft #5
  python3 cron/review_outreach.py --reject 3   # Reject draft #3
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import schema
from db.outreach import get_drafts, update_draft_status, get_jobs_for_outreach


def show_summary():
    """Compact summary of all outreach statuses."""
    schema.init()
    drafts = get_drafts()
    pending = [d for d in drafts if d["status"] == "draft"]
    approved = [d for d in drafts if d["status"] == "approved"]
    rejected = [d for d in drafts if d["status"] == "rejected"]

    print(f"Outreach Summary:")
    print(f"  Pending review:  {len(pending)}")
    print(f"  Approved:        {len(approved)}")
    print(f"  Rejected:        {len(rejected)}")
    print(f"  Total:           {len(drafts)}")

    # Show eligible jobs not yet drafted
    eligible = get_jobs_for_outreach(min_score=75)
    undrafted = [j for j in eligible if j.get("outreach_status") in ("none", "")]
    if undrafted:
        print(f"\n  Eligible (75%+) not yet drafted: {len(undrafted)}")
        for j in undrafted[:5]:
            print(f"    {j['fit_score']}% | {j['title'][:50]} at {j['company']}")


def show_pending():
    """Show all pending drafts with full message text."""
    schema.init()
    drafts = get_drafts("draft")
    if not drafts:
        print("No pending drafts to review.")
        return

    print(f"=== {len(drafts)} Pending Drafts ===\n")
    for i, d in enumerate(drafts, 1):
        score = d.get("fit_score", "?")
        print(f"[Draft #{d['id']}] {d['subject']}")
        print(f"  Job: {d.get('job_title', '?')} at {d.get('job_company', '?')} ({score}%)")
        if d.get("contact_name"):
            print(f"  Contact: {d['contact_name']} — {d.get('contact_title', '')}")
        if d.get("pack_dir"):
            print(f"  Pack: {d['pack_dir']}")
        print()
        print(d["message_text"])
        print(f"\n─── Approve: review_outreach.py --approve {d['id']}  │  Reject: review_outreach.py --reject {d['id']} ───\n")


def approve_draft(draft_id: int):
    schema.init()
    update_draft_status(draft_id, "approved")
    print(f"Draft #{draft_id} approved.")


def reject_draft(draft_id: int):
    schema.init()
    update_draft_status(draft_id, "rejected")
    print(f"Draft #{draft_id} rejected.")


if __name__ == "__main__":
    schema.init()

    if "--pending" in sys.argv:
        show_pending()
    elif "--approve" in sys.argv:
        idx = sys.argv.index("--approve")
        if idx + 1 < len(sys.argv):
            approve_draft(int(sys.argv[idx + 1]))
        else:
            print("Usage: --approve <draft_id>")
    elif "--reject" in sys.argv:
        idx = sys.argv.index("--reject")
        if idx + 1 < len(sys.argv):
            reject_draft(int(sys.argv[idx + 1]))
        else:
            print("Usage: --reject <draft_id>")
    else:
        show_summary()
