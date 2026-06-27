#!/bin/bash
# HaxJobs dashboard dev watcher — auto-rebuilds on source changes
# Usage: bash dev-watch.sh
# Watches dashboard/src/ for changes, rebuilds when detected.

set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---
DASHBOARD_DIR="$HAXJOBS_HOME/dashboard"

echo "Watching $DASHBOARD_DIR/src/ for changes..."
echo "Press Ctrl+C to stop."

while true; do
  inotifywait -r -e modify,create,delete "$DASHBOARD_DIR/src/" 2>/dev/null || {
    # inotifywait not available — fall back to polling every 2 seconds
    sleep 2
  }
  echo "$(date '+%H:%M:%S') Change detected — rebuilding..."
  cd "$DASHBOARD_DIR" && npm run build 2>&1 | tail -3
  echo "  Done."
done
