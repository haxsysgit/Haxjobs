# Plan 003 Corrected - Final Implementation Report

## Summary

The corrected Plan 003 keeps the delivered career graph (schema, store, migration, CLI, tests) and adds a full conversational runtime with an inline prompt_toolkit terminal. The rejected Textual TUI and fake chat shells are gone and not restored.

Repair round 1 applied 12 accepted reviewer findings. Repair round 2 applied 15 accepted reviewer findings from four independent DeepSeek V4 Pro reviewers. Repair round 3 applied pre-final hardening to one accepted lifecycle defect cluster: detached pending tasks, reused cancel event, and terminal shutdown race. Repair round 4 (this commit) applies two accepted correctness blockers found by a final release-gate reviewer: double TURN_INTERRUPTED emission on pre-model cancellation and tool dispatch vs cancel race condition.

## Files created

| File | Purpose |
|------|---------|
| `src/haxjobs/agent_core/messages.py` | Canonical User, Assistant, ToolCall, ToolResult messages |
| `src/haxjobs/agent_core/live_events.py` | Content-bearing LiveEvent types for the terminal |
| `src/haxjobs/agent_core/session_store.py` | Append-only SQLite session persistence |
| `src/haxjobs/agent_core/turn.py` | Domain-free bounded streaming turn runtime |
| `src/haxjobs/agent_core/session.py` | AgentSession with prompt, subscribe, abort, resume, close |
| `src/haxjobs/employment/context.py` | Volatile career context assembly from CareerStore |
| `src/haxjobs/employment/host.py` | EmploymentHost connecting runtime to career data |
| `src/haxjobs/employment/composition.py` | Composition root — wires provider, store, host, session |
| `src/haxjobs/interfaces/terminal.py` | Inline prompt_toolkit terminal client |
| `tests/test_conversation_messages.py` | 20 tests |
| `tests/test_live_events.py` | 19 tests |
| `tests/test_model_streaming.py` | 11 tests |
| `tests/test_session_store.py` | 17 tests |
| `tests/test_turn_runtime.py` | 20 tests |
| `tests/test_employment_host.py` | 9 tests |
| `tests/test_session.py` | 18 tests |
| `tests/test_terminal.py` | 14 tests |
| `tests/test_terminal_pty.py` | 2 tests |

## Files modified

| File | Change |
|------|--------|
| `src/haxjobs/agent_core/types.py` | Removed unused `AgentMessage` class |
| `src/haxjobs/model/types.py` | Added `ModelStreamEvent`, `ModelStreamEventType`, `tool_calls_unsafe` |
| `src/haxjobs/model/client.py` | Added `stream()` protocol and OpenAIModelClient implementation; reject unsafe tool calls; removed dead `completed_tool_calls` set |
| `src/haxjobs/model/fake.py` | Added `stream()` with repeat mode and per-event delay; `responses` parameter now optional |
| `src/haxjobs/config.py` | Added `SESSION_DB_PATH` |
| `src/haxjobs/cli.py` | Added `chat` command, `--fake-delay` option; catch `ValueError` for unknown resume IDs; bare `haxjobs` resumes latest session |
| `src/haxjobs/agent_core/turn.py` | Added `QUEUED` exit reason; removed dead `request = ModelMessage`; catch `active_schemas()` ValueError |
| `src/haxjobs/agent_core/session.py` | `resume()` made synchronous; `CanonicalParseError` raises on corrupt messages; `close()` with cleanup callbacks; pending-turn race fixed (no `_busy=False` gap); abort timing fixed (honour abort before `clear()`); host/context setup failure caught with TURN_FAILED + SESSION_SETTLED |
| `src/haxjobs/interfaces/terminal.py` | Non-blocking prompt dispatch; renders replacement notice; cooperative shutdown with grace wait; safe task exception handling; calls `session.close()` |
| `src/haxjobs/interfaces/profile_cli.py` | Fixed None store `.close()` crash (kept — scope exception for user-facing crash) |
| `src/haxjobs/employment/migration.py` | Fixed missing fixture handling: `sys.exit(1)` instead of silent return (kept — scope exception) |
| `src/haxjobs/employment/store.py` | Added `db_path.chmod(0o600)` for file-backed databases; conditional WAL for `:memory:` |
| `src/haxjobs/employment/composition.py` | Removed `await` from `resume()` call; added cleanup callback for CareerStore; added `fake_delay_ms` parameter; `_fake_model()` uses `repeat=True` |
| `pyproject.toml` | Added `prompt-toolkit>=3.0,<4.0` |
| `uv.lock` | Updated with prompt_toolkit |
| `docs/GETTING_STARTED.md` | Updated with chat commands and key bindings |
| `deliverables/003-career-graph/` | Updated plan.md, README, report, review-ledger, manual-proof.md |

## Files NOT modified (preserved as-is)

- `src/haxjobs/employment/schema.py` — career models
- `src/haxjobs/employment/fixtures.py` — Pydantic fixture contracts
- `src/haxjobs/interfaces/experiment_cli.py` — experiment runner
- All existing tests in `tests/test_stage0_job_review.py`, `tests/test_stage1_source_inspection.py`, `tests/test_career_graph.py` (except 2 new CareerStore permission tests)

## Test results

**Full suite: 217 passed, 0 failures**

All 217 tests pass when the private career fixture (`state/experiments/fixtures/backend-career.json`) is present. The fixture is an untracked local file — not committed to the repository.

Tests added or changed by corrected Plan 003: 132
Tests present at baseline `ae1dbce`: 85
Total: 217

| Test file | Count |
|-----------|-------|
| test_conversation_messages.py | 20 |
| test_live_events.py | 19 |
| test_model_streaming.py | 11 |
| test_session_store.py | 17 |
| test_turn_runtime.py | 20 |
| test_employment_host.py | 9 |
| test_session.py | 18 |
| test_terminal.py | 14 |
| test_terminal_pty.py | 2 |
| test_career_graph.py | 23 |
| test_stage0_job_review.py | 27 |
| test_stage1_source_inspection.py | 37 |

## Repair round 2 fixes applied (15 findings)

| # | Finding | Source | Fix applied |
|---|---------|--------|-------------|
| 1 | CRITICAL: AgentSession.resume async with no await | Reviewers B,D | Made `resume()` synchronous; updated call site in `composition.py`; removed `await` from tests |
| 2 | Pending-turn race (`_busy` cleared before pending task scheduled) | Reviewer D (MODERATE) | `_busy` stays True when chaining pending; only cleared when no pending |
| 3 | `_cancel_event.clear()` loses pre-turn abort signal | Reviewer C (HIGH) | Moved `clear()` after user message persistence; check event before clearing and return INTERRUPTED |
| 4 | Terminal shutdown — no grace wait before force-cancel | Reviewer D (MODERATE) | Added bounded 1s grace wait via `asyncio.wait_for`; force-cancel only remaining tasks; safe done callbacks |
| 5 | Pending message replacement notification invisible | Reviewers B,C,D | Terminal renders `USER_MESSAGE_ACCEPTED` text when `turn_id` is empty (replacement notice) |
| 6 | PTY "escape during streaming" test false positive | Reviewer D (MODERATE) | Added `--fake-delay` option and delayed fake model (150ms per-event); genuine mid-stream interruption |
| 7 | `test_cancellation_during_text_streaming` never cancels | Reviewer D (MINOR) | Replaced with real mid-stream test using delayed fake model + cancel_event.set() |
| 8 | CareerStore has no explicit 0600 permissions | Reviewer C (MODERATE) | Added `db_path.chmod(0o600)` for file-backed DBs; regression test included; `:memory:` skipped |
| 9 | Session/career stores leak on exit | Reviewer C (MODERATE) | Added `AgentSession.close()` with cleanup callbacks; CareerStore closed via callback; terminal calls `session.close()` |
| 10 | `active_schemas()` ValueError uncaught; host setup not caught | Reviewer C (LOW), Plan | Catch `active_schemas` ValueError → MODEL_FAILED; catch host/context setup exceptions → TURN_FAILED + SESSION_SETTLED |
| 11 | Corrupted canonical messages silently dropped | Reviewer B (MODERATE) | `CanonicalParseError` raised on corrupt messages; caught in `_run_turn` → TURN_FAILED + SESSION_SETTLED |
| 12 | Fake chat second-turn exhaustion | Reviewer B (MODERATE) | Added `repeat=True` mode to `FakeModelClient`; `_fake_model()` uses repeat mode |
| 13 | Busy input returns INTERRUPTED | Reviewer B (MINOR) | Added `QUEUED` exit reason; `prompt()` returns QUEUED when busy |
| 14 | Dead code: `request = ModelMessage`, `completed_tool_calls` | Reviewer B (MODERATE) | Removed both dead variables |
| 15 | Report test counts stale/false | Reviewer A (MEDIUM) | Updated to actual `pytest --collect-only` counts (209 total) |

## Repair round 4: Release-gate correctness blockers

Two correctness blockers found by a final release-gate reviewer (Reviewer B, final):

| # | Finding | Fix applied |
|---|---------|-------------|
| 1 | Double `TURN_INTERRUPTED` — pre-model cancellation emitted once in loop, again in final block | Removed the emit inside the `while`-loop pre-model cancel check; final block now handles the single emission |
| 2 | Tool dispatch vs cancel race — `cancel_task in done or dispatch_task not in done` discarded successful dispatch when both completed same-tick | Changed condition to `dispatch_task not in done` so successful dispatch always wins the race |

Two deterministic tests added:
- `test_pre_model_cancellation_emits_exactly_one_turn_interrupted` — proves exactly 1 TURN_INTERRUPTED
- `test_tool_dispatch_wins_over_simultaneous_cancel` — proves canonical ToolResultMessage keeps successful output and TOOL_COMPLETED emits once

Cosmetic fixes:
- Removed dead `session_id or` branch in `composition.py` new-session creation
- Corrected comment in `client.py` from "Skip tool calls" to document actual `tool_calls_unsafe=True` emission

Test count: 217 (+2 from round 4).

---

## Repair round 3: Lifecycle defect cluster hardening

Pre-final hardening fixing one accepted defect cluster from the plan:

1. AgentSession no longer reuses one cancel event — each turn in the serial loop
   gets a fresh asyncio.Event. abort() affects only the currently busy turn and
   is a no-op while idle.
2. No detached asyncio.create_task inside AgentSession — the original prompt task
   owns a serial loop (_run_serial_loop) that runs the current turn, atomically
   takes the one pending message, and repeats. _busy stays true for the entire
   chain, only cleared when no pending work remains.
3. TerminalClient tracks one owner task — yields asyncio.sleep(0) after creating
   it so the session marks itself busy before Escape is handled. Callback catches
   CancelledError explicitly via t.cancelled() check. Shutdown awaits the owner
   task (which includes all queued work) before force-cancel and session.close().
4. Owner prompt return value documented: the original prompt caller receives the
   result of the LAST turn in the chain. Secondary calls return QUEUED immediately.
5. 6 deterministic tests prove: idle abort does not poison next prompt; cancel
   current then queued successor runs with fresh event; pending work finishes
   before close; no detached task after chain; callback handles cancelled task;
   immediate Enter then Escape reaches active turn.

Files changed in round 3:
- src/haxjobs/agent_core/session.py: +126/-147 (restructure)
- src/haxjobs/interfaces/terminal.py: +41/-28 (owner task, yield, shutdown)
- tests/test_session.py: +216 (6 lifecycle tests)
- tests/test_terminal.py: +54/-6 (update tracking, callback test)

Test count: 215 (+6 from round 3).

## Repair round 4: Release-gate correctness blockers

Two correctness blockers found by a final release-gate reviewer:

1. Double `TURN_INTERRUPTED` emission on pre-model cancellation
2. Tool dispatch vs cancel race condition

Both fixed. Test count: 217 (+2 from round 4). Full suite passes twice; PTY tests pass twice;
py_compile, uv lock, git diff all clean. Two focused tests pass 5/5 repetitions.

## Scope exceptions documented

| File | Change | Reason |
|------|--------|--------|
| `src/haxjobs/employment/migration.py` | `sys.exit(1)` for missing fixture | Prevents user-facing crash in production path |
| `src/haxjobs/interfaces/profile_cli.py` | `None` guard for `.close()` | Prevents user-facing crash on incomplete store |

## Layer connections

```
TerminalClient (prompt_toolkit)
    → AgentSession.prompt() / abort() / subscribe() / close()
        → run_turn() (domain-free)
            → ModelClient.stream() (streaming provider)
            → ToolRegistry.dispatch() (validated tool execution)
            → LiveEventEmitter (terminal rendering)
        → SessionStore (persist canonical messages)
    → EmploymentHost.system_prompt() / context_messages()
        → CareerStore (read career facts)
```

## Diagrams

| File | Status |
|------|--------|
| `deliverables/003-career-graph/conversation-runtime.drawio` | Created, cleaned, exported to PNG |
| `deliverables/003-career-graph/interaction-flow.drawio` | Created, cleaned, exported to PNG |
| `deliverables/003-career-graph/career-graph-report.md` | Preserved from original delivery |
| `deliverables/003-career-graph/schema-diagram.drawio` | Preserved from original delivery |
| `deliverables/003-career-graph/schema-diagram.png` | Preserved from original delivery |

## Verification floor

```bash
# All passed
pytest tests/                                     # 217 passed
py_compile $(find src tests -name '*.py')         # clean
uv lock --check                                    # "Resolved 29 packages in 4ms"
git diff --check                                   # clean
haxjobs --help                                     # all commands listed
haxjobs chat --help                                # --new, --resume, --fake, --fake-delay, --session-db
haxjobs chat --new --fake (pipe input)             # creates session, accepts input
haxjobs chat --fake (existing DB)                  # resumes latest session
haxjobs chat --resume BADID --fake                 # prints clean "Error: Session not found: BADID"
```

## Final release gate

Implementation commit: `d6fa361`

Four fresh DeepSeek V4 Pro release reviewers independently approved the unchanged implementation commit after checking plan compliance, runtime correctness, session and employment boundaries, terminal behavior, PTY tests, docs, and deliverables.

A real configured-provider PTY run also passed outside the committed test suite:

- `haxjobs chat --new` accepted a prompt and streamed the requested response
- the process exited cleanly
- a second bare `haxjobs` launch resumed the same session ID
- only pass/fail metadata was retained under `/tmp`; career context and model output were not copied into deliverables

## Deferred work

- Context compaction
- Token budgets
- Branching conversations
- Sub-agents
- Skills and saved workflows
- Background operations
- Approval workflows
- External side effects
- Discovery, application generation, outreach
- Provider fallback, model switching
- Web or desktop UI

## Known limitations

1. Prompt_toolkit requires a real TTY for interactive mode. Pipe-based testing produces warnings.
2. `inspect_job_source` only resolves refs 49 and 328.
3. One career person and one track assumed.
4. No token tracking or context compaction.
5. Session database is file-backed, not distributed.

## Risks

| Risk | Mitigation |
|------|-----------|
| OpenAI SDK streaming changes | Fake client provides deterministic streaming path for tests |
| prompt_toolkit async + streaming | patch_stdout used; cancellation stops streams cleanly; non-blocking prompt dispatch |
| Career graph missing → silent failure | EmploymentSetupError raised before any model call |
| Truncated tool calls dispatched | `tool_calls_unsafe` flag checked before dispatch; rejected on finish_reason="length" |
| Tool cancellation blocking | dispatch_task raced against cancel_event.wait() |
| Pending turn race | `_busy` stays True across turn chains; no gap |
| Pre-turn abort signal lost | `cancel_event.clear()` delayed until after persistence; honour pre-existing abort |
| Terminal exit state loss | Cooperative abort with grace wait; force-cancel only after timeout |
