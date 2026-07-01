# HaxJobs Data Model

Single SQLite database (`state/haxjobs.db`). All tables use integer primary keys, foreign keys with CASCADE where appropriate, and ISO-8601 timestamps.

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
| applied_at | TEXT | ISO-8601, when user clicked "apply" |
| decision | TEXT | apply, skip, reject, pending |
| decision_reason | TEXT | Why the user chose this |
| cycle_id | TEXT | Which discovery cycle this job came from |
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

### cycle_state

Tracks each pipeline run cycle for learning and reporting.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| cycle_id | TEXT UNIQUE | e.g. `2026-07-01` |
| started_at | TEXT | ISO-8601 |
| completed_at | TEXT | ISO-8601 |
| jobs_discovered | INTEGER | |
| jobs_evaluated | INTEGER | |
| packs_generated | INTEGER | |
| decisions_made | INTEGER | |

### job_history

Permanent archive of user actions on jobs. Jobs move here after apply/reject/archive.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| job_id | INTEGER FK | Reference to jobs |
| action | TEXT | applied, rejected, archived |
| action_reason | TEXT | |
| acted_at | TEXT | ISO-8601 |
| cycle_id | TEXT | Which cycle |

### learning_patterns

Learned preferences from user decisions over time.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| pattern_type | TEXT | preferred_company, rejected_keyword, salary_trend, role_preference |
| pattern_value | TEXT | The actual pattern value |
| weight | REAL | Confidence 0.0-1.0 |
| evidence_count | INTEGER | How many decisions support this |
| updated_at | TEXT | ISO-8601 |

### Supporting tables

> **Deprecated** — replaced by `decisions` table + `job_history`. Will be removed in a future DB migration.
- **favorites** — user-starred jobs (job_id UNIQUE FK)
- **saved_jobs** — user-saved jobs with notes (job_id UNIQUE FK)
- **evaluation_history** — historical scores on re-evaluation. Replaced by `evaluations.report_cycle_id`
- **decisions** — approval/rejection/skip decisions per job
- **outreach_drafts** — generated outreach messages (linked to jobs and contacts)
- **outreach_contacts** — discovered recruiter/hiring manager contacts
- **activity_log** — pipeline event log
- **profile_snapshots** — profile state captured at evaluation time
- **whitelist** — company/role whitelist patterns for evaluation

## Key relationships

```
discovered_jobs --(promoted)--> jobs
jobs --(evaluated)--> evaluations
jobs --(decided)--> decisions
decisions --(feed)--> learning_patterns
jobs --(archived)--> job_history
jobs --(outreach)--> outreach_drafts --> outreach_contacts
cycles captured in --> cycle_state
```

## Config-driven, not schema-driven

Role families, CV variants, evaluation agent choice, and delivery channels are configured in `haxjobs.toml`, not in the database schema. The DB stores data; the config drives behavior.
