#!/bin/bash

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---

cd "$HAXJOBS_HOME/dashboard"
npx vite build --outDir dist
echo 'Dashboard built and ready for restart: dashctl restart'
