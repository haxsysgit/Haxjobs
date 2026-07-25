# Plan 009: Code Quality Hardening and Architecture Discipline

> **Executor:** DeepSeek V4 Pro (writer), DeepSeek V4 Flash (reviewers)
> **Depends on:** Plan 008 DONE
> **Drift stamp:** commit `c2a4455` (v0.1.0 tag)
> **Status:** TODO
> **WARNING:** This plan is not final. The executor must compare it against live code before implementing. Deliver a completion report covering what changed, how it changed, and deliverables.

## Goal

Make the codebase maintainable for one developer returning after 6 months. Every file should be readable in one pass. Every layer boundary should be obvious. Every public API surface should be documented. No hardcoded settings outside of tests and explicit module-level constants with clear names.

## Why

The deep audit found these specific problems:

1. **`turn.py` (1182 lines):** `run_turn()` constructs `TurnResult` in 15+ places with identical 12-field dicts. The cancellation-vs-dispatch race has 4 code paths that are individually correct but collectively impossible to skim. Adding one field to `TurnResult` requires touching 15 locations. This is the #1 maintenance risk.

2. **`session.py` (696 lines):** `_run_turn()` mixes 5 concerns: persistence, measurement, settlement, event emission, and error handling. The happy path is buried in guard clauses.

3. **`messages.py`: `project_messages()`** uses a `nonlocal` mutable-state accumulator pattern that resets after tool results. Correct but fragile — adding a message kind would break the flush ordering.

4. **Missing `__init__.py` exports.** `agent_core/__init__.py` exports only tools. Session, turn, messages, errors, live_events, and session_store have no public re-export path. A developer importing from `haxjobs.agent_core` can't discover what's available.

5. **Hardcoded constants scattered across files.** `_MAX_MODEL_STEPS = 5` in `turn.py`, `max_tokens=4096`, `_EVIDENCE_CHAR_CAP = 500`, `_EVIDENCE_TOTAL_CAP = 8000`, `_MAX_BYTES`, `_MAX_VISIBLE_CHARS`, `_TIMEOUT = 15.0`. These are correct values but live in 4 different files with no central constants module.

6. **`composition.py`: `_fake_model()`** is 40 lines of inline string literals defining fake model behavior. It belongs in `model/fake.py` as a named factory function.

7. **No codebase skill.** Future assistants opening this repo have no guide for how the layers work, what the naming conventions are, where to add new tools, or what the 4-layer architecture expects.

## Scope

### In
- Extract `TurnResult` builder pattern — one `_make_result()` helper replacing 15 duplicate constructions
- Extract tool dispatch paths into separate functions (`_dispatch_tool_normal`, `_dispatch_tool_cancelled`, `_dispatch_tool_cancel_wins_race`)
- Extract settlement logic from `_run_turn()` into a dedicated `_settle_turn()` method
- Add a `constants.py` module under `agent_core/` for `_MAX_MODEL_STEPS`, `MAX_TOKENS`, and domain-free defaults
- Add a `constants.py` module under `employment/` for `EVIDENCE_CHAR_CAP`, `EVIDENCE_TOTAL_CAP`
- Move `_fake_model()` from `composition.py` to `model/fake.py` as `default_fake_model()`
- Complete `__init__.py` exports for all 4 layers
- Write `.agents/skills/haxjobs-codebase/SKILL.md`

### Out
- Adding new features
- Changing any public API signatures (TurnResult, AgentSession.prompt, ToolRegistry.dispatch, EmploymentHost)
- Refactoring CareerStore or migration (already well-structured)
- Moving files between packages
- Adding type hints beyond what already exists
- Changing test files (except to update import paths if __init__.py changes break them)

## Files

### Modify
- `src/haxjobs/agent_core/turn.py` — extract helpers, reduce duplication
- `src/haxjobs/agent_core/session.py` — extract `_settle_turn()` method
- `src/haxjobs/agent_core/__init__.py` — complete exports
- `src/haxjobs/employment/__init__.py` — complete exports
- `src/haxjobs/model/__init__.py` — complete exports
- `src/haxjobs/interfaces/__init__.py` — complete exports
- `src/haxjobs/employment/composition.py` — move `_fake_model()` out
- `src/haxjobs/model/fake.py` — add `default_fake_model()`

### Create
- `src/haxjobs/agent_core/constants.py` — domain-free defaults
- `src/haxjobs/employment/constants.py` — employment-layer defaults
- `.agents/skills/haxjobs-codebase/SKILL.md` — codebase development guide

### Do NOT modify
- `tests/` — no test changes (all refactors are internal, no API changes)
- `src/haxjobs/employment/store.py` — already clean
- `src/haxjobs/employment/tools.py` — already clean
- `src/haxjobs/agent_core/tools.py` — already clean
- `src/haxjobs/agent_core/errors.py` — already clean

## Phase 1: TurnResult builder pattern

### Task 1: Add `_make_result()` to turn.py

The current pattern (appears 15+ times):

```python
return TurnResult(
    turn_id=turn_id,
    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
    final_text=accumulated_text,
    model_steps=model_steps,
    tool_starts=tool_starts,
    new_messages=new_messages,
    safe_failure=safe_failure,
    user_message_id=user_message_id,
    model_name=captured_model_name,
    provider_name=captured_provider_name,
    usage=captured_usage,
    input_characters=input_characters,
)
```

Replace with a single builder at the bottom of `turn.py`:

```python
def _make_result(
    *,
    exit_reason: TurnExitReason,
    turn_id: str,
    final_text: str = "",
    model_steps: int = 0,
    tool_starts: int = 0,
    new_messages: list[ConversationMessage] | None = None,
    safe_failure: str = "",
    user_message_id: str = "",
    model_name: str = "",
    provider_name: str = "",
    usage: ModelUsage | None = None,
    input_characters: int = 0,
) -> TurnResult:
    return TurnResult(
        turn_id=turn_id,
        exit_reason=exit_reason,
        final_text=final_text,
        model_steps=model_steps,
        tool_starts=tool_starts,
        new_messages=new_messages or [],
        safe_failure=safe_failure,
        user_message_id=user_message_id,
        model_name=model_name,
        provider_name=provider_name,
        usage=usage,
        input_characters=input_characters,
    )
```

Then replace every `TurnResult(...)` construction in `run_turn()` with `_make_result(...)`. This is a mechanical change — identical behavior, less code.

Each call site becomes:

```python
return _make_result(
    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
    turn_id=turn_id,
    final_text=accumulated_text,
    model_steps=model_steps,
    tool_starts=tool_starts,
    new_messages=new_messages,
    safe_failure=safe_failure,
    user_message_id=user_message_id,
    model_name=captured_model_name,
    provider_name=captured_provider_name,
    usage=captured_usage,
    input_characters=input_characters,
)
```

### Task 2: Extract tool dispatch paths

`run_turn()` has 4 tool dispatch code paths (each ~40-60 lines):

1. **Normal completion** — `dispatch_task in done`, dispatch succeeded
2. **External task cancellation** — `asyncio.CancelledError` wrapping dispatch wait
3. **Cancel wins race** — `dispatch_task not in done` after `asyncio.wait`
4. **Cancel wins race (external cancel variant)** — same logic as #3 but triggered differently

Extract each into a named function in `turn.py`:

```python
async def _dispatch_tool_normal(
    dispatch_task: asyncio.Task,
    cancel_task: asyncio.Task,
    call_id: str,
    tool_name: str,
    ...
) -> tuple[dict[str, Any], float]:
    """Dispatch completed normally. Cancel the cancel-waiter, collect result."""
    ...

async def _dispatch_cancelled_before_wait(
    dispatch_task: asyncio.Task,
    cancel_task: asyncio.Task,
    ...
) -> tuple[dict[str, Any] | None, float, bool]:
    """External cancellation arrived before asyncio.wait. Collect handler outcome."""
    ...

async def _dispatch_cancel_wins_race(
    dispatch_task: asyncio.Task,
    cancel_task: asyncio.Task,
    ...
) -> tuple[dict[str, Any] | None, float, bool]:
    """Cancellation won the race. Handler may still have committed."""
    ...
```

The main loop in `run_turn()` then calls the appropriate helper and handles the result uniformly.

## Phase 2: Extract settlement logic from session.py

### Task 3: Extract `_settle_turn()` from `_run_turn()`

Currently `_run_turn()` has 3 sequential persistence stages (measurement → settlement → terminal event) that are ~60 lines of try/except guards. Extract into a private method:

```python
def _settle_turn(
    self,
    turn_id: str,
    started_at: str,
    started_mono: float,
    result: TurnResult,
) -> TurnResult:
    """Persist measurement, mark settled, publish terminal event. One cohesive step."""
    ...
```

The caller in `_run_turn()` becomes:

```python
result = await run_turn(...)
return self._settle_turn(turn_id, started_at, started_mono, result)
```

The existing `_settle_failed_turn()` method handles the pre-model failure path and should remain separate — it handles a different code path (no model call happened) and has different invariants.

## Phase 3: Centralize constants

### Task 4: Create `agent_core/constants.py`

```python
"""Domain-free constants — limits, caps, and default values."""

MAX_MODEL_STEPS = 5
MAX_TOKENS = 4096
MAX_TOOL_RESULT_CHARS = 12_000
```

Update `turn.py` to import from here. Update `tools.py` default `ToolDefinition.max_result_chars` to reference `MAX_TOOL_RESULT_CHARS`.

### Task 5: Create `employment/constants.py`

```python
"""Employment-layer constants — evidence caps, source limits, timeout."""

EVIDENCE_CHAR_CAP = 500
EVIDENCE_TOTAL_CAP = 8_000
JOB_SOURCE_MAX_BYTES = 512 * 1024
JOB_SOURCE_MAX_VISIBLE_CHARS = 12_000
JOB_SOURCE_TIMEOUT = 15.0
```

Update `context.py` and `job_source.py` to import from here.

## Phase 4: Move fake model factory

### Task 6: Move `_fake_model()` to `model/fake.py`

`composition.py: _fake_model()` is 40 lines that belong in the model layer. Move it to `model/fake.py` as `default_fake_model()`:

```python
def default_fake_model(delay_ms: float = 0) -> FakeModelClient:
    """A single-turn fake model for CLI --fake mode and tests."""
    ...
```

Update `composition.py` to import and call `default_fake_model()`.

## Phase 5: Complete __init__.py exports

### Task 7: Complete public API surfaces

Each `__init__.py` should re-export the public names a caller is expected to use. Private helpers (prefixed with `_`) remain file-local.

**`agent_core/__init__.py`:**

```python
from haxjobs.agent_core.tools import EffectKind, ToolDefinition, ToolExecutionContext, ToolRegistry
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.turn import TurnExitReason, TurnResult, run_turn
from haxjobs.agent_core.messages import (
    UserMessage, AssistantMessage, ToolCallMessage, ToolResultMessage,
    ConversationMessage, project_messages,
)
from haxjobs.agent_core.errors import safe_error, safe_tool_error, SAFE_ERROR_TEXT
from haxjobs.agent_core.live_events import LiveEvent, LiveEventType, LiveEventEmitter
```

**`employment/__init__.py`:**

```python
from haxjobs.employment.host import EmploymentHost, EmploymentSetupError
from haxjobs.employment.store import CareerStore
from haxjobs.employment.schema import (
    Person, CareerTrack, Skill, EvidenceItem, SkillGap,
    HardConstraint, Preference, Job, JobAssessment, JobDecision,
)
from haxjobs.employment.tools import build_employment_tool_registry
from haxjobs.employment.composition import compose_session
from haxjobs.employment.job_actions import (
    get_job, record_assessment, record_decision,
    get_latest_assessment, get_latest_decision, import_job_from_fixture,
)
```

**`model/__init__.py`:**

```python
from haxjobs.model.client import ModelClient, OpenAIModelClient
from haxjobs.model.fake import FakeModelClient, default_fake_model
from haxjobs.model.types import (
    ModelMessage, ModelRequest, ModelResponse, ModelFailure,
    ModelUsage, ModelStreamEvent, ModelStreamEventType,
    ToolSchema, ToolCall,
)
```

**`interfaces/__init__.py`:**

```python
from haxjobs.interfaces.terminal import TerminalClient
from haxjobs.interfaces.setup_cli import run_setup
```

### Task 8: Verify no import breakage

After updating `__init__.py` files, update any callers that use the long import path to use the public re-export. But do NOT break backward compatibility — the long paths must still work. This is purely additive.

Run the full test suite. If a test imports from a long path that still exists, it passes unchanged.

## Phase 6: Write the haxjobs-codebase skill

### Task 9: Create `.agents/skills/haxjobs-codebase/SKILL.md`

This skill is loaded by future assistants when working on HaxJobs. It must cover:

1. **What HaxJobs is** (one paragraph)
2. **The 4-layer architecture** with a diagram (ASCII art):
   - `interfaces/` — CLI, terminal, setup (imports everything below)
   - `employment/` — career logic, host, store, tools, context (imports agent_core + model)
   - `agent_core/` — domain-free runtime: session, turn, tools, messages (imports model only)
   - `model/` — provider boundary, types (imports config only)

3. **How to add a new tool:**
   - Define Pydantic input/output models in `employment/tools.py`
   - Write the handler wrapping a function in `job_actions.py`
   - Register it in `build_employment_tool_registry()`
   - Tool handlers receive `ToolExecutionContext` and return `{"ok": True, "data": {...}}`

4. **How to add a new CLI command:**
   - Add argparse subparser in `cli.py`
   - Handler function in `interfaces/`
   - Always call `ensure_runtime_home()` before real work
   - Use `--fake` flag for no-network testing

5. **How to add a DB table:**
   - Add DDL to `CareerStore` or `SessionStore`
   - Add Pydantic model to `employment/schema.py`
   - Add CRUD methods to the store class
   - Add a migration in `_migrate_job_columns()` pattern

6. **Naming conventions:**
   - Public classes: PascalCase (`EmploymentHost`, `CareerStore`)
   - Public functions: snake_case (`compose_session`, `build_system_prompt`)
   - Private module-level: `_leading_underscore`
   - Constants: `UPPER_SNAKE_CASE`
   - DB tables: `snake_case`
   - Pydantic models: PascalCase matching table names

7. **Where to find things:**
   - "I need to change how sessions work" → `agent_core/session.py`, `agent_core/session_store.py`
   - "I need to add job evaluation logic" → `employment/job_actions.py`, `employment/tools.py`
   - "I need to change the terminal UI" → `interfaces/terminal.py`
   - "I need to add a provider" → `model/client.py`

8. **Safety rules:**
   - Never expose raw exception text in TurnResult or LiveEvent — use `safe_error()`
   - Tool results go through `_normalize_tool_result()` before being projected to the model
   - Career context is injected per-turn, never stored in session history
   - Dev mode: `HAXJOBS_HOME` separates checkout state from installed state
   - No hardcoded personal details anywhere except tests

9. **Verification commands:**
   ```bash
   PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
   PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
   uv lock --check
   git diff --check
   ```

10. **Key design decisions recorded in discussion/:**
    - `discussion/001-hax-goal-and-run-lifecycle.md`
    - `discussion/004-minimal-job-native-harness.md`
    - `discussion/006-pi-inspired-haxjobs-architecture.md`
    - `discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md`

Keep the skill under 200 lines. Tone: sharp, practical, no fluff.

## Phase 7: Verification

### Task 10: Full verification

```bash
# Full test suite — must still pass 290+ tests
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/

# Verify all __init__.py imports work
PYTHONPATH=src:. uv run -- python3 -c "
from haxjobs.agent_core import AgentSession, SessionStore, TurnResult, TurnExitReason
from haxjobs.employment import EmploymentHost, CareerStore, compose_session
from haxjobs.model import ModelClient, OpenAIModelClient, FakeModelClient
print('All imports OK')
"

# Compile check
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')

# uv lock
uv lock --check

# git diff
git diff --check
```

## Deliverables

After implementation, create `deliverables/009-code-quality/` with:
- `plan.md` — copy of this plan
- `report.md` — implementation report: line count before/after for turn.py, session.py, test count
- `README.md` — deliverable index
- `skill-preview.md` — the first 30 lines of the haxjobs-codebase skill for quick review
