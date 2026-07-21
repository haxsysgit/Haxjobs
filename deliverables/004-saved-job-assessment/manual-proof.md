# Plan 004 Manual Proof

## Status

Final review is pending, not approved. No live model, public network, private fixture, or interactive proof was run by this writer. Live/private proof remains controller-owned.

## Verified CLI help

`PYTHONPATH=src:. uv run -- haxjobs --help` and `... haxjobs chat --help` were verified. The chat command exposes `--new`, `--resume`, `--fake`, `--fake-delay`, `--session-db`, `--person-id`, and `--track-id`.

## Safe fake CLI proof

Use a fresh temporary directory for both databases. The tracked synthetic fixture is migrated into that temporary career database before starting chat; neither command reads or mutates `state/`.

```bash
set -eu
TMP_DIR="$(mktemp -d /tmp/haxjobs-plan004-proof.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
CAREER_DB="$TMP_DIR/career.db"
SESSION_DB="$TMP_DIR/session.db"

HAXJOBS_CAREER_DB="$CAREER_DB" \
  PYTHONPATH=src:. uv run -- haxjobs migrate \
  --fixture tests/fixtures/job_review/career.json

HAXJOBS_CAREER_DB="$CAREER_DB" \
  PYTHONPATH=src:. uv run -- haxjobs chat --new --fake \
  --session-db "$SESSION_DB"
```

Enter a short text prompt and press Ctrl+D on an empty prompt to exit. The CLI fake model is deliberately text-only. It does **not** call job tools, inspect a source, or record an assessment. The safe observation is only that a no-network text response can be entered and persisted in a configured session using the same temporary career database.

## Automated trajectory proof

The saved-job tool trajectory is covered separately by deterministic pytest tests, including injected resolver/transport and no public network:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q \
  tests/test_trajectory_job_328.py tests/test_job_source.py \
  tests/test_employment_tools.py
```

Those tests exercise saved-job retrieval, source inspection, assessment dispatch, resume, and persistence boundaries. They are not a claim about the CLI `--fake` model.

## Controller-owned proof

A controller may perform attended interactive proof with approved credentials and private fixtures. Do not record credentials, raw private fixture data, live model output, or PTY transcripts here. Live provider verification remains deferred.

| Field | Value (controller fills) |
|---|---|
| Date | |
| Worktree commit | |
| Session DB path | |
| CLI fake text-only result | |
| Automated trajectory result | |
| Live/private proof result | deferred |
| Verdict | final review pending |
