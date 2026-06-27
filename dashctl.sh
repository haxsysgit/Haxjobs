#!/bin/bash
# HaxJobs Dashboard Control — start, stop, restart, clean
# Auto-detects HAXJOBS_HOME from script location when not set.

set -euo pipefail

# Resolve HAXJOBS_HOME from script location if not set
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
export HAXJOBS_HOME

PORT=8800
API_SCRIPT="$HAXJOBS_HOME/api_server.py"
LOG="/tmp/pipeline-api.log"
PACKS_DIR="$HAXJOBS_HOME/packs"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
action="${1:-status}"

case "$action" in
  check)
    echo "Checking dashboard asset integrity..."
    if python3 "$HAXJOBS_HOME/check_dashboard.py" --quiet; then
      echo "✓ All assets resolve correctly"
      exit 0
    else
      echo "✗ STALE ASSETS DETECTED — run 'dashctl deploy' to auto-fix"
      python3 "$HAXJOBS_HOME/check_dashboard.py"
      exit 1
    fi
    ;;

  deploy)
    echo "Pre-deploy check..."
    python3 "$HAXJOBS_HOME/check_dashboard.py"
    if ! python3 "$HAXJOBS_HOME/check_dashboard.py" --quiet; then
      echo ""
      echo "Auto-fixing stale references..."
      python3 "$HAXJOBS_HOME/check_dashboard.py" --fix
    fi
    echo ""
    "$SCRIPT_PATH" restart
    ;;

  start)
    if ss -tlnp | grep -q ":$PORT "; then
      echo "Dashboard already running on port $PORT"
    else
      echo "Starting dashboard..."
      nohup python3 "$API_SCRIPT" > "$LOG" 2>&1 &
      sleep 2
      if ss -tlnp | grep -q ":$PORT "; then
        echo "Dashboard started on http://127.0.0.1:$PORT"
      else
        echo "Failed to start. Check $LOG"
        tail -5 "$LOG"
      fi
    fi
    ;;

  stop)
    if ss -tlnp | grep -q ":$PORT "; then
      echo "Stopping dashboard on port $PORT..."
      fuser -k "$PORT/tcp" 2>/dev/null || true
      sleep 1
      echo "Stopped"
    else
      echo "Dashboard not running"
    fi
    ;;

  restart)
    "$SCRIPT_PATH" stop
    sleep 1
    "$SCRIPT_PATH" start
    ;;

  status)
    if ss -tlnp | grep -q ":$PORT "; then
      echo "Dashboard: RUNNING on port $PORT"
      echo "API test: $(curl -fsS http://127.0.0.1:$PORT/api/status | python3 -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("jobs", 0)) + " jobs, " + str(d.get("packs", 0)) + " packs")' 2>/dev/null || echo 'API not responding')"
    else
      echo "Dashboard: STOPPED"
    fi
    ;;

  clean)
    echo "Cleaning garbage packs (non-engineering roles)..."
    cd "$PACKS_DIR"
    PATTERN='analyst|author|oversight|support|compliance|fincrime|marketing|sales|recruiter|hr-|accountant|legal|counsel|paralegal'
    count=0
    for d in *; do
      if echo "$d" | grep -qiE "$PATTERN"; then
        echo "  Removing: $d"
        rm -rf "$d"
        ((count++))
      fi
    done
    echo "Cleaned $count garbage packs"
    echo "Remaining packs: $(ls -1 "$PACKS_DIR" | wc -l)"
    ;;

  log)
    tail "${2:-30}" "$LOG"
    ;;

  *)
    echo "Usage: dashctl {start|stop|restart|status|check|deploy|clean|log}"
    echo ""
    echo "  start    - Start the API + dashboard server on port $PORT"
    echo "  stop     - Stop the server"
    echo "  restart  - Stop then start"
    echo "  status   - Check if running"
    echo "  check    - Verify dashboard assets are not stale (exit 1 if stale)"
    echo "  deploy   - Check assets, auto-fix stale refs, then restart"
    echo "  clean    - Remove non-engineering garbage packs"
    echo "  log [N]  - Tail last N lines of server log (default 30)"
    ;;
esac
