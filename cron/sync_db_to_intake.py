#!/usr/bin/env python3
"""Sync pipeline.db evaluations back to intake JSON files so the dashboard can see them."""
import sqlite3, json, os, glob

DB = "/home/hermes/haxjobs/state/pipeline.db"
INTAKE = "/home/hermes/haxjobs/intake"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Get all evaluations with scores
rows = conn.execute("""
    SELECT j.id, j.title, j.company, j.location, j.source, j.source_url, j.jd_text,
           e.fit_score, e.fit_verdict, e.level, e.level_name, e.decision, e.skip_reason,
           e.strongest_matches, e.major_gaps, e.sponsorship_risk, e.summary
    FROM jobs j
    JOIN evaluations e ON j.id = e.job_id
    ORDER BY e.fit_score DESC
""").fetchall()

synced = 0
for r in rows:
    # Find matching intake file by title and company
    title = r["title"]
    company = r["company"]
    found = False
    
    for fpath in glob.glob(f"{INTAKE}/*.json"):
        try:
            d = json.load(open(fpath))
            if d.get("title") == title and d.get("company") == company:
                # Update with evaluation results
                d["status"] = "evaluated"
                d["fit_report"] = {
                    "fit_score": r["fit_score"],
                    "verdict": r["fit_verdict"],
                    "level": r["level"],
                    "level_name": r["level_name"],
                    "decision": r["decision"],
                    "skip_reason": r["skip_reason"],
                    "strongest_matches": json.loads(r["strongest_matches"]) if r["strongest_matches"] else [],
                    "major_gaps": json.loads(r["major_gaps"]) if r["major_gaps"] else [],
                    "sponsorship_risk": r["sponsorship_risk"] or "unknown",
                    "summary": r["summary"] or "",
                }
                with open(fpath, "w") as f:
                    json.dump(d, f, indent=2)
                synced += 1
                found = True
                break
        except:
            pass

conn.close()
print(f"Synced {synced} jobs from database to intake JSON files")
print(f"Dashboard should now show evaluated jobs on next refresh")
