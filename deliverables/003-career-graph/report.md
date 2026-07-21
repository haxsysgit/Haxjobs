# Plan 003 Corrected — Implementation Report (Repair Round)

## Summary

The corrected Plan 003 keeps the delivered career graph (schema, store, migration, CLI, tests) and adds a full conversational runtime with an inline prompt_toolkit terminal. The rejected Textual TUI and fake chat shells are gone and not restored.

Repair round 1 applied 12 accepted reviewer findings: unsafe streaming tool calls rejected, single TURN_FAILED emission, responsive tool cancellation, pending-turn exception tracking, terminal concurrency (non-blocking prompt dispatch), tool event rendering, SESSION_STARTED emission, bare `haxjobs` resume fix, deliverable completeness, trailing whitespace cleanup, migration crash fix retained, and real PTY manual proof.

## Files created

| File | Purpose |
|------|---------|
| `src/haxjobs/agent_core/messages.py` | Canonical User, Assistant, ToolCall, ToolResult messages |
| `src/haxjobs/agent_core/live_events.py` | Content-bearing LiveEvent types for the terminal |
| `src/haxjobs/agent_core/session_store.py` | Append-only SQLite session persistence |
| `src/haxjobs/agent_core/turn.py` | Domain-free bounded streaming turn runtime |
| `src/haxjobs/agent_core/session.py` | AgentSession with prompt, subscribe, abort, resume |
| `src/haxjobs/employment/context.py` | Volatile career context assembly from CareerStore |
| `src/haxjobs/employment/host.py` | EmploymentHost connecting runtime to career data |
| `src/haxjobs/employment/composition.py` | Composition root — wires provider, store, host, session |
| `src/haxjobs/interfaces/terminal.py` | Inline prompt_toolkit terminal client |
| `tests/test_conversation_messages.py` | 20 tests |
| `tests/test_live_events.py` | 19 tests |
| `tests/test_model_streaming.py` | 11 tests |
| `tests/test_session_store.py` | 17 tests |
| `tests/test_turn_runtime.py` | 11 tests |
| `tests/test_employment_host.py` | 9 tests |
| `tests/test_session.py` | 8 tests |
| `tests/test_terminal.py` | 8 tests |

## Files modified

| File | Change |
|------|--------|
| `src/haxjobs/agent_core/types.py` | Removed unused `AgentMessage` class |
| `src/haxjobs/agent_core/runtime.py` | Removed `AgentMessage` import |
| `src/haxjobs/agent_core/__init__.py` | Removed `AgentMessage` from exports; cleaned blank line |
| `src/haxjobs/model/types.py` | Added `ModelStreamEvent`, `ModelStreamEventType`, `tool_calls_unsafe` |
| `src/haxjobs/model/client.py` | Added `stream()` protocol and OpenAIModelClient implementation; reject unsafe tool calls on finish_reason="length" |
| `src/haxjobs/model/fake.py` | Added `stream()` with scripted stream sequences |
| `src/haxjobs/config.py` | Added `SESSION_DB_PATH` |
| `src/haxjobs/cli.py` | Added `chat` command and default handler (now resumes latest session) |
| `src/haxjobs/agent_core/turn.py` | Domain-free turn runtime; responsive cancellation races cancel_event; single TURN_FAILED; rejects tool_calls_unsafe |
| `src/haxjobs/agent_core/session.py` | AgentSession; emits SESSION_STARTED; tracks pending-turn exceptions |
| `src/haxjobs/interfaces/terminal.py` | Non-blocking prompt dispatch; renders TOOL_STARTED/PROGRESS/COMPLETED/FAILED; aborts/settles on exit |
| `src/haxjobs/interfaces/profile_cli.py` | Fixed None store `.close()` crash (kept — prevents user-facing crash) |
| `src/haxjobs/employment/migration.py` | Fixed missing fixture handling: `sys.exit(1)` instead of silent return (kept) |
| `pyproject.toml` | Added `prompt-toolkit>=3.0,<4.0` |
| `uv.lock` | Updated with prompt_toolkit |
| `docs/GETTING_STARTED.md` | Updated with chat commands and key bindings (bare `haxjobs` now resumes latest) |
| `deliverables/003-career-graph/` | Updated plan.md, README, report, review-ledger, preserved career-graph artifacts |

## Files NOT modified (preserved as-is)

- `src/haxjobs/employment/schema.py` — career models
- `src/haxjobs/employment/store.py` — CareerStore
- `src/haxjobs/employment/fixtures.py` — Pydantic fixture contracts
- `src/haxjobs/interfaces/experiment_cli.py` — experiment runner
- All existing tests in `tests/test_stage0_job_review.py`, `tests/test_stage1_source_inspection.py`, `tests/test_career_graph.py`

## Test results

**Full suite: 188 passed, 0 failures**

All 188 tests pass when the private career fixture (`state/experiments/fixtures/backend-career.json`) is present. The fixture is an untracked local file — not committed to the repository.

103 new tests + 85 existing tests = 188 total.

## Repair round fixes applied

| # | Finding | Fix | Tested |
|---|---------|-----|--------|
| 1 | Truncated tool calls dispatched on finish_reason="length" | Added `tool_calls_unsafe` flag to `ModelStreamEvent`; skip/reject in client.py and turn.py | ✓ |
| 2 | Double TURN_FAILED emission | Removed inline emit from RESPONSE_FAILED/Exception handlers; single final emit | ✓ |
| 3 | Tool cancellation not responsive | Race dispatch_task against cancel_event.wait(); clean up both tasks | ✓ |
| 4 | Pending-turn fire-and-forget exceptions | Added `add_done_callback` with error logging | ✓ |
| 5 | Terminal awaits session.prompt() blocking input | Fire as non-blocking task; track tasks; abort/settle on exit | ✓ |
| 6 | Tool events not rendered | Render TOOL_STARTED, TOOL_PROGRESS, TOOL_COMPLETED, TOOL_FAILED from LiveEvents | ✓ |
| 7 | SESSION_STARTED never emitted | Emit on first turn in AgentSession._run_turn | ✓ |
| 8 | Bare `haxjobs` always creates new session | Now resumes latest session (matches `haxjobs chat`) | ✓ |
| 9 | Missing deliverable artifacts | Copied plan.md, career-graph-report.md, schema-diagram.*; updated README and report | ✓ |
| 10 | Trailing whitespace in Draw.io XML; blank __all__ line | Cleaned both .drawio files; removed blank line in __all__ | ✓ |
| 11 | Migration/profile_cli fixes | Kept — `sys.exit(1)` + None guard prevent real user-facing crash | ✓ |
| 12 | Real terminal proof through PTY | See manual-proof.md — local PTY test confirmed | ✓ |

## Layer connections

```
TerminalClient (prompt_toolkit)
    → AgentSession.prompt() / abort() / subscribe()
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
| `deliverables/003-career-graph/conversation-runtime.drawio` | Created, cleaned whitespace, exported to PNG |
| `deliverables/003-career-graph/interaction-flow.drawio` | Created, cleaned whitespace, exported to PNG |
| `deliverables/003-career-graph/career-graph-report.md` | Preserved from original delivery |
| `deliverables/003-career-graph/schema-diagram.drawio` | Preserved from original delivery |
| `deliverables/003-career-graph/schema-diagram.png` | Preserved from original delivery |

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

1. Prompt_toolkit requires a real TTY for interactive mode. Pipe-based testing is limited.
2. `inspect_job_source` only resolves refs 49 and 328.
3. One career person and one track assumed.
4. No token tracking or context compaction.
5. Session database is file-backed, not distributed.
6. Terminal PTY proof depends on local environment (see manual-proof.md).

## Risks

| Risk | Mitigation |
|------|-----------|
| OpenAI SDK streaming changes | Fake client provides deterministic streaming path for tests |
| prompt_toolkit async + streaming | patch_stdout used; cancellation stops streams cleanly; non-blocking prompt dispatch |
| Career graph missing → silent failure | EmploymentSetupError raised before any model call |
| Truncated tool calls dispatched | `tool_calls_unsafe` flag checked before dispatch; rejected on finish_reason="length" |
| Tool cancellation blocking | dispatch_task raced against cancel_event.wait() |
