# Plan 004 Manual Proof

## Status

Final review is pending, not approved. The automated fake source trajectory and event-loop heartbeat regressions are covered by the isolated test suite; no live or private proof was run.

Interactive TTY proof is **controller-owned**. This noninteractive writer process cannot open a `prompt_toolkit` terminal or stream live model responses. No live model run is claimed here.

## Verified: CLI help output

The following `--help` outputs were verified after all Plan 004 repairs and before commit:

```
$ PYTHONPATH=src:. uv run -- haxjobs --help
usage: haxjobs [-h] {profile,migrate,chat} ...

Career agent platform

positional arguments:
  {profile,migrate,chat}
    profile             Career profile management
    migrate             Quick: migrate career fixture to graph
    chat                Open a live conversation with Hax

options:
  -h, --help            show this help message and exit
```

```
$ PYTHONPATH=src:. uv run -- haxjobs chat --help
usage: haxjobs chat [-h] [--new] [--resume ID] [--fake] [--fake-delay MS]
                    [--session-db SESSION_DB] [--person-id PERSON_ID]
                    [--track-id TRACK_ID]

options:
  -h, --help            show this help message and exit
  --new                 Create a new session (don't resume latest)
  --resume ID           Resume a specific session by ID
  --fake                Use fake model — no network
  --fake-delay MS       Per-event delay for fake model (ms, cancellation tests)
  --session-db SESSION_DB
                        Override session database path
  --person-id PERSON_ID
                        Person ID (valid only with --new)
  --track-id TRACK_ID   Track ID (valid only with --new)
```

The `haxjobs chat` subcommand accepts `--person-id` and `--track-id` (Plan 004 scope) and `--fake` for no-network development. The deleted `experiment review-job` subcommand is absent.

## Controller-owned live proof procedure

This remains controller-owned and is not part of the writer verification.

The following exact commands and expected observations are provided for the controller to run in an attended interactive terminal:

### Prerequisites

```bash
# Use synthetic test fixture (no private data)
PYTHONPATH=src:. uv run -- haxjobs profile migrate --fixture tests/fixtures/job_review/career.json

# Import job fixtures (one-way, operator-controlled)
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions import discussion/fixtures/harness/job-49.json
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions import discussion/fixtures/harness/job-328.json
```

### Fake-mode trajectory (no network, no live model)

```bash
# Session 1: ask about job 49
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan004-manual.db \
  PYTHONPATH=src:. uv run -- haxjobs chat --new --fake

# Type: "What do you think of job 49?"
# Expected: get_job("job-49") tool call, assessment tool call, natural reply
# Press Ctrl+D to exit (when empty)

# Session 2: resume and ask about job 328
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan004-manual.db \
  PYTHONPATH=src:. uv run -- haxjobs chat --fake

# Type: "What about job 328?"
# Expected: get_job("job-328"), inspect_job_source, needs_more_information
```

### Expected safe observations

1. No raw career fixture content in terminal output
2. No provider credentials exposed
3. Tool lifecycle events visible (get_job, inspect_job_source, record_job_assessment)
4. Session resumes with prior history intact
5. `--person-id` and `--track-id` flags accepted with `--new`
6. `--fake` mode produces no network traffic

### Controller verification record

| Field | Value (controller fills) |
|-------|--------------------------|
| Date | |
| Worktree commit | |
| Session DB path | |
| Fake-mode job 49 result | |
| Fake-mode job 328 result | |
| Resume verification | |
| Verdict | |

No raw PTY transcripts, career text, model outputs, or credentials are stored in this file.
