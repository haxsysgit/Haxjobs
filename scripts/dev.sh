#!/usr/bin/env bash
# Source this file before running haxjobs in development.
# Usage: source scripts/dev.sh
#
# All runtime state lives under the checkout (will be gitignored).
# Real ~/.haxjobs/ is never touched.

export HAXJOBS_HOME="$(pwd)"
export PYTHONPATH="src:."
echo "Dev environment: HAXJOBS_HOME=$HAXJOBS_HOME"
