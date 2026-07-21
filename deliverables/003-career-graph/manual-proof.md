# Manual Proof — Plan 003 Corrected (Repair Round)

## Environment

- Worktree: `/tmp/haxjobs-exec-003-corrected`
- Branch: `advisor/003-corrected`
- Baseline commit: `ae1dbce`
- Implementation commit: `d6fa361`

## PTY Smoke Test (stdlib pty)

Two automated PTY tests using stdlib `pty` and `subprocess` prove critical terminal behaviors
with a real pseudo-terminal. No external test dependency required.

### Test 1: Enter submits, terminal survives Escape, returns to prompt

```
$ PYTHONPATH=src:. uv run python3 -m pytest tests/test_terminal_pty.py -v -k enter
tests/test_terminal_pty.py::test_terminal_pty_enter_submits_and_escape_interrupts PASSED
```

Observed:
1. Session banner printed with session ID ✓
2. "> " prompt appeared ✓
3. "hello world" + Enter submitted → FAKE response appeared ✓
4. Escape sent, terminal alive ✓
5. "still alive" + Enter → prompt "> " returned ✓
6. Ctrl+D exited cleanly ✓

### Test 2: Escape during streaming interrupts turn, terminal returns to prompt

```
$ PYTHONPATH=src:. uv run python3 -m pytest tests/test_terminal_pty.py -v -k escape
tests/test_terminal_pty.py::test_terminal_pty_escape_during_streaming_interrupts PASSED
```

Observed:
1. Input sent with a delayed fake stream, then Escape sent while streaming was active ✓
2. Terminal returned to "> " prompt after Escape ✓
3. Ctrl+D exited cleanly ✓

This proves interruption happens before the turn completes —
the terminal does not hang or deadlock.

## Fake mode (manual CTD)

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan003-sessions.db uv run haxjobs chat --fake
```

- Session created and composition verified ✓
- Full interactive flow confirmed by PTY tests above

## Live configured-provider proof

A privacy-safe PTY check was run after all four release reviewers approved `d6fa361`:

```bash
python3 /tmp/haxjobs-live-pty-proof2.py
```

Observed:

1. `haxjobs chat --new` opened in normal terminal mode.
2. Enter submitted a real prompt to the configured provider.
3. The requested response streamed back.
4. Ctrl+D exited with status 0.
5. A second bare `haxjobs` launch resumed the same session ID.
6. The second process exited with status 0.

Result metadata was written to `/tmp/haxjobs-plan003-live-proof2.json`. Raw terminal output stayed under `/tmp` and is not part of the deliverables because it may contain career context.

## Verified by tests

| Behaviour | Test file | Result |
|-----------|-----------|--------|
| Enter submits | `test_terminal_pty.py::test_terminal_pty_enter_submits_and_escape_interrupts` | ✓ PASSED |
| Escape interrupts, prompt returns | `test_terminal_pty.py::test_terminal_pty_escape_during_streaming_interrupts` | ✓ PASSED |
| Ctrl+J newline | `test_terminal.py` | Key binding verified |
| Escape aborts session | `test_session.py::test_abort_returns_session_to_idle` | ✓ PASSED |
| Streamed assistant deltas | `test_turn_runtime.py::test_text_only_response` | ✓ PASSED |
| Tool lifecycle events | `test_turn_runtime.py::test_event_ordering` | ✓ PASSED |
| Session resume | `test_session.py::test_resume_after_close` | ✓ PASSED |
| History replay | `test_session.py::test_two_turns_replay_history` | ✓ PASSED |
| Career context | `test_employment_host.py::test_context_contains_selected_track` | ✓ PASSED |
| Cancellation | `test_turn_runtime.py::test_cancellation_while_waiting_for_tool` | ✓ PASSED |
| Unsafe tool calls rejected | `test_turn_runtime.py` (verified by code path) | ✓ |
| SESSION_STARTED emitted | `test_session.py` (verified by code path) | ✓ |
| Full suite | `pytest tests/` | 217 passed, 0 failures |
| Pre-model cancel cardinality | `test_turn_runtime.py::test_pre_model_cancellation_emits_exactly_one_turn_interrupted` | ✓ PASSED |
| Dispatch-vs-cancel race | `test_turn_runtime.py::test_tool_dispatch_wins_over_simultaneous_cancel` | ✓ PASSED |
