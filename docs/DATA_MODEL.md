# HaxJobs Data Model

Single SQLite database (`state/pipeline.db`). All tables use integer primary keys, foreign keys with CASCADE where appropriate, and ISO-8601 timestamps.

## Core tables

### discovered_jobs

Raw scraped or manually submitted jobs before processing.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| source | TEXT | `manual`, `greenhouse`, `ashby`, `lever` |
| source_url | TEXT | Unique job URL |
| apply_url | TEXT | Direct apply link if different |
| ats | TEXT | ATS platform if detected |
| external_id | TEXT | Source-specific ID |
| title | TEXT | |
| company | TEXT | |
| location | TEXT | |
| jd_text | TEXT | Full job description |
| raw_payload_json | TEXT | Original scraper output |
| discovery_status | TEXT | `new`, `duplicate`, `blacklisted`, `filtered`, `accepted` |
| filter_reason | TEXT | Why filtered/skipped |
| created_at | TEXT | ISO-8601 |
| updated_at | TEXT | ISO-8601 |

### jobs

Accepted jobs promoted from discovery.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| external_id | TEXT UNIQUE | Links back to discovered_jobs |
| title | TEXT | |
| company | TEXT | |
| location | TEXT | |
| jd_text | TEXT | |
| source_url | TEXT | |
| source | TEXT | |
| status | TEXT | `pending`, `evaluated`, `skipped` |
| role_family | TEXT | From classifier |
| role_family_confidence | REAL | 0.0-1.0 |
| recommended_cv_variant | TEXT | Which CV variant to use |
| pack_status | TEXT | `none`, `generated`, `manual_review` |
| pack_dir | TEXT | Path to pack directory |
| pack_review_status | TEXT | For L3/L4 manual review |
| outreach_status | TEXT | |
| classified_at | TEXT | ISO-8601 |
| discovered_at | TEXT | ISO-8601 |
| updated_at | TEXT | ISO-8601 |

### evaluations

Fit evaluation results. One row per evaluated job.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| job_id | INTEGER FK | UNIQUE reference to jobs |
| fit_score | INTEGER | 0-100 |
| fit_verdict | TEXT | STRONG_FIT, GOOD_FIT, WEAK_FIT, SKIP |
| level | INTEGER | 1-4 |
| level_name | TEXT | Standard, Quick Apply, Lite, Skip |
| strongest_matches | TEXT | JSON array |
| major_gaps | TEXT | JSON array |
| sponsorship_risk | TEXT | low, medium, high |
| summary | TEXT | Fit summary |
| decision | TEXT | completed, skipped |
| skip_reason | TEXT | |
| agent | TEXT | Which evaluation agent produced this |
| profile_snapshot_json | TEXT | Profile state at eval time |
| report_markdown | TEXT | Generated report section for this job |
| pack_dir | TEXT | Path to generated pack |
| pack_template_id | TEXT | Which role template was used |
| report_cycle_id | TEXT | Which cycle report this belongs to |
| evaluated_by | TEXT | Agent name |
| evaluated_at | TEXT | ISO-8601 |

### Supporting tables

- **favorites** — user-starred jobs (job_id UNIQUE FK)
- **saved_jobs** — user-saved jobs with notes (job_id UNIQUE FK)
- **decisions** — approval/rejection/skip decisions per job
- **outreach_drafts** — generated outreach messages (linked to jobs and contacts)
- **outreach_contacts** — discovered recruiter/hiring manager contacts
- **activity_log** — pipeline event log
- **evaluation_history** — historical scores when jobs are re-evaluated
- **profile_snapshots** — profile state captured at evaluation time
- **whitelist** — company/role whitelist patterns for evaluation

## Key relationships

```
discovered_jobs --(promoted)--> jobs
jobs --(evaluated)--> evaluations
jobs --(starred)--> favorites
evaluations --(historical)--> evaluation_history
jobs --(decided)--> decisions
jobs --(outreach)--> outreach_drafts --> outreach_contacts
```

## Config-driven, not schema-driven

Role families, CV variants, evaluation agent choice, and delivery channels are configured in `haxjobs.toml`, not in the database schema. The DB stores data; the config drives behavior.
