# HaxJobs BUGLIST — Full System Audit (June 8, 2026)

## CRITICAL — Dashboard data not showing

### BUG 1: skipReason not returned by API [FIXED]
- **File:** `server/routes/jobs.py` line 28
- **Symptom:** 328 filtered jobs show in UI but all say "skipped" with no reason
- **Root cause:** `list_jobs()` maps `skip_reason` field from DB. Verified working.
- **Status:** FIXED — `skipReason` now in job dict

### BUG 2: Only 2 evaluated jobs show fit scores [FIXED]
- **File:** `server/routes/jobs.py`
- **Symptom:** Dashboard shows only 2 evaluated jobs despite API returning 93 completed
- **Root cause:** `fitScore` returns 0 when `fit_score` is null in DB. Old jobs had no evaluations.
- **Status:** RESOLVED — pipeline now evaluates all jobs through evaluate_with_hermes.py

### BUG 3: packDir empty for most jobs [KNOWN]
- **File:** `server/routes/jobs.py` line 27
- **Symptom:** No pack download links in job detail
- **Root cause:** `pack_dir` not populated automatically. Pipeline generates packs but doesn't update DB consistently.
- **Fix:** Update post_process.py to set `pack_dir` when matching packs exist (post_process.py now has correct paths)

## HIGH — UI not rendering

### BUG 4: Dashboard stale cache [KNOWN]
- **File:** `index.html` (source)
- **Symptom:** User sees old UI without sub-nav, favorites, filtered tabs
- **Root cause:** Static builds create cache issues. USE DEV SERVER instead: `npx vite --port 5173 --host 0.0.0.0`
- **Fix:** `vite.config.ts` now has API proxy configured. Dev server is preferred over static builds.

### BUG 5: handleUnskip prop error [FIXED]
- **File:** `App.tsx` line 75
- **Symptom:** Pipeline component receives `onUnskip` — no longer accesses `job.jdText`
- **Status:** FIXED — `handleUnskip` now only uses `job.id`

### BUG 6: Duplicate 'pipeline' view reference [FIXED]
- **File:** `App.tsx`
- **Symptom:** TypeScript warning about comparison between View and 'pipeline'
- **Status:** FIXED — renamed to 'jobs'

## MEDIUM — Pipeline Logic

### BUG 7: "Senior Engineering Manager" passed through sharp_filter [WONT FIX]
- **File:** `discovery/sharp_filter.py`
- **Symptom:** Senior+manager roles still getting queued
- **Decision:** This is INTENTIONAL under lenient v3.0.0. sharp_filter only blocks obvious non-engineering. Hermes evaluates actual fit.

### BUG 8: Pipeline runner marks all unprocessed as 'skipped' [FIXED]
- **File:** `post_process.py`
- **Symptom:** 328 jobs marked skipped without Hermes evaluation
- **Root cause:** post_process.py was reading from wrong path (`/home/hermes/job-pipeline/` instead of `/home/hermes/haxjobs/`)
- **Status:** FIXED — paths corrected. post_process now only marks as skipped if pack dir exists with no PDFs.

### BUG 9: Batch processing skips jobs when Hermes session exits early [KNOWN]
- **File:** `cron/run_pipeline.sh`
- **Symptom:** 2 pending jobs remaining after full pipeline run
- **Root cause:** No retry logic for failed batches.
- **Fix:** Add retry logic for failed batches.

## LOW — Code Architecture

### BUG 10: api_server.py was refactored [DONE]
- **File:** Now split into `api_server.py` (routing) + `server/routes/jobs.py` + `server/routes/resources.py`
- **Status:** DONE — refactored to modular routes

### BUG 11: No TypeScript interfaces for API responses [KNOWN]
- **File:** `dashboard/src/data/api.ts`
- **Symptom:** `Job` interface has `jdText?: string` and other optional fields
- **Status:** Partial — `Job` interface covers API response shape. Some fields still use `as any` casts.

### BUG 12: CSS loaded as separate file, no SSR [WONT FIX]
- **Status:** Minor. Low priority.

## JUNE 8 AUDIT — NEW BUGS

### BUG 13: Hermes prompt had wrong thresholds [FIXED]
- **File:** `evaluate_with_hermes.py` lines 131-155
- **Symptom:** Hermes using 80/60/40 instead of approved 75/50/30
- **Status:** FIXED — prompt updated to v3.0.0 lenient mode with NOT-hard-blocker guidance

### BUG 14: post_process.py wrong paths [FIXED]
- **File:** `post_process.py` lines 8-9
- **Symptom:** Paths pointed to `/home/hermes/job-pipeline/` (old dir)
- **Status:** FIXED — changed to `/home/hermes/haxjobs/`

### BUG 15: --batch mode didn't update intake JSONs [FIXED]
- **File:** `evaluate_with_hermes.py` lines 454-463
- **Symptom:** Batch evaluation saved to DB but not intake files
- **Status:** FIXED — added intake JSON write-back in batch loop

### BUG 16: Status filter missed 'completed' jobs [FIXED]
- **Files:** `Pipeline.tsx` line 141, `JobDetail.tsx` line 5
- **Symptom:** Jobs with status 'completed' invisible in dashboard
- **Status:** FIXED — filter now accepts both 'evaluated' and 'completed'

### BUG 17: Orphaned code fragments in repo root [FIXED]
- **Symptom:** `0).fetchall()\nfor p in packs:\n...` as a filename in repo root
- **Status:** FIXED — removed

### BUG 18: vite.config.ts missing API proxy [FIXED]
- **File:** `dashboard/vite.config.ts`
- **Symptom:** Dev server couldn't reach Python API on port 8800
- **Status:** FIXED — proxy config added, `.tmp` duplicate removed

### BUG 19: process_pending_intakes.py is dead code [KNOWN]
- **File:** `process_pending_intakes.py`
- **Symptom:** 1067-line legacy file with hardcoded Spotify scoring, not imported by anything
- **Status:** Marked as LEGACY — DO NOT USE. Superseded by `evaluate_with_hermes.py`.

## VERIFICATION STEPS
After fixes are deployed:
1. Sync to Archilles: `rsync` from local to VPS
2. Rebuild dashboard: `cd /home/hermes/haxjobs/dashboard && npx vite build`
3. Restart: `dashctl restart`
4. Open http://localhost:8800, hard refresh (Ctrl+Shift+R)
5. Click Jobs → should see 4 sub-nav tabs with correct counts
6. Click Filtered → should see skip reasons
7. Verify evaluate_with_hermes.py uses 75/50/30 thresholds
