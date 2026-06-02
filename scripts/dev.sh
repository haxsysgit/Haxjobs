#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.haxjobs/run"
LOG_DIR="$ROOT_DIR/.haxjobs/logs"
API_PID_FILE="$RUN_DIR/backend.pid"
WEB_PID_FILE="$RUN_DIR/frontend.pid"
API_LOG="$LOG_DIR/backend.log"
WEB_LOG="$LOG_DIR/frontend.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"

usage() {
  cat <<'USAGE'
Usage: ./scripts/dev.sh <command> [target]

Commands:
  start       Start backend and frontend in the background
  stop        Stop tracked backend/frontend processes
  restart     Stop then start both servers
  status      Show backend/frontend process status
  logs        Follow both logs, or pass api/backend/web/frontend
  clean       Stop tracked processes and clean stale HaxJobs dev processes

Examples:
  ./scripts/dev.sh start
  ./scripts/dev.sh logs
  ./scripts/dev.sh logs api
  ./scripts/dev.sh restart
  ./scripts/dev.sh stop
USAGE
}

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

start_backend() {
  if is_running "$API_PID_FILE"; then
    echo "backend already running (pid $(cat "$API_PID_FILE"))"
    return
  fi

  : > "$API_LOG"
  (
    cd "$ROOT_DIR"
    exec uv run uvicorn haxjobs_api.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
  ) >> "$API_LOG" 2>&1 &

  echo $! > "$API_PID_FILE"
  echo "started backend (pid $(cat "$API_PID_FILE"), log $API_LOG)"
}

start_frontend() {
  if is_running "$WEB_PID_FILE"; then
    echo "frontend already running (pid $(cat "$WEB_PID_FILE"))"
    return
  fi

  : > "$WEB_LOG"
  (
    cd "$ROOT_DIR/frontend"
    exec npm run dev -- --host 127.0.0.1
  ) >> "$WEB_LOG" 2>&1 &

  echo $! > "$WEB_PID_FILE"
  echo "started frontend (pid $(cat "$WEB_PID_FILE"), log $WEB_LOG)"
}

stop_one() {
  local name="$1"
  local pid_file="$2"

  if ! [[ -f "$pid_file" ]]; then
    echo "$name not tracked"
    return
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "stopping $name (pid $pid)"
    kill "$pid" 2>/dev/null || true

    for _ in {1..20}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done

    if kill -0 "$pid" 2>/dev/null; then
      echo "$name did not stop gracefully; killing"
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "$name was not running"
  fi

  rm -f "$pid_file"
}

stop_all() {
  stop_one "frontend" "$WEB_PID_FILE"
  stop_one "backend" "$API_PID_FILE"
}

status_one() {
  local name="$1"
  local pid_file="$2"
  local url="$3"

  if is_running "$pid_file"; then
    echo "$name: running (pid $(cat "$pid_file")) — $url"
  else
    echo "$name: stopped"
  fi
}

status_all() {
  status_one "backend" "$API_PID_FILE" "http://127.0.0.1:8000"
  status_one "frontend" "$WEB_PID_FILE" "http://127.0.0.1:5173"
}

follow_logs() {
  local target="${1:-all}"

  case "$target" in
    api|backend)
      touch "$API_LOG"
      tail -n 80 -f "$API_LOG"
      ;;
    web|frontend)
      touch "$WEB_LOG"
      tail -n 80 -f "$WEB_LOG"
      ;;
    all)
      touch "$API_LOG" "$WEB_LOG"
      tail -n 80 -f "$API_LOG" "$WEB_LOG"
      ;;
    *)
      echo "unknown log target: $target"
      usage
      exit 1
      ;;
  esac
}

clean_stale() {
  stop_all

  # These patterns are intentionally narrow to HaxJobs dev commands.
  # They clean up reload child processes or stale runs left behind by crashes.
  pkill -f "uvicorn haxjobs_api.main:app --app-dir backend" 2>/dev/null || true
  pkill -f "vite.*127.0.0.1" 2>/dev/null || true

  rm -f "$API_PID_FILE" "$WEB_PID_FILE"
  echo "cleaned tracked and stale HaxJobs dev processes"
}

command="${1:-}"
target="${2:-}"

case "$command" in
  start)
    start_backend
    start_frontend
    status_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_backend
    start_frontend
    status_all
    ;;
  status)
    status_all
    ;;
  logs)
    follow_logs "${target:-all}"
    ;;
  clean)
    clean_stale
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "unknown command: $command"
    usage
    exit 1
    ;;
esac
