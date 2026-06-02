#!/usr/bin/env bash
set -euo pipefail

uv run uvicorn haxjobs_api.main:app --app-dir backend --reload
