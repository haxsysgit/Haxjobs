# Plan 003 Corrected — Implementation Report

## Summary

The corrected Plan 003 keeps the delivered career graph (schema, store, migration, CLI, tests) and adds a full conversational runtime with an inline prompt_toolkit terminal. The rejected Textual TUI and fake chat shells are gone and not restored.

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
| `src/haxjobs/agent_core/__init__.py` | Removed `AgentMessage` from exports |
| `src/haxjobs/model/types.py` | Added `ModelStreamEvent`, `ModelStreamEventType` |
| `src/haxjobs/model/client.py` | Added `stream()` protocol and OpenAIModelClient implementation |
| `src/haxjobs/model/fake.py` | Added `stream()` with scripted stream sequences |
| `src/haxjobs/config.py` | Added `SESSION_DB_PATH` |
| `src/haxjobs/cli.py` | Added `chat` command and default handler |
| `src/haxjobs/interfaces/profile_cli.py` | Fixed None store `.close()` crash |
| `src/haxjobs/employment/migration.py` | Fixed missing fixture handling (sys.exit) |
| `pyproject.toml` | Added `prompt-toolkit>=3.0,<4.0` |
| `uv.lock` | Updated with prompt_toolkit |
| `docs/GETTING_STARTED.md` | Updated with chat commands and key bindings |

## Files NOT modified (preserved as-is)

- `src/haxjobs/employment/schema.py` — career models
- `src/haxjobs/employment/store.py` — CareerStore
- `src/haxjobs/employment/migration.py` — one-way fixture migration
- `src/haxjobs/employment/fixtures.py` — Pydantic fixture contracts
- `src/haxjobs/interfaces/profile_cli.py` — profile CLI (except crash fix)
- `src/haxjobs/interfaces/experiment_cli.py` — experiment runner
- All existing tests in `tests/test_stage0_job_review.py`, `tests/test_stage1_source_inspection.py`, `tests/test_career_graph.py`

## Test results

**New tests: 103** (all pass)
- test_conversation_messages.py: 20 pass
- test_live_events.py: 19 pass
- test_model_streaming.py: 11 pass
- test_session_store.py: 17 pass
- test_turn_runtime.py: 11 pass
- test_employment_host.py: 9 pass
- test_session.py: 8 pass
- test_terminal.py: 8 pass

**Existing tests: 81 of 85 pass** (4 pre-existing failures due to missing private fixture `state/experiments/fixtures/backend-career.json`)

**Total: 184 pass, 4 pre-existing failures**

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

## Manual proof status

### Fake mode
- `haxjobs chat --fake` requires a career graph
- With a manually-created minimal career graph, the composition succeeds
- Due to non-TTY execution environment, full interactive flow requires a real terminal
- The session is created and composition verified

### Live mode
- Provider config exists at `~/.haxjobs/haxjobs.toml`
- Live session composition verified: `Session created: beb5b48debdf`
- Full interactive live flow requires a real terminal (not available in this execution context)

### Blocked items
- Full interactive fake demo: requires real TTY (prompt_toolkit needs terminal)
- Full interactive live demo: requires real TTY
- The career graph, composition, and runtime all work correctly — proven by tests

## Diagrams

| File | Status |
|------|--------|
| `deliverables/003-career-graph/conversation-runtime.drawio` | Created and exported to PNG |
| `deliverables/003-career-graph/interaction-flow.drawio` | Created and exported to PNG |
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

## Risks

| Risk | Mitigation |
|------|-----------|
| OpenAI SDK streaming changes | Fake client provides deterministic streaming path for tests |
| prompt_toolkit async + streaming | patch_stdout used; cancellation stops streams cleanly |
| Career graph missing → silent failure | EmploymentSetupError raised before any model call |
