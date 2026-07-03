#!/bin/bash
# HaxJobs Pipeline Runner v3 — full pipeline with configurable discovery
# Run by system crontab every 30 minutes.
# Discovery runs conditionally (once per discovery_interval_minutes).
# Evaluation processes evaluate_batch jobs per tick.
set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---
cd "$HAXJOBS_HOME"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src:."

LOG_FILE="state/pipeline.log"
DISCOVERY_MARKER="state/.last_discovery"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"; }

# Read config values
BATCH=$(python3 -c "
from haxjobs.config import CRON_CONFIG
print(CRON_CONFIG.get('evaluate_batch', 1))
")
DISCOVERY_INTERVAL=$(python3 -c "
from haxjobs.config import CRON_CONFIG
print(CRON_CONFIG.get('discovery_interval_minutes', 720))
")

# ── Conditional discovery (plan 026) ──
# Run discovery if the marker is missing or older than discovery_interval_minutes.
if [ ! -f "$DISCOVERY_MARKER" ] || [ "$(find "$DISCOVERY_MARKER" -mmin +"$DISCOVERY_INTERVAL")" ]; then
    log "Running discovery cycle…"
    python3 -m haxjobs.pipeline_db discover-full 2>&1 | tee -a "$LOG_FILE" || log "Discovery had issues (continuing)"
    touch "$DISCOVERY_MARKER"
else
    log "Discovery skipped (last run within ${DISCOVERY_INTERVAL} minutes)."
fi

# Count pending jobs
PENDING=$(python3 -c "
from haxjobs import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")

if [ "$PENDING" -eq 0 ]; then
    log "No pending jobs. Pipeline done."
    exit 0
fi

log "Pipeline starting — $PENDING pending jobs. Processing up to $BATCH job(s)…"

# ── Evaluate batch ──
python3 -m haxjobs.evaluate.run --batch "$BATCH" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=$?

# Re-count pending
PENDING_AFTER=$(python3 -c "
from haxjobs import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")

if [ $EXIT_CODE -eq 0 ]; then
    log "Evaluation done. $PENDING_AFTER remaining."
else
    log "Evaluation had issues (exit $EXIT_CODE). $PENDING_AFTER remaining."
fi

# --all mode: process everything in a single run
if [ "${1:-}" = "--all" ] && [ "$PENDING_AFTER" -gt 0 ]; then
    log "--all mode: processing remaining $PENDING_AFTER jobs…"
    while [ "$PENDING_AFTER" -gt 0 ]; do
        sleep 5
        python3 -m haxjobs.evaluate.run --batch "$BATCH" 2>&1 | tail -3 | tee -a "$LOG_FILE"
        PENDING_AFTER=$(python3 -c "
from haxjobs import pipeline_db as db
db.init()
print(db.get_stats()['pending'])
")
        log "Remaining: $PENDING_AFTER"
    done
    log "--all mode: complete."
fi

# Always refresh classifications and report
python3 -m haxjobs.pipeline_db classify-roles 2>&1 | tee -a "$LOG_FILE"

python3 cron/generate_cycle_report.py 2>&1 | tee -a "$LOG_FILE"

log "Pipeline done."
