#!/bin/bash
# Called by discovery scrapers when they finish.
# Touches a trigger file so the pipeline runner runs immediately.
touch /tmp/pipeline-trigger
echo "[2026-06-07T04:49:51Z] Trigger set — pipeline will run on next check"
