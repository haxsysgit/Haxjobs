# HaxJobs — Audit Plan (June 8, 2026)

## What works
- Discovery scrapers (Lever, Ashby, Greenhouse, HN, Mongoose, Reed, CWJobs, Experis, BCG)
- System crontab scheduling (11 jobs)
- sharp_filter (loose mode — blocks only HR/Finance/Legal/Sales/Senior+)
- Database (pipeline.db with 13 tables)
- Vite dev server (port 5173, hot reload)
- Python API (port 8800)

## What's broken — fix in order

### 1. [CRITICAL] Data disconnect: evaluator writes to DB, dashboard reads from files
- **Symptom:** Jobs are evaluated (83%, 72%, 70%) but dashboard shows them as pending with 0%
- **Root cause:** evaluate_with_hermes.py saves to `jobs` and `evaluations` tables in pipeline.db. API `list_intake_jobs()` reads from intake/*.json files.
- **Fix:** Make API read from DB for evaluated jobs. OR sync DB → intake files after evaluation.
- **Owner:** Jade or Archilles
- **Time:** 30 min

### 2. [CRITICAL] Pack generation not wired into evaluation pipeline
- **Symptom:** Jobs are evaluated with scores but no packs are generated
- **Root cause:** evaluate_with_hermes.py only does evaluation. Pack generation is separate (old hermes chat call)
- **Fix:** Wire pack generation as Post-evaluation step. For score >= 50: call hermes chat with arinze-job-application-pack skill.
- **Owner:** Archilles
- **Time:** 1 hour

### 3. [HIGH] Dashboard: build system broken, cache issues prevent updates
- **Symptom:** User never sees UI changes
- **Fix:** Use Vite dev server (port 5173) instead of static build. Already started. Access via tunnel or http://178.105.245.120:5173
- **Owner:** Done
- **Time:** Done

### 4. [HIGH] Evaluator too strict — rejects based on experience years
- **Symptom:** "1.5-2 years experience" used as rejection reason
- **Root cause:** Fit evaluator skill v2.x was too strict
- **Fix:** Deployed v3.0.0 (LENIENT MODE). Lowered thresholds to 75/50/30. Removed experience year gating.
- **Owner:** Done
- **Time:** Done

### 5. [MEDIUM] Dashboard shows all 110 jobs as 'pending 0%' 
- **Symptom:** Evaluated tab is empty even though 15+ jobs are evaluated
- **Root cause:** Same as #1 — data disconnect
- **Fix:** Same as #1
- **Owner:** Same as #1

### 6. [MEDIUM] Dashboard API read doesn't include skip_reason for skipped jobs
- **Symptom:** Filtered tab shows 'skipped' badge with no reason
- **Root cause:** API server maps skip_reason from intake files but evaluator saves to DB
- **Fix:** After fixing #1, add skip_reason field to API response from DB
- **Owner:** Same as #1

### 7. [LOW] Multiple JS bundles in assets/ directory
- **Symptom:** Old Cpb1gpV4.js alongside new CUT5DLTz.js
- **Fix:** Clean old assets on next deploy
- **Owner:** Jade
- **Time:** 5 min

### 8. [LOW] send_email.py still uses old skills, not cv_generate.py
- **Symptom:** Emails may use old CV template
- **Fix:** Wire cv_validator.py as gate before email send
- **Owner:** Archilles
- **Time:** 30 min

## Immediate actions for Arinze

1. **Access dashboard:** `ssh -L 5173:127.0.0.1:5173 archilles` → http://localhost:5173 (Vite dev server with hot reload)
2. **Review packs:** Pack generation in progress for mongoosegray jobs (83% + 72%)
3. **Check email:** Packs will be sent to elenasuludavid@gmail.com

## What to tell Archilles next

"Archilles, please:
1. Fix evaluate_with_hermes.py to ALSO write results back to intake JSON files (not just pipeline.db). The dashboard reads from intake files.
2. Wire pack generation as a post-evaluation step for all jobs scoring 50%+.
3. Re-run evaluation on all pending jobs using the new lenient evaluator v3.0.0."
