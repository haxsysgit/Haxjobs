---
name: job-fit-evaluator
description: Evaluate a job description against Arinze's profile and generate a fit report. Used by the Archilles job pipeline.
version: 1.0.0
---

# Job Fit Evaluator

## When to use
When a new job description arrives in the intake queue at /home/hermes/haxjobs/intake/

## Instructions

1. Read the oldest pending intake file (status: "pending") from /home/hermes/haxjobs/intake/
2. Load Arinze's profile from /home/hermes/haxjobs/profile/arinze_profile.local.json
3. Compare the JD against the profile

## Fit scoring weights
- Stack match (Python, FastAPI, SQLAlchemy, PostgreSQL, Docker): 40%
- Role alignment (backend, AI, automation): 25%
- Experience level match: 15%
- Location/visa feasibility: 20%

## Output format
Return a JSON fit report:
```json
{
  "fit_score": 72,
  "verdict": "PURSUE",
  "strongest_matches": ["FastAPI experience at Vigilis", "PostgreSQL + SQLAlchemy depth"],
  "major_gaps": ["No confirmed AWS production experience"],
  "sponsorship_risk": "low",
  "summary": "Strong backend match. FastAPI and PostgreSQL experience directly relevant.",
  "questions_for_arinze": []
}
```

## Thresholds
- fit_score >= 60: PURSUE — generate application pack
- fit_score 40-59: WEAK_FIT — save but don't generate pack
- fit_score < 40: SKIP — archive

## After evaluation
- If PURSUE: call the arinze-job-application-pack skill to generate the full pack
- Save the pack to /home/hermes/haxjobs/packs/{company}_{role}/
- Send notification via `hermes send -t telegram` with fit summary
- Mark intake as "completed" or "skipped" in the intake JSON file
- Log everything to /home/hermes/haxjobs/state/pipeline.log
