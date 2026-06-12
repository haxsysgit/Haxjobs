#!/bin/bash
# HaxJobs Pipeline Runner v2 — step-by-step, one job at a time
# Uses evaluate_with_hermes.py for precise Hermes evaluation.
# Run by system crontab every 3 hours.
# Each invocation processes exactly ONE pending job.
set -euo pipefail
cd /home/hermes/haxjobs

LOG_FILE="state/pipeline.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"; }

# Count pending jobs
PENDING=$(python3 -c "
import sys; sys.path.insert(0, '.')
import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")

if [ "$PENDING" -eq 0 ]; then
    log "No pending jobs. Checking for evaluated jobs that need packs..."
    log "Pack generation: creating ready packs for evaluated jobs..."
    python3 generate_ready_packs.py --limit 10 2>&1 | tee -a "$LOG_FILE"
    python3 pipeline_db.py classify-roles 2>&1 | tee -a "$LOG_FILE"
    python3 /home/hermes/haxjobs/cron/sync_db_to_intake.py
    log "Pipeline done."
    exit 0
fi

log "Pipeline starting — $PENDING pending jobs. Processing 1 job..."

# ── Job Classifier: build cluster index + check pack reuse ──
log "Building job classification index..."
python3 discovery/job_classifier.py classify 2>&1 | tee -a "$LOG_FILE"

# ── Process exactly ONE job using evaluate_with_hermes.py ──
python3 evaluate_with_hermes.py --batch 1 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=$?

# Re-count pending
PENDING_AFTER=$(python3 -c "
import sys; sys.path.insert(0, '.')
import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")

if [ $EXIT_CODE -eq 0 ]; then
    log "Job evaluated successfully. $PENDING_AFTER remaining."
else
    log "Evaluation had issues (exit $EXIT_CODE). $PENDING_AFTER remaining."
fi

# If there are more pending and this is a manual trigger, process another
# (system crontab fires every 3h, so naturally processes 8 jobs/day)
if [ "${1:-}" = "--all" ] && [ "$PENDING_AFTER" -gt 0 ]; then
    log "--all mode: processing remaining $PENDING_AFTER jobs one at a time..."
    while [ "$PENDING_AFTER" -gt 0 ]; do
        sleep 5
        python3 evaluate_with_hermes.py --batch 1 2>&1 | tail -3 | tee -a "$LOG_FILE"
        PENDING_AFTER=$(python3 -c "
import sys; sys.path.insert(0, '.')
import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")
        log "Remaining: $PENDING_AFTER"
    done
    log "--all mode: complete."
fi

# Create packs for evaluated jobs that are ready. Keep this separate from
# evaluation so Hermes scoring and markdown pack generation stay debuggable.
log "Pack generation: creating ready packs for evaluated jobs..."
python3 generate_ready_packs.py --limit 10 2>&1 | tee -a "$LOG_FILE"

python3 pipeline_db.py classify-roles 2>&1 | tee -a "$LOG_FILE"
python3 /home/hermes/haxjobs/cron/sync_db_to_intake.py
log "Pipeline done."
