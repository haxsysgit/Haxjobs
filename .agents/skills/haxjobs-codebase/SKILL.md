# HaxJobs Codebase Skill

This skill teaches AI assistants how to develop in the HaxJobs codebase. Always load before making changes to any file under `src/haxjobs/`.

---

## Architecture — Four Layers, Strict Downward Dependencies

```
interfaces/   (CLI, terminal, setup)
    ↓
employment/   (host, tools, store, context, actions, schema)
    ↓
agent_core/   (session, turn, messages, tools, errors, events)
    ↓
model/        (client protocol, OpenAI adapter, fake client, types)
```

### Import rules

1. **model/** imports nothing above it — only `config` and stdlib
2. **agent_core/** imports only `model/` — NEVER `employment/`, NEVER `interfaces/`
3. **employment/** imports `agent_core/` and `model/` — NEVER `interfaces/`
4. **interfaces/** imports everything — it's the outermost layer

Violating these rules is a merge blocker. Every layer has `__all__` in `__init__.py` defining its public API. Other layers import from that public API, never from internal modules.

### Dependency verification

```bash
# agent_core must never import employment or interfaces
grep -r "from haxjobs.employment\|from haxjobs.interfaces" src/haxjobs/agent_core/ && echo "LAYER VIOLATION" || echo "clean"

# employment must never import interfaces
grep -r "from haxjobs.interfaces" src/haxjobs/employment/ && echo "LAYER VIOLATION" || echo "clean"
```

---

## Key files — what each one does

### model/ — Provider boundary

| File | Responsibility | Size |
|---|---|---|
| `types.py` | Pydantic models: ModelRequest, ModelResponse, ModelStreamEvent, ToolCall, ToolSchema | 125 lines |
| `client.py` | OpenAIModelClient — wraps openai, reads provider config from `~/.haxjobs/haxjobs.toml` | 270 lines |
| `fake.py` | FakeModelClient — deterministic, no network, records requests, supports stream replay | 100 lines |

### agent_core/ — Domain-free runtime

| File | Responsibility | Size |
|---|---|---|
| `tools.py` | ToolRegistry, ToolDefinition, ToolExecutionContext, EffectKind — explicit registration, no auto-discovery | 175 lines |
| `messages.py` | 4 canonical message types (User, Assistant, ToolCall, ToolResult), project_messages() to provider format | 175 lines |
| `turn.py` | `run_turn()` — streaming model + tool loop, 5-step max, cancellation, durable tool persistence | 1182 lines |
| `session.py` | AgentSession — prompt queue, busy policy, turn lifecycle, measurement, settlement, resume | 696 lines |
| `session_store.py` | SessionStore — append-only SQLite for sessions, messages, configuration, measurements | 285 lines |
| `errors.py` | `safe_error()` — maps internal failure categories to stable text, never leaks exception text | 65 lines |
| `live_events.py` | LiveEvent, LiveEventType — content-bearing events for the terminal interface | 65 lines |

### employment/ — Career domain

| File | Responsibility | Size |
|---|---|---|
| `host.py` | EmploymentHost — wires CareerStore → system_prompt, context_messages, registered tools | 120 lines |
| `store.py` | CareerStore — SQLite store for persons, tracks, skills, evidence, gaps, constraints, jobs, assessments, decisions | 615 lines |
| `schema.py` | Pydantic models: Person, CareerTrack, Skill, EvidenceItem, Job, JobAssessment, JobDecision, ConstraintCheck | 180 lines |
| `context.py` | build_system_prompt(), build_career_context() — assembles volatile context from CareerStore | 185 lines |
| `tools.py` | build_employment_tool_registry() — registers get_job, inspect_job_source, record_job_assessment, record_job_decision | 395 lines |
| `job_actions.py` | Plain functions: get_job, record_assessment, record_decision, inspect_job_source, normalise_description | 315 lines |
| `job_source.py` | JobSourceFetcher — HTTPS-only, no redirects, host allowlist, 512KB/12K char limits, DNS rebinding comment | 560 lines |
| `fixtures.py` | CareerFixture, JobFixture — Pydantic contracts for frozen test/seed data | 115 lines |
| `migration.py` | migrate_career_fixture() — one-way CareerFixture → CareerStore migration | 215 lines |
| `composition.py` | compose_session() — wires everything together: model, store, host, session scope, resume | 220 lines |
| `identifiers.py` | make_stable_id() — SHA-256 based deterministic ID generation | 15 lines |
| `errors.py` | IdempotencyConflict — typed error for duplicate tool_call_id with different payload | 10 lines |

### interfaces/ — Entry points

| File | Responsibility | Size |
|---|---|---|
| `cli.py` | argparse CLI — haxjobs, haxjobs chat, haxjobs setup, haxjobs migrate, haxjobs profile | 220 lines |
| `terminal.py` | TerminalClient — prompt_toolkit, renders live events, handles input, cancellation, shutdown | 260 lines |
| `setup_cli.py` | run_setup() — interactive provider setup, getpass, atomic 0600 TOML write | 93 lines |
| `profile_cli.py` | Profile CLI handlers — show, migrate, track/skill/evidence/gap/constraint add | 205 lines |

### Root

| File | Responsibility | Size |
|---|---|---|
| `config.py` | Runtime paths — HAXJOBS_HOME (~/.haxjobs default), PROVIDER_CONFIG_PATH, STATE_DIR, CAREER_DB_PATH, SESSION_DB_PATH, ensure_runtime_home() | 36 lines |
| `__main__.py` | Entry for `python -m haxjobs` | 4 lines |

---

## Development rules

### No hardcoded values

- Paths come from `haxjobs.config` or are injected via constructor arguments
- Provider credentials come from `~/.haxjobs/haxjobs.toml`, never hardcoded
- Model names, API keys, base URLs all come from provider config
- Timeouts are module-level constants with clear names (`_TIMEOUT = 15.0`)
- Exception: tests may hardcode synthetic values. Migration may hardcode the developer's personal skill taxonomy (single-user tool).

### How to add a tool

1. Define input/output Pydantic models in `employment/tools.py`
2. Define a handler function (async, takes `(input_obj, ToolExecutionContext)`)
3. Register with `registry.register(ToolDefinition(...))` in `build_employment_tool_registry()`
4. Add the plain Python action to `employment/job_actions.py`
5. Add store methods to `employment/store.py` if new tables are needed
6. Add schema models to `employment/schema.py`
7. Add the tool name to the active tuple

### How to add a new layer capability

1. Does it change the model boundary? → `model/`
2. Does it change the conversation loop? → `agent_core/`
3. Does it change what Hax knows about the user? → `employment/`
4. Does it change the CLI/terminal? → `interfaces/`

### Testing

- `PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/`
- 290 tests, all pass
- Test isolation: set `HAXJOBS_HOME` to `tmp_path`, use monkeypatched `HAXJOBS_CAREER_DB` for subprocess tests
- Fake model for conversation tests, OpenAI client mocked with `autospec=True` for streaming tests
- PTY tests use pexpect for terminal interaction

### Verification before commit

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests scripts -name '*.py')
uv lock --check
git diff --check
```

---

## Code quality guidelines

### Single responsibility per module

Each file under `agent_core/` and `employment/` does exactly one thing. The module docstring states:
- What it does (responsibilities)
- What it does NOT do (explicit boundaries)

### No duplication

- Settlement logic is shared via a private helper, not copied
- TurnResult construction uses a builder, not 15+ identical calls
- Error mapping goes through `safe_error()` — one choke point
- `normalise_description()` is shared by job import and source inspection

### Readable names

- Classes: `AgentSession`, `CareerStore`, `ToolRegistry`, `EmploymentHost`
- Functions: `run_turn()`, `compose_session()`, `build_employment_tool_registry()`
- No abbreviations: `tool_call_id` not `tcid`, `assessment_id` not `asmt_id`
- Builder names: `_TurnResultBuilder`, `_MessageProjector` — private, descriptive

### Safe at trust boundaries

- `safe_error()` maps all internal failures to stable text
- Tool error codes are allowlisted via `SAFE_TOOL_CODES`
- `normalize_tool_code()` returns "tool_failed" for unknown codes
- Provider credentials are never logged or exposed in events
- Exception text never enters TurnResult, LiveEvent, or provider messages
- `JobSourceFetcher` validates host before connecting, uses HTTPS only, no redirects

---

## Known smells (to fix, not emulate)

| Smell | Where | Plan |
|---|---|---|
| Long Method | `turn.py:run_turn()` (1182 lines) | Plan 009 extracts TurnResultBuilder |
| Duplicated Code | `session.py` settlement paths | Plan 009 extracts shared helper |
| Mutable Closure State | `messages.py:project_messages()` | Plan 009 replaces with MessageProjector class |
| Hardcoded personal skills | `migration.py:_KNOWN_SKILLS` | Acceptable (single-user tool) |
| Three-layer wrapping | `tools.py` → `job_actions.py` → `store.py` | Deliberate design (test isolation) |

---

## Deferred capabilities

These are explicitly NOT built yet. Do not add them without a plan:

| Capability | Trigger to add |
|---|---|
| Context compaction | When multi-turn exceeds 75% of context window |
| Token budget tracking | When costs become measurable |
| RunContext/resume mid-workflow | When workflows need checkpoints |
| Parallel tool dispatch | When 10+ evaluations bottleneck |
| Provider fallback cascade | When DeepSeek has reliability problems |
| Conversation loop (Heronic) | When interactive chat needs multi-turn awareness |
| Skills/procedures | When repeated tool sequences become patterns |
| Subagent delegation | When parallel scraping or evaluation is needed |
| Discovery engine | When job search automation is next |
| Outreach/application | Never without explicit user approval |
