#!/bin/bash
# HaxJobs local dev launcher: starts backend/API and frontend dev server.
# Usage: ./dev-app.sh {start|stop|restart|status|logs}

set -euo pipefail

if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
export HAXJOBS_HOME

BACKEND_PORT=8800
FRONTEND_PORT=5173
FRONTEND_HOST="127.0.0.1"
DASHBOARD_DIR="$HAXJOBS_HOME/dashboard"
FRONTEND_LOG="/tmp/haxjobs-vite.log"
FRONTEND_PID_FILE="/tmp/haxjobs-vite.pid"

action="${1:-start}"

is_port_listening() {
  local port="$1"
  ss -tlnp | grep -q ":$port "
}

frontend_pid_is_running() {
  if [ ! -f "$FRONTEND_PID_FILE" ]; then
    return 1
  fi

  local frontend_pid
  frontend_pid="$(cat "$FRONTEND_PID_FILE")"

  if [ -z "$frontend_pid" ]; then
    return 1
  fi

  kill -0 "$frontend_pid" 2>/dev/null
}

start_backend() {
  "$HAXJOBS_HOME/dashctl.sh" start
}

start_frontend() {
  if is_port_listening "$FRONTEND_PORT"; then
    echo "Frontend already running on http://$FRONTEND_HOST:$FRONTEND_PORT"
    return 0
  fi

  echo "Starting frontend dev server..."
  cd "$DASHBOARD_DIR"
  nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
  echo "$!" > "$FRONTEND_PID_FILE"

  sleep 2

  if is_port_listening "$FRONTEND_PORT"; then
    echo "Frontend started on http://$FRONTEND_HOST:$FRONTEND_PORT"
  else
    echo "Frontend failed to start. Check $FRONTEND_LOG"
    tail -20 "$FRONTEND_LOG" || true
    return 1
  fi
}

stop_frontend() {
  if frontend_pid_is_running; then
    local frontend_pid
    frontend_pid="$(cat "$FRONTEND_PID_FILE")"
    echo "Stopping frontend dev server (pid $frontend_pid)..."
    kill "$frontend_pid" 2>/dev/null || true
    rm -f "$FRONTEND_PID_FILE"
    sleep 1
  fi

  if is_port_listening "$FRONTEND_PORT"; then
    echo "Port $FRONTEND_PORT is still in use. Stopping remaining listener..."
    fuser -k "$FRONTEND_PORT/tcp" 2>/dev/null || true
  else
    echo "Frontend dev server stopped"
  fi
}

show_status() {
  "$HAXJOBS_HOME/dashctl.sh" status || true

  if is_port_listening "$FRONTEND_PORT"; then
    echo "Frontend: RUNNING on http://$FRONTEND_HOST:$FRONTEND_PORT"
  else
    echo "Frontend: STOPPED"
  fi

  echo ""
  echo "Open this in the browser for live dev UI:"
  echo "  http://$FRONTEND_HOST:$FRONTEND_PORT"
  echo ""
  echo "Backend/API:"
  echo "  http://127.0.0.1:$BACKEND_PORT"
}

case "$action" in
  start)
    start_backend
    start_frontend
    echo ""
    show_status
    ;;

  stop)
    stop_frontend
    "$HAXJOBS_HOME/dashctl.sh" stop
    ;;

  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;

  status)
    show_status
    ;;

  logs)
    echo "Backend log: /tmp/pipeline-api.log"
    tail -30 /tmp/pipeline-api.log 2>/dev/null || true
    echo ""
    echo "Frontend log: $FRONTEND_LOG"
    tail -30 "$FRONTEND_LOG" 2>/dev/null || true
    ;;

  *)
    echo "Usage: ./dev-app.sh {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
