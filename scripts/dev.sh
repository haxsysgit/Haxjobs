#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
API_PID_FILE="$RUN_DIR/api.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
API_LOG_FILE="$RUN_DIR/api.log"
WEB_LOG_FILE="$RUN_DIR/web.log"
API_PORT=8000
WEB_PORT=5173
API_HOST=127.0.0.1
WEB_HOST=127.0.0.1

mkdir -p "$RUN_DIR"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev.sh <start|stop|restart|status|ps|logs> [api|web]
EOF
}

listener_pid() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
  fi
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' <"$pid_file"
  fi
}

is_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

service_status() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  local log_file="$4"
  local pid
  local state="dead"

  pid="$(read_pid "$pid_file")"
  if is_alive "$pid"; then
    state="alive"
  fi

  printf '%-8s pid=%-8s port=%-5s state=%-5s log=%s\n' \
    "$name" "${pid:-missing}" "$port" "$state" "$log_file"
}

print_links() {
  cat <<EOF

Open:
  web: http://$WEB_HOST:$WEB_PORT/
  api: http://$API_HOST:$API_PORT/docs
  health: http://$API_HOST:$API_PORT/api/health

Logs:
  ./scripts/dev.sh logs web
  ./scripts/dev.sh logs api
EOF
}

start_api() {
  local pid
  local existing_pid
  pid="$(read_pid "$API_PID_FILE")"
  if is_alive "$pid"; then
    echo "API already running on pid $pid"
    return
  fi
  existing_pid="$(listener_pid "$API_PORT")"
  if is_alive "$existing_pid"; then
    echo "$existing_pid" >"$API_PID_FILE"
    echo "Adopted existing api listener on port $API_PORT"
    return
  fi

  : >"$API_LOG_FILE"
  nohup setsid bash -lc "cd '$ROOT_DIR' && uv run fastapi dev main.py --host '$API_HOST' --port '$API_PORT'" \
    >>"$API_LOG_FILE" 2>&1 < /dev/null &
  echo $! >"$API_PID_FILE"
  echo "Started api on port $API_PORT"
}

start_web() {
  local pid
  local existing_pid
  pid="$(read_pid "$WEB_PID_FILE")"
  if is_alive "$pid"; then
    echo "Web already running on pid $pid"
    return
  fi
  existing_pid="$(listener_pid "$WEB_PORT")"
  if is_alive "$existing_pid"; then
    echo "$existing_pid" >"$WEB_PID_FILE"
    echo "Adopted existing web listener on port $WEB_PORT"
    return
  fi

  : >"$WEB_LOG_FILE"
  nohup setsid bash -lc "cd '$ROOT_DIR/web' && npm run dev -- --host '$WEB_HOST' --port '$WEB_PORT'" \
    >>"$WEB_LOG_FILE" 2>&1 < /dev/null &
  echo $! >"$WEB_PID_FILE"
  echo "Started web on port $WEB_PORT"
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  local pid
  local listening_pid

  pid="$(read_pid "$pid_file")"
  if ! is_alive "$pid"; then
    listening_pid="$(listener_pid "$port")"
    if is_alive "$listening_pid"; then
      kill "$listening_pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
    echo "$name already stopped"
    return
  fi

  kill "$pid" 2>/dev/null || true
  for _ in {1..20}; do
    if ! is_alive "$pid"; then
      break
    fi
    sleep 0.2
  done
  if is_alive "$pid"; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  listening_pid="$(listener_pid "$port")"
  if is_alive "$listening_pid"; then
    kill "$listening_pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  echo "Stopped $name"
}

show_ps() {
  local pid_file="$1"
  local pid
  pid="$(read_pid "$pid_file")"
  if is_alive "$pid"; then
    ps -p "$pid" -o pid=,ppid=,stat=,etime=,command=
  fi
}

show_logs() {
  touch "$API_LOG_FILE" "$WEB_LOG_FILE"
  case "${1:-all}" in
    api)
      tail -n 40 -f "$API_LOG_FILE"
      ;;
    web)
      tail -n 40 -f "$WEB_LOG_FILE"
      ;;
    all)
      tail -n 40 -f "$API_LOG_FILE" "$WEB_LOG_FILE"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

command="${1:-}"

case "$command" in
  start)
    start_api
    start_web
    sleep 2
    service_status "api" "$API_PID_FILE" "$API_PORT" "$API_LOG_FILE"
    service_status "web" "$WEB_PID_FILE" "$WEB_PORT" "$WEB_LOG_FILE"
    print_links
    ;;
  stop)
    stop_service "web" "$WEB_PID_FILE" "$WEB_PORT"
    stop_service "api" "$API_PID_FILE" "$API_PORT"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    service_status "api" "$API_PID_FILE" "$API_PORT" "$API_LOG_FILE"
    service_status "web" "$WEB_PID_FILE" "$WEB_PORT" "$WEB_LOG_FILE"
    print_links
    ;;
  ps)
    show_ps "$API_PID_FILE"
    show_ps "$WEB_PID_FILE"
    ;;
  logs)
    show_logs "${2:-all}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
