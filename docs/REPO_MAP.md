# HaxJobs Repo Map

Status: reset inventory
Date: 2026-06-11
Purpose: identify what is active, generated, legacy, future automation, or documentation so HaxJobs can be cleaned without breaking Archilles.

## 1. Source of truth workflow

```text
Jade local checkout: /home/hax/haxjobs
GitHub source:      https://github.com/haxsysgit/Haxjobs
Archilles checkout: /home/hermes/haxjobs
Update command:     haxjobs-update
```

Jade edits and commits locally. GitHub stores the shared source. Archilles pulls with `haxjobs-update` and runs the live automation.

Archilles is the only agent that should send Telegram messages.

## 2. Runtime model today

Current active runtime is still mixed:

```text
discovery scripts → sharp_filter.py → intake JSON + SQLite jobs
cron/run_pipeline.sh → evaluate_with_hermes.py → SQLite evaluations + intake sync
dashboard/api_server.py → reads SQLite and pack folders
```

Known drift:

- SQLite should become the only job source of truth.
- `intake/*.json` should become raw import/archive, not the live database.
- Per-job packs should stop generating fresh CVs by default.
- Telegram digest is not cleanly implemented yet.

## 3. Active runtime files

These files are in the current live path or directly support it.

### Root runtime

| Path | Status | Notes |
|---|---|---|
| `api_server.py` | active | Python HTTP API and dashboard static server on port 8800. Imports route handlers and `pipeline_db`. |
| `dashctl.sh` | active | Starts/stops/restarts API server and dashboard services on Archilles. |
| `pipeline_db.py` | active compatibility wrapper | Re-exports `db/` modules so old imports still work. Keep until imports are cleaned. |
| `evaluate_with_hermes.py` | active but needs refactor | Evaluates jobs through Hermes and saves fit reports. Does not correctly own pack generation. |
| `cron/run_pipeline.sh` | active | Current system cron calls this every 30 minutes on Archilles. Processes one job per run. |
| `scripts/haxjobs-update` | active | Pulls GitHub source to Archilles, installs dashboard deps, restarts services unless `--no-restart`. |

### Database layer

| Path | Status | Notes |
|---|---|---|
| `db/schema.py` | active | Defines SQLite schema. Missing reset-target fields like role family, source quality, CV variant, pack status, outreach status. |
| `db/jobs.py` | active | Job insert/update/read functions. |
| `db/evaluations.py` | active | Evaluation read/write functions. |
| `db/activity.py` | active | Activity feed. |
| `db/decisions.py` | active | User decisions such as approved, unskipped, auto_apply markers. |
| `db/favorites.py` | active | Dashboard favorites. |
| `db/saved.py` | active | Saved jobs. |
| `db/stats.py` | active | Dashboard and status counts. |
| `db/whitelist.py` | active | Whitelist suggestions and evaluation context. |
| `db/seed.py` | utility | Seeds database from intake files. Useful during transition, not product core. |

### Dashboard API routes

| Path | Status | Notes |
|---|---|---|
| `server/routes/jobs.py` | active | `/api/jobs`, approvals, saved jobs, auto-apply decision markers. Does not run browser auto-apply itself. |
| `server/routes/resources.py` | active | Packs, profile, discovery, activity, whitelist, trigger pipeline. |

### Discovery

| Path | Status | Notes |
|---|---|---|
| `discovery/sharp_filter.py` | active | Loose pre-filter. Should stay loose. |
| `discovery/lever_scraper.sh` | active via Archilles cron wrapper | Direct/API source discovery. |
| `discovery/ashby_scraper.sh` | active via Archilles cron wrapper | Direct/API source discovery. |
| `discovery/greenhouse_scraper.sh` | active via Archilles cron wrapper | Direct/API source discovery. |
| `discovery/hn_monthly.sh` | active via Archilles cron wrapper | Monthly HN discovery. |
| `discovery/mongoose_scraper.py` | active-ish | Mongoose jobs discovery. Third-party/graylist, should be lower priority than direct sources. |
| `discovery/mongoose_scraper.sh` | active via Archilles cron wrapper | Shell wrapper for Mongoose discovery. |
| `discovery/browser_scraper.py` | active but fragile | Generic Playwright scraper used by Experis, BCG, Reed, CWJobs cron entries. Needs review before trusting. |
| `discovery/dedup.py` | utility | Useful for discovery cleanup if wired. |
| `discovery/companies.txt` | config data | Lever/company slug list. |
| `discovery/ashby_companies.txt` | config data | Ashby company slug list. |
| `discovery/greenhouse_companies.txt` | config data | Greenhouse company slug list. |
| `discovery/unknown_companies.txt` | config data | Candidate company list. |
| `discovery/company_ranking.json` | config/data | Company priority signal if maintained. |
| `discovery/us_sponsorship.json` | config/data | Sponsorship context, may be less important for UK-first search. |

### Dashboard frontend

| Path | Status | Notes |
|---|---|---|
| `dashboard/` | active | React/Vite dashboard source. Source should be committed. `node_modules/` and `dist/` should not be committed. |
| `dashboard/src/` | active | Main frontend code. |
| `dashboard/package.json` | active | Dashboard dependency and scripts. |
| `dashboard/vite.config.ts` | active | Vite config. |
| `dashboard/dist/` | generated runtime | Build output. Ignored by git. Can exist locally and on Archilles. |
| `dashboard/node_modules/` | generated dependency dir | Ignored by git. Large local folder, not source. |

## 4. Profile and CV source

| Path | Status | Notes |
|---|---|---|
| `profile/arinze_profile.local.json` | active profile source | Current profile used by evaluator. Needs consolidation into a clearer master profile. |
| `cv_profile.typed.json` | active CV governance source | Typed CV facts and locked constants. Useful for variant generation. |
| `cv_template.html` | active CV generation template | Used by CV generation flow. |
| `cv_generate.py` | active utility | Generates/exports CV from typed profile. Should support variant generation later. |
| `cv_validator.py` | active gate | Validates CV output. Keep and extend. |
| `cv_profile_helper.py` | utility | Interactive profile maintenance helper. |
| `pack_builder.sh` | utility/future | CV validator gate + PDF export for pack dirs. Current target says packs should not create per-job CVs by default. |
| `cv_variants/` | active CV variant registry | Stable reusable CV variant directories and registry. PDFs/HTML stay private and should be pulled from Archilles when needed. |
| `application_templates/` | active template source | Reusable CV briefs, dynamic cover-letter templates, and pack templates for each role family. |

## 5. Future automation lane

These are useful long term, but should not be part of the core reset path until the workflow is stable.

| Path | Status | Notes |
|---|---|---|
| `legacy/discovery/auto_apply.py` | future automation lane, isolated | Browser form filler. Not called by current cron. Keep isolated until Level 2/3 automation is designed and tested. |
| `legacy/discovery/site_knowledge.json` | future automation lane, isolated | Selectors/quirks for ATS auto-fill. Useful with `auto_apply.py`, but not current core. |
| Dashboard auto-apply toggle | future automation lane | `server/routes/jobs.py` records an `auto_apply` decision marker. It does not submit applications. Keep as intent marker. |
| `discovery/auto_trigger.sh` | future automation lane | Needs review before use. |

Automation ladder from product spec:

```text
0 discovery/ranking only
1 copy-paste docs and answers
2 prefill forms
3 upload docs and stop before submit
4 approved submit for known safe forms
5 full automation for trusted repeatable flows
```

Reset scope should target levels 0 to 2 first.

## 6. Legacy or cleanup candidates

Do not delete these blindly. Move behind `legacy/` only after import checks and a passing smoke test.

| Path | Status | Reason |
|---|---|---|
| `legacy/process_pending_intakes.py` | legacy isolated | Large old all-in-one pipeline. `BUGLIST.md` already marks it dead code. It still contains stale per-job `Tailored_CV` behavior. |
| `post_process.py` | legacy or transition utility | Root-level status reconciler. Current active runner uses `cron/sync_db_to_intake.py`, not this root file. Confirm before moving. |
| `cron/post_process.py` | transition utility | Similar purpose to root `post_process.py`. Needs consolidation with DB-first model. |
| `legacy/visuals/infographic/` | non-runtime visual artifact | Useful as reference only. Not part of live system. |
| `check_dashboard.py` | dev utility | Keep only if actively used for dashboard smoke checks. |
| `dev_reload.py` | dev utility | Local/dev convenience. Not product core. |
| `dev-watch.sh` | dev utility | Local/dev convenience. |
| `build-dash.sh` | dev/deploy utility | Useful if it reflects current Vite flow. Needs review against `haxjobs-update`. |
| `buildnext.md` | old notes | Review and archive if stale. |
| `frameconvo.md` | old notes | Review and archive if stale. |
| `AUDIT-2026-06-08.md` | historical audit | Keep under docs/archive later. |
| `AUDIT_PLAN.md` | historical audit plan | Keep under docs/archive later. |
| `BRIDGE-2026-06-08.md` | historical bridge note | Keep under docs/archive later. |
| `MILESTONE_2_PLAN.md` | historical plan | Merge useful parts into current reset plan or archive. |
| `CV_FRAME_GOVERNANCE.md` | useful concept doc | Keep if still accurate. Otherwise rewrite around CV variants. |

## 7. Documentation map

| Path | Status | Notes |
|---|---|---|
| `docs/HAXJOBS_PRODUCT_SPEC.md` | canonical | Defines the actual product goal. Read first. |
| `docs/HAXJOBS_RESET_PLAN.md` | canonical plan | Step-by-step reset plan. |
| `docs/REPO_MAP.md` | canonical inventory | This file. Use before moving/deleting files. |
| `docs/ROADMAP.md` | needs review | May contain stale roadmap language. |
| `docs/ARCHITECTURE.md` | needs review | Check against current reset spec before trusting. |
| `docs/DATA_MODEL.md` | needs review | Likely stale because DB schema is changing. |
| `docs/APPLICATION_PACK_STANDARD.md` | needs review | Should be updated to reusable CV variant model. |
| `docs/APPLICATION_WORKFLOW.md` | needs review | Should reflect automation ladder. |
| `docs/BROWSER_EXTENSION.md` | future | Browser extension remains possible but not reset scope. |
| `docs/HERMES_INTEGRATION.md` | useful but verify | Should reflect Archilles-only Telegram and `haxjobs-update`. |
| `docs/ARCHILLES_JOB_PIPELINE_PLAN.md` | historical/current mix | Useful context, but product spec supersedes it. |
| `docs/Job_Site_Feasibility_Research_Report.*` | research artifact | Useful source-quality reference. |
| `docs/roadmaps/` | roadmap archive/current | Review after reset spec. |

## 8. Generated/runtime paths that should not be committed

These may exist locally or on Archilles, but should stay out of git:

```text
.venv/
__pycache__/
*.pyc
dashboard/node_modules/
dashboard/dist/
dashboard/assets/
intake/
packs/
state/
reports/
outreach/
*.sqlite
*.db
*.log
.linkedin-profile/
```

Current audit found ignored generated folders locally:

```text
__pycache__/
cron/__pycache__/
server/routes/__pycache__/
db/__pycache__/
discovery/__pycache__/
dashboard/dist/
```

They are not tracked, but they make the local tree feel bloated. It is safe to remove local caches when needed:

```bash
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
rm -rf dashboard/dist
```

Do not remove Archilles runtime folders unless explicitly cleaning runtime state.

## 9. Archilles cron reality at time of map

System crontab currently runs:

```text
*/30 * * * * /home/hermes/haxjobs/cron/run_pipeline.sh
0 8 */2 * * /home/hermes/.hermes/scripts/job-discovery-lever_scraper.sh
0 9 */2 * * /home/hermes/.hermes/scripts/job-discovery-ashby_scraper.sh
0 10 */2 * * /home/hermes/.hermes/scripts/job-discovery-greenhouse_scraper.sh
0 8 1 * * /home/hermes/.hermes/scripts/job-discovery-hn_monthly.sh
0 12 */2 * * /home/hermes/.hermes/scripts/job-discovery-graylist_mongoose.sh
0 14 */3 * * python3 /home/hermes/haxjobs/discovery/browser_scraper.py experis
0 14 * * 1 python3 /home/hermes/haxjobs/discovery/browser_scraper.py bcg
0 16 */3 * * python3 /home/hermes/haxjobs/discovery/browser_scraper.py reed
0 17 */3 * * python3 /home/hermes/haxjobs/discovery/browser_scraper.py cwjobs
```

Reset target is fewer named scripts:

```text
cron/discover_jobs.sh
cron/evaluate_jobs.sh
cron/send_telegram_digest.sh
cron/healthcheck.sh
```

Do not replace crontab until those scripts exist and pass manual tests.

## 10. Import and usage findings

Legacy candidate usage check found:

- `legacy/process_pending_intakes.py` is referenced by docs/BUGLIST/historical notes, not active runtime imports.
- `legacy/discovery/auto_apply.py` is not called by cron, but the dashboard records `auto_apply` decisions. Treat browser auto-apply as a future lane, not dead forever.
- `legacy/discovery/site_knowledge.json` is used by `legacy/discovery/auto_apply.py` only.
- `job_classifier.py` is actively called by `cron/run_pipeline.sh`.
- `sync_db_to_intake.py` is actively called by `cron/run_pipeline.sh`.
- `cron/send_email.py` exists but email should not be the primary notification route.
- Telegram delivery should be implemented via Archilles, not local Jade.

## 11. Next safe cleanup sequence

Recommended next commits:

1. Add `profile/role_taxonomy.json` and tests for role-family classification.
2. Create `evaluation/role_family.py` and route job classification through it.
3. Create `cv_variants/` from `base_cvs/` without changing existing generated PDFs yet.
4. Add DB fields for role family, source quality, recommended CV variant, pack status, and outreach status.
5. Create markdown-first per-job pack generator that references a CV variant instead of creating a fresh CV.
6. Move true legacy files to `legacy/` only after tests and compile checks pass.

## 12. Rule for future cleanup

Before deleting or moving any file, answer:

1. Is it called by Archilles cron?
2. Is it imported by `api_server.py`, `cron/run_pipeline.sh`, or dashboard routes?
3. Does it hold profile/CV truth?
4. Is it runtime output that should be ignored, not deleted from source?
5. Is it future browser automation that should be isolated, not destroyed?

If uncertain, move to `legacy/` with a short note instead of deleting.
