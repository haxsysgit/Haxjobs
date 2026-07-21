# Manual Proof — Plan 003 Corrected

## Environment

- Worktree: `/tmp/haxjobs-exec-003-corrected`
- Branch: `advisor/003-corrected`
- Baseline commit: `ae1dbce`

## Fake mode

### Prerequisites
Created minimal career graph manually:

```bash
HAXJOBS_CAREER_DB=/tmp/haxjobs-plan003-career.db python3 -c "..." # creates person, track, skill, evidence, constraint, preference
```

### Fake session composition

```bash
$ env HAXJOBS_SESSION_DB=/tmp/haxjobs-plan003-fake3.db HAXJOBS_CAREER_DB=/tmp/haxjobs-plan003-career.db haxjobs chat --fake

Session ID: e7f89baeefd4
Resume: haxjobs chat --resume e7f89baeefd4
Type your message. Enter to submit, Ctrl+J for newline, Escape to interrupt.
Ctrl+C to clear (or exit if empty), Ctrl+D to exit when empty.
```

**Result:** Session created. Composition OK. Full interactive flow requires real TTY.

## Live mode

### Provider config
Config exists at `~/.haxjobs/haxjobs.toml` with api_key, model, and base_url. Credentials not printed per plan rules.

### Live session composition

```bash
$ env HAXJOBS_SESSION_DB=/tmp/haxjobs-plan003-live-test.db HAXJOBS_CAREER_DB=/tmp/haxjobs-plan003-career.db python3 -c "
from haxjobs.employment.composition import compose_session
session = compose_session(fake=False, session_db_path='/tmp/haxjobs-plan003-live-test.db')
print(f'Session created: {session.session_id}')
"

Session created: beb5b48debdf
Live session composition: OK
```

**Result:** Live session composes correctly. Provider config resolves. Career graph connects. Full interactive live flow requires real TTY — not available in this execution environment.

## Honest blocker for full interactive manual proof

The `prompt_toolkit` terminal requires a real TTY (pseudo-terminal). The execution environment does not provide an interactive terminal — input is piped. prompt_toolkit reports "Warning: Input is not a terminal (fd=0)" and does not enter its full async prompt loop.

The fake mode and the live mode session compositions are verified programmatically. The full interactive flow (Enter submits, Ctrl+J newline, Escape interrupts, streamed deltas, tool lifecycle rendering, exit restores shell) requires a real terminal session.

## Verified by tests (not manual)

| Behaviour | Test file | Test count |
|-----------|-----------|------------|
| Enter submits | test_terminal.py | Key binding presence verified |
| Ctrl+J newline | test_terminal.py | Key binding presence verified |
| Escape aborts | test_session.py | test_abort_returns_session_to_idle |
| Streamed assistant deltas | test_turn_runtime.py | test_text_only_response |
| Tool lifecycle events | test_turn_runtime.py | test_event_ordering |
| Session resume | test_session.py | test_resume_after_close |
| History replay | test_session.py | test_two_turns_replay_history |
| Career context | test_employment_host.py | test_context_contains_selected_track |
| Cancellation | test_turn_runtime.py | test_cancellation_while_waiting_for_tool |
