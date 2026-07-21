# Plan 004: Saved Job Assessment and Durable Tool Effects

| Key | Value |
|----|-----|
| **Plan ID** | 004 |
| **Title** | Saved Job Assessment and Durable Tool Effects |
| **Design baseline** | `0c412b0` |
| **Depends on** | Plan 003 corrected DONE at `d6fa361` |
| **Status** | TODO |
| **Priority** | P1 |

---

## Executor warning

This plan is not final just because it is written down.

Before editing code, compare every instruction against the live repository at baseline `0c412b0`. Read the source, tests, imports, and current dependency lock. If the plan disagrees with working code, stop and report the drift. Do not silently adapt. Do not preserve stale behavior through compatibility wrappers.

The writer must read these files first:

1. `AGENTS.md`
2. `plans/003-career-graph-schema.md` (the corrected version)
3. `plans/README.md`
4. `discussion/004-minimal-job-native-harness.md`
5. `discussion/006-pi-inspired-haxjobs-architecture.md`
6. `discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md`
7. `docs/harness-primitives/03-tool-interface.md`
8. `docs/harness-primitives/05-durable-state.md`
9. `docs/harness-primitives/08-verification-and-observability.md`
10. `docs/HAXJOBS.md`
11. this plan in full

Then inspect every file under `src/haxjobs/agent_core/`, `src/haxjobs/employment/`, `src/haxjobs/model/`, `src/haxjobs/interfaces/`, `tests/`, and `pyproject.toml`. Treat current code at `0c412b0` as authority.

---

## Drift and status

| Check | Status |
|-----|------|
| Baseline commit | `0c412b0` |
| Expected pass count | 217 (after the controller copies the approved private fixture and isolated DB prerequisites) |
| CLI subprocess isolation | Already fixed at `0c412b0`; do not reimplement |
| `src/haxjobs/interfaces/tui.py` | absent (deleted in Plan 003 correction) |
| `textual` in deps | absent |
| Real career DB | operator cleaned, backed up, rebuilt outside git |
| Profile drafts in worktree | unrelated, out of scope |

Any mismatch from 217 passed is environment drift (missing private fixture, missing isolated DB). Preflight tests may show fewer passes in an unprepared worktree. Do not describe that as a baseline product failure.

---

## Purpose

Build the first real state changing employment workflow through the conversational runtime:

```text
user asks about a saved job
  -> Hax loads normalized saved job from employment store
  -> may inspect trusted source if evidence is thin
  -> compares with active career track and evidence
  -> records a typed assessment
  -> responds naturally
  -> later turn or session can retrieve that assessment
```

This is the first call path where an employment tool writes durable state, the session persists tool call and tool result messages at the correct boundaries, and the runtime can resume with dangling calls detected.

---

## Architecture invariants

These are release gates. No phase is done until every invariant holds.

1. **Layer ownership unchanged.** `model` knows no employment. `agent_core` knows no employment. `employment` owns Hax identity, career logic, and employment tools. `interfaces` import composition/session only.
2. **Domain free agent core.** `turn.py`, `session.py`, `tools.py`, `messages.py` must not import or reference jobs, CVs, companies, careers, assessments, decisions, or person names. If agent core needs employment specific metadata (effect kind, retry safety), that metadata travels through a domain free protocol.
3. **Employment tools live in `employment/tools.py`.** Not inside `EmploymentHost._build_registry`.
4. **Shared plain Python actions own import/get/record/list behavior before tool adapters.** The tool handler wraps an action. Tests for actions do not need the tool registry.
5. **CareerStore is the sole source for career facts.** The migration fixture is never read at runtime. `EmploymentHost` does not import or open fixture files.
6. **Assessments are append only.** Latest selected by a monotonic sequence column, not only `created_at`. No numeric fit score. No user decision field.
7. **Durable tool execution boundary.** `ToolCallMessage` persisted before handler execution. If persistence fails, do not dispatch the handler. `ToolResultMessage` persisted immediately after handler completion. If persistence fails, stop before the next model call (do not claim success or failure; the persisted call remains dangling). If assistant message persistence fails, stop safely and do not continue the turn.

---

## Phase 0: Preflight

**Files changed:** none

1. Confirm `git rev-parse HEAD` is `0c412b0`.
2. Confirm `git status --short` shows no modified tracked files.
3. Run full suite and record exact pass/fail count. Expect 217 after the controller supplies the approved private fixture and isolated DB prerequisites.
4. Check that `textual` is absent from `pyproject.toml` and `uv.lock`.
5. Check that `src/haxjobs/interfaces/tui.py` is absent.
6. Inspect all callers of `ModelClient.stream()`, `run_turn()`, `run_stage0()`, `ToolRegistry.dispatch()`, `CareerStore`, `EmploymentHost`, `SessionStore.append_message()`, and `AgentSession.prompt()` before changing shared behavior.

**STOP** if the worktree is dirty for reasons not created by the executor.

---

## Phase A: Career migration integrity

### A.1 Problem statement

The current migration at `src/haxjobs/employment/migration.py` has four defects:

1. **Unstable IDs.** Every migration call generates new random UUID based IDs. Two migrations of the same fixture produce different row IDs. A repeatable build cannot verify row counts or checksums.
2. **Person name derived from career_direction.** `Person.name` is set from `fixture.career_direction.split("|")[0].strip().rstrip(".")`. The career direction field is an instruction string like "Backend Python Engineer | target: London, remote UK". Splitting it produces a fragment, not a name.
3. **Contradictory SkillGaps.** `SkillGap` rows are created for skills in `_GAP_SKILLS` regardless of whether a matching `Skill` already exists at or above the target proficiency. If a track already lists React at "strong" proficiency, a gap for React at "working" is wrong.
4. **Non idempotent SkillEvidence linking.** `store.link_skill_evidence` uses plain `INSERT`, which raises `IntegrityError` on duplicate (skill_id, evidence_id) pairs. Running migration twice corrupts the second run.

### A.2 Required changes

**File:** `src/haxjobs/employment/fixtures.py` (modify)

A.2.1 Add required identity fields to `CareerFixture`. No defaults, no blank fallback:

```python
class CareerFixture(BaseModel):
    person_id: str          # required, e.g. from private fixture
    person_name: str        # required, e.g. from private fixture
    track_name: str         # required, e.g. "Backend Python Engineer"
    career_direction: str
    # ... existing fields unchanged
```

Validation: `person_id`, `person_name`, and `track_name` must be non empty strings. The controller updates the ignored private fixture before any live run. **STOP** before live verification if the private fixture lacks these required fields.

**File:** `tests/fixtures/job_review/career.json` (modify)

Add synthetic `person_id`, `person_name`, and `track_name` values to the tracked test fixture.

**File:** synthetic fixture builders in tests (modify)

All constructors of `CareerFixture` in tests must supply non empty `person_id`, `person_name`, `track_name`. CLI migration tests must use `tests/fixtures/job_review/career.json`, never the ignored private fixture. After this phase, the full automated suite must run in a fresh checkout without any private fixture or operator database.

### A.3 Stable deterministic identifiers

**File:** `src/haxjobs/employment/identifiers.py` (create)

A small shared employment module so migration, assessment, and decision actions use the same helper. No importing IDs from `migration.py` and no duplication:

```python
import hashlib

def make_stable_id(prefix: str, *parts: str) -> str:
    """Produce a stable, repeatable ID from a prefix and ordered parts."""
    joined = "|".join(parts)
    digest = hashlib.sha256(joined.encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"
```

Include enough semantic content to avoid collisions. Evidence IDs must include fixture identity or a content digest to prevent two evidence items with the same label/source from colliding:

```python
evidence_id = make_stable_id("ev", evidence_item.label, evidence_item.source,
                              hashlib.sha256(evidence_item.content.encode()).hexdigest()[:12])
```

**File:** `src/haxjobs/employment/migration.py` (modify)

Import `make_stable_id` from `employment/identifiers.py`. Replace random UUID generation. Derive `track_id` from `person_id` + `track_name` (not from a hardcoded backend track name):

```python
track_id = make_stable_id("track", fixture.person_id, fixture.track_name)
```

Remove all hardcoded backend track ID/name assumptions from migration and composition where this phase touches them.

### A.4 Explicit person identity

Zero hardcoded display identity in source. Person name comes only from the fixture:

```python
person = Person(
    person_id=fixture.person_id,
    name=fixture.person_name,
    ...
)
```

### A.5 Prevent contradictory SkillGaps

Before upserting a gap, check whether the track already has a Skill with that name at or above the target proficiency. Proficiency ordering: `learning < working < strong < primary`.

```python
_PROFICIENCY_ORDER = {"learning": 0, "working": 1, "strong": 2, "primary": 3}

def _proficiency_at_least(existing: str, target: str) -> bool:
    return _PROFICIENCY_ORDER.get(existing, 0) >= _PROFICIENCY_ORDER.get(target, 0)
```

Before `store.upsert_gap(...)`, check existing skills:

```python
existing_skills = {s["name"]: s["proficiency"] for s in store.list_skills(track_id)}
for gap_skill, prof in _GAP_SKILLS.items():
    if gap_skill in existing_skills and _proficiency_at_least(existing_skills[gap_skill], prof):
        continue  # skip: already met or exceeds target
    store.upsert_gap(...)
```

### A.6 Make skill_evidence linking idempotent

**File:** `src/haxjobs/employment/store.py` (modify)

change `link_skill_evidence` INSERT to use `ON CONFLICT` so only the duplicate relationship is ignored, not unrelated integrity failures:

```python
def link_skill_evidence(self, link: SkillEvidence) -> None:
    self._conn.execute(
        "INSERT INTO skill_evidence (skill_id, evidence_id) VALUES (?, ?) "
        "ON CONFLICT(skill_id, evidence_id) DO NOTHING",
        (link.skill_id, link.evidence_id),
    )
    self._conn.commit()
```

### A.7 Tests

**File:** `tests/test_career_graph.py` (modify)

```python
def test_migration_deterministic_ids():
    """Two migrations of the same fixture produce identical IDs."""
    # Run the same migration twice against THE SAME temp file database,
    # not two separate :memory: databases. Second run upserts same IDs.

def test_migration_row_count_stable():
    """Two migrations with same fixture yield identical row counts per table."""

def test_migration_person_name_explicit():
    """Person name comes from fixture.person_name, not career_direction."""

def test_migration_skips_contradictory_gaps():
    """No gap created for a skill that already meets target proficiency."""

def test_migration_skill_evidence_idempotent():
    """Running link_skill_evidence twice does not error or duplicate."""

def test_fixture_requires_person_id_and_name():
    """CareerFixture rejects empty person_id, person_name, or track_name."""
```

### A.8 Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_career_graph.py -k "migration"
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_career_graph.py
```

---

## Phase B: Durable tool execution boundary and ToolExecutionContext

This phase combines the shared `run_turn` signature work so durable persistence and `ToolExecutionContext` are implemented together, not in contradictory phases.

### B.1 Problem statement

The current session (`src/haxjobs/agent_core/session.py`) persists all `result.new_messages` in one batch after `run_turn()` returns. If the process dies during a turn:

- The `ToolCallMessage` was never persisted
- The `ToolResultMessage` was never persisted
- Any partial assistant text was never persisted
- On resume, the model has no record that the tool was ever called
- A mutating tool (like `record_job_assessment`) may have already written its effect, but the session has no trace of it

The fix: persist `ToolCallMessage` before handler execution and `ToolResultMessage` immediately after handler completion.

**Reject batch atomic turn persistence.** The whole purpose of durable tool boundaries is message-by-message durability: each tool call and result is recorded independently so that a mid-turn process death leaves a truthful trace. Mid-turn truncation is represented by canonical partial messages and dangling-call reconciliation (Phase B.6), not by an atomic batch that either writes nothing or writes everything. Do not batch the turn atomically.

### B.2 Required changes

**File:** `src/haxjobs/agent_core/turn.py` (modify)

B.2.1 Add a required `persist_message` callback parameter to `run_turn()`. No `None` fallback, no batch only test path. Tests pass `list.append` or an explicit recorder callback:

```python
from typing import Callable

# SessionStore.append_message is synchronous, so the callback is not awaitable.
PersistCallback = Callable[[ConversationMessage], None]

async def run_turn(
    *,
    session_id: str,
    turn_id: str,
    model: ModelClient,
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
    tool_registry: ToolRegistry,
    active_tools: tuple[str, ...],
    cancel_event: asyncio.Event,
    emit: LiveEventEmitter,
    persist_message: PersistCallback,
    user_message_id: str,
    max_model_steps: int = 5,
) -> TurnResult:
```

B.2.2 Add `user_message_id` to `TurnResult` so session can wire measurement after the turn completes.

B.2.3 Persist `ToolCallMessage` before dispatch. In the tool dispatch loop, after building `tc_msg`:

```python
tc_msg = ToolCallMessage(...)
new_messages.append(tc_msg)
persist_message(tc_msg)
# Only now dispatch the handler
```

If `persist_message(tc_msg)` raises, do **not** dispatch the handler. Fail the turn safely.

B.2.4 Persist `ToolResultMessage` immediately after handler completion. After building `tr_msg`:

```python
new_messages.append(tr_msg)
persist_message(tr_msg)
```

If `persist_message(tr_msg)` raises after the handler has already completed, stop before the next model call. Do not claim success or failure. The persisted tool call remains dangling; on resume, `_detect_dangling_calls` synthesizes `unknown_outcome`. Never continue with an unrecorded tool result.

B.2.5 Persist assistant messages at the same boundary:

```python
new_messages.append(assistant_msg)
persist_message(assistant_msg)
```

If assistant message persistence fails, stop safely and do not continue the turn.

B.2.6 User message persistence remains in `session.py` (already persisted before turn start).

### B.3 ToolExecutionContext

**File:** `src/haxjobs/agent_core/tools.py` (modify)

B.3.1 Add `ToolExecutionContext`:

```python
from dataclasses import dataclass, field
import asyncio

@dataclass
class ToolExecutionContext:
    """Domain free context passed to every tool handler."""
    session_id: str
    turn_id: str
    call_id: str
    user_message_id: str   # from the already persisted current UserMessage
    cancel_event: asyncio.Event
```

B.3.2 Change handler signature. The existing `HandlerFunc` is:

```python
HandlerFunc = Callable[..., Coroutine[Any, Any, dict[str, Any]]]
```

New signature:

```python
HandlerFunc = Callable[[Any, ToolExecutionContext], Coroutine[Any, Any, dict[str, Any]]]
```

The first argument is the validated Pydantic input. The second is the context. No one argument compatibility path. All handlers are rewritten.

B.3.3 Add tool policy metadata to `ToolDefinition`:

```python
class EffectKind(str, Enum):
    READ = "read"
    INTERNAL_WRITE = "internal_write"
    EXTERNAL_EFFECT = "external_effect"

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: HandlerFunc
    max_result_chars: int = 12_000
    effect_kind: EffectKind = EffectKind.READ
    retry_safe: bool = False
```

B.3.4 Modify `ToolRegistry.dispatch()` to accept and pass the context:

```python
async def dispatch(
    self,
    name: str,
    arguments: str,
    active_names: tuple[str, ...],
    context: ToolExecutionContext,
) -> dict[str, Any]:
    ...
    result = await tool.handler(input_obj, context)
    ...
```

B.3.5 Do not build an approval framework. The metadata fields exist so downstream policy can check them. For now, no tool is blocked based on `effect_kind`. The approval gate is deferred.

### B.4 Build ToolExecutionContext in turn runtime

**File:** `src/haxjobs/agent_core/turn.py` (modify)

Build `ToolExecutionContext` for each tool call before dispatch:

```python
context = ToolExecutionContext(
    session_id=session_id,
    turn_id=turn_id,
    call_id=tc_event.call_id,
    user_message_id=user_message_id,
    cancel_event=cancel_event,
)
result = await tool_registry.dispatch(
    name=tc_event.tool_name,
    arguments=tc_event.arguments,
    active_names=active_tools,
    context=context,
)
```

### B.5 Session wiring

**File:** `src/haxjobs/agent_core/session.py` (modify)

B.5.1 Pass `persist_message` from session to `run_turn`:

```python
result = await run_turn(
    ...,
    persist_message=lambda msg: self._store.append_message(self.session_id, msg),
    user_message_id=user_msg.message_id,
    ...
)
# Do NOT iterate result.new_messages again; already persisted
```

B.5.2 Session always supplies `persist_message`. No conditional batch fallback. Test sessions use `list.append` or an explicit recorder callback.

### B.6 Process death detection on resume

**File:** `src/haxjobs/agent_core/session.py` (modify)

B.6.1 Add `_detect_dangling_calls()` method called during `resume()`:

```python
def _detect_dangling_calls(self) -> list[ToolCallMessage]:
    """Find unmatched ToolCallMessages (no matching ToolResultMessage)."""
    stored = self._store.load_messages(self.session_id)
    calls: dict[str, ToolCallMessage] = {}
    results: set[str] = set()
    for row in stored:
        payload = row.get("payload_json", {})
        if payload.get("kind") == "tool_call":
            calls[payload["call_id"]] = ...
        elif payload.get("kind") == "tool_result":
            results.add(payload["call_id"])
    return [c for cid, c in calls.items() if cid not in results]
```

B.6.2 For each dangling call, append a synthetic `ToolResultMessage` with `ok=False`, `error_code="unknown_outcome"`, `error="Process terminated before tool completed. Outcome unknown."`. Never auto retry a dangling call.

B.6.3 Synthetic dangling result insertion must be idempotent enough not to duplicate on repeated resume in one process. Check for an existing result before inserting.

B.6.4 Concurrent same session processes remain explicitly deferred. This is a local single process limitation documented as a known scope boundary.

### B.7 Tests

**File:** `tests/test_turn_runtime.py` (modify)

```python
@pytest.mark.asyncio
async def test_tool_call_persisted_before_handler():
    """ToolCallMessage is persisted before the handler executes."""

@pytest.mark.asyncio
async def test_tool_result_persisted_before_next_model_call():
    """ToolResultMessage is persisted before the next provider stream call."""

@pytest.mark.asyncio
async def test_tool_handler_receives_context():
    """Handler receives ToolExecutionContext with correct fields."""

@pytest.mark.asyncio
async def test_cancel_event_passed_to_tool_context():
    """ToolExecutionContext.cancel_event is the same asyncio.Event."""

@pytest.mark.asyncio
async def test_persist_message_failure_aborts_turn():
    """If ToolCallMessage persistence fails, handler is not dispatched and turn fails."""

@pytest.mark.asyncio
async def test_tool_result_persist_failure_stops_turn():
    """If ToolResultMessage persistence fails after handler, turn stops before next model call."""
```

**File:** `tests/test_session.py` (modify)

```python
@pytest.mark.asyncio
async def test_dangling_call_gets_synthetic_result():
    """Unmatched ToolCallMessage on resume gets unknown_outcome result."""

@pytest.mark.asyncio
async def test_no_duplicate_persistence():
    """Messages are not persisted twice."""

@pytest.mark.asyncio
async def test_dangling_call_not_auto_retried():
    """Synthetic unknown_outcome result does not trigger handler re execution."""

@pytest.mark.asyncio
async def test_dangling_result_idempotent_on_repeated_resume():
    """Second resume in same process does not duplicate synthetic result."""
```

---

## Phase C: Immutable session configuration table

### C.1 Problem statement

Current sessions have no employment scope. They call `system_prompt()` and `context_messages()` fresh each turn. A resumed session could silently switch person or track if the composition root changes. The user cannot tell which person and track a conversation is about.

### C.2 Required changes

**File:** `src/haxjobs/agent_core/session_store.py` (modify)

C.2.1 Use a separate immutable `session_configuration` table keyed by `session_id`. No `ALTER TABLE` syntax and no `IF NOT EXISTS` column hacks:

```sql
CREATE TABLE IF NOT EXISTS session_configuration (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    configuration_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

C.2.2 Create session and configuration in one transaction. Session IDs are fresh and immutable (generated by the caller, e.g. `uuid4()`). Use plain `INSERT`. It must fail with `IntegrityError` on duplicate. Do **not** add `ON CONFLICT DO NOTHING` or any silent-upsert variant. A duplicate session ID is a programming error and must be loud.

```python
def create_session(self, session_id: str, configuration_json: str) -> None:
    now = _utcnow()
    with self._conn:
        self._conn.execute(
            "INSERT INTO sessions (session_id, created_at, updated_at, status, turn_count) "
            "VALUES (?, ?, ?, 'active', 0)",
            (session_id, now, now),
        )
        self._conn.execute(
            "INSERT INTO session_configuration (session_id, configuration_json, created_at) "
            "VALUES (?, ?, ?)",
            (session_id, configuration_json, now),
        )
```

C.2.3 Add `get_session_configuration(session_id)` to return the opaque JSON string.

C.2.4 `AgentSession` need not understand the JSON. Employment composition parses `person_id`/`track_id`.

C.2.5 Existing sessions without configuration fail clearly and ask for `--new`:

```python
cfg = session_store.get_session_configuration(session_id)
if cfg is None:
    raise ValueError(
        f"Session {session_id} has no configuration (created before Plan 004). "
        f"Create a new session with --new."
    )
```

No silent scope fallback.

### C.3 Employment composition

**File:** `src/haxjobs/employment/composition.py` (modify)

C.3.0 Add `CareerStore.list_people()` returning all person rows.

C.3.1 `compose_session` accepts optional `person_id` and `track_id` for NEW sessions only.

If `person_id` is omitted, select exactly one person automatically:
```python
people = career_store.list_people()
if len(people) == 0:
    raise EmploymentSetupError("No people found in career store.")
if len(people) > 1:
    raise EmploymentSetupError(
        f"Multiple people exist. Specify --person-id. "
        f"Available: {[p['person_id'] for p in people]}"
    )
person_id = people[0]["person_id"]
```

If `track_id` is omitted, select exactly one track for the selected person:
```python
tracks = career_store.list_tracks(person_id)
if len(tracks) == 0:
    raise EmploymentSetupError("No career tracks found.")
if len(tracks) > 1 and track_id is None:
    raise EmploymentSetupError(
        f"Multiple tracks exist for {person_id}. Specify --track-id. "
        f"Available: {[t['track_id'] for t in tracks]}"
    )
```

Multiple persons/tracks require explicit selection; zero persons/tracks is an error.

C.3.2 Store configuration JSON:

```python
import json
config = json.dumps({"person_id": person_id, "track_id": track_id})
session_store.create_session(new_id, configuration_json=config)
```

C.3.3 On resume, validate the stored scope against the current host:

```python
cfg = json.loads(session_store.get_session_configuration(session_id))
if cfg.get("person_id") != current_person_id:
    raise ValueError(
        f"Session {session_id} was created for person '{cfg.get('person_id')}' "
        f"but current host is for '{current_person_id}'. Create a new session."
    )
```

Resume loads the immutable configuration and does not reselect.

C.3.4 Clean up stores on construction failure.

Because `composition.py` is already in scope, wrap SessionStore/CareerStore/session construction in try/except so every failure path closes opened stores. If `EmploymentHost` raises, close both `session_store` and `career_store` before re-raising. If `career_store` creation fails, close `session_store` before re-raising. Every code path that opens a store must close it on failure.

Add focused tests for resume-failure and create-session-failure cleanup. Do not silently swallow cleanup errors in tests. Assert that `.close()` was called on every opened store.

### C.4 CLI flags for new sessions

**File:** `src/haxjobs/cli.py` (modify)

Add thin `--person-id` and `--track-id` flags valid only with `haxjobs chat --new`. These are passed to
`compose_session` for explicit selection. No terminal rendering changes. Agent core still treats
`configuration_json` as opaque.

```bash
PYTHONPATH=src:. uv run -- haxjobs chat --new --person-id person-abc123 --track-id track-abc123
```

Update `haxjobs chat --help` output verification in tests and current docs.

### C.4 Session store treats configuration as opaque

The session store treats `configuration_json` as an opaque string. It does not parse, validate, or inspect the JSON. The employment layer owns the schema.

### C.5 Tests

**File:** `tests/test_session_store.py` (modify)

```python
def test_session_configuration_round_trip():
    """Configuration written to DB is returned exactly from get_session_configuration()."""

def test_session_and_config_created_in_one_transaction():
    """Both rows exist or neither exists."""

def test_create_session_without_config_fails():
    """create_session requires configuration_json."""

def test_duplicate_create_session_fails():
    """Duplicate session_id on create_session must raise IntegrityError (plain INSERT),
    not silently attach wrong configuration. No ON CONFLICT DO NOTHING."""
```

**File:** `tests/test_session.py` (modify)

```python
@pytest.mark.asyncio
async def test_unconfigured_session_fails_on_resume():
    """Resume raises ValueError for session without configuration."""

@pytest.mark.asyncio
async def test_wrong_person_session_fails_on_resume():
    """Resume with mismatched person_id raises clear error."""
```

**File:** `tests/test_employment_host.py` (modify)

```python
def test_single_person_auto_selected():
    """When exactly one person exists and no --person-id, it is selected automatically."""

def test_multiple_people_triggers_error_without_explicit():
    """Multiple people and no --person-id -> EmploymentSetupError."""

def test_zero_people_triggers_error():
    """Zero people in career store -> EmploymentSetupError."""

def test_single_track_auto_selected():
    """When exactly one track exists for selected person, it is selected automatically."""

def test_multiple_tracks_triggers_error_without_explicit():
    """Two tracks and no track_id -> EmploymentSetupError, not silent first pick."""

def test_zero_tracks_triggers_error():
    """Zero tracks for selected person -> EmploymentSetupError."""
```

---

## Phase D: Content free per turn measurement

### D.1 Problem statement

We need usage and model performance data to decide when compaction is needed. Compaction should not be implemented until measured context pressure crosses a threshold.

### D.2 Data flow

D.2.1 `AgentSession` captures `started_at` UTC and a monotonic start timestamp before host/context setup, so pre-model failures (host setup error, corrupt history) are measured.

D.2.2 `ModelStreamEvent` already carries `usage`, `model`, and `provider` fields (`client.py`). During `run_turn()`, capture the final `RESPONSE_COMPLETED` event's usage and model/provider into `TurnResult`. These fields stay empty/null when the turn fails before reaching model projection.

D.2.3 Extend `TurnResult`:

```python
@dataclass
class TurnResult:
    ...
    model_name: str = ""
    provider_name: str = ""
    usage: ModelUsage | None = None
    input_characters: int = 0
```

D.2.4 Compute `input_characters` from `project_messages(...)` output: sum of character lengths of all message contents. This is projected input character count, not a token claim. Null usage stays null when the provider omits it.

### D.3 Required changes

**File:** `src/haxjobs/agent_core/session_store.py` (modify)

D.3.1 Add measurement table with `UNIQUE(session_id, turn_id)` to prevent duplicates:

```sql
CREATE TABLE IF NOT EXISTS turn_measurements (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    exit_reason TEXT NOT NULL,
    model_name TEXT NOT NULL DEFAULT '',
    provider_name TEXT NOT NULL DEFAULT '',
    model_steps INTEGER NOT NULL DEFAULT 0,
    tool_starts INTEGER NOT NULL DEFAULT 0,
    input_characters INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    duration_ms REAL NOT NULL DEFAULT 0,
    UNIQUE(session_id, turn_id)
);
```

No prompts, responses, tool arguments, tool results, career content, or credentials.

D.3.2 Add `record_measurement()` method.

**File:** `src/haxjobs/agent_core/session.py` (modify)

D.3.3 One helper records exactly one measurement before emitting `SESSION_SETTLED` on **every** accepted turn exit path:

- Host setup failure
- Corrupt history
- Provider failure
- Interrupt
- Model step limit
- Turn completion

`finished_at` and `duration_ms` are computed by `AgentSession` from the stored start timestamps.

### D.4 What is explicitly NOT built

- Compaction
- Summaries
- Retrieval frameworks
- Token budgets
- Context window checking
- Automatic compaction triggers

### D.5 Tests

**File:** `tests/test_session.py` (modify)

```python
@pytest.mark.asyncio
async def test_measurement_recorded_after_turn():
    """A completed turn records a measurement row with correct turn_number."""

@pytest.mark.asyncio
async def test_measurement_has_no_content_columns():
    """Schema has no prompt_text, response_text, tool_argument, or tool_result columns."""

@pytest.mark.asyncio
async def test_measurement_row_contains_no_content_values():
    """Rows contain no content text in any column."""

@pytest.mark.asyncio
async def test_measurement_interrupted_turn():
    """An interrupted turn still records exit_reason=interrupted."""

@pytest.mark.asyncio
async def test_measurement_null_usage_when_provider_omits():
    """When provider returns no usage, measurement stores NULL tokens."""

@pytest.mark.asyncio
async def test_measurement_host_setup_failure():
    """Host setup failure records exit_reason=host_setup_failure with null model fields."""

@pytest.mark.asyncio
async def test_measurement_duplicate_turn_id_prevented():
    """UNIQUE(session_id, turn_id) prevents duplicate measurement rows."""

@pytest.mark.asyncio
async def test_measurement_no_forbidden_content_fields():
    """Measurement row has no prompt, response, tool argument, or tool result content."""
```

---

## Phase E: Employment models, storage, and actions

### E.1 Problem statement

No normalized `Job` model exists. Jobs are only in JSON fixture files. The conversational runtime cannot `get_job(job_id)` from a store. No `JobAssessment` model or store exists.

### E.2 New Pydantic models

**File:** `src/haxjobs/employment/schema.py` (modify)

```python
class Job(BaseModel):
    """A normalized saved job."""
    job_id: str
    external_ref: str
    employer_name: str | None = None
    title: str
    location: str
    source_url: str
    source_type: str
    description: str
    source_status: str = ""        # mapped from SourceObservation.status: "current", "gone", etc.
    description_kind: str = ""     # truthful deterministic: "source_page_text", or prior kind if unchanged
    description_complete: bool = False
    observed_at: str
    allowed_source_hosts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_content_hash: str = ""   # full SHA-256 of normalized description snapshot
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)

class ConstraintCheck(BaseModel):
    constraint_id: str
    constraint_text: str
    result: Literal["pass", "fail", "unknown"]

class JobAssessment(BaseModel):
    assessment_id: str             # stable ID derived from tool_call_id
    job_id: str
    track_id: str
    tool_call_id: str              # idempotency key; assessment_id is derived from this
    recommendation: Literal["pursue", "consider", "skip", "needs_more_information"]
    summary: str
    constraint_checks: list[ConstraintCheck] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_content_hash: str = ""  # copied from saved Job server-side; model never supplies this
    sequence: int | None = None    # store-populated output-only; never model/tool input
    created_at: str = Field(default_factory=_utcnow)
```

No numeric fit score. No user decision field.

### E.3 Store additions

**File:** `src/haxjobs/employment/store.py` (modify)

E.3.1 Add DDL:

```sql
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    external_ref TEXT NOT NULL,
    employer_name TEXT,
    title TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    description_complete INTEGER NOT NULL DEFAULT 0,
    observed_at TEXT NOT NULL,
    allowed_source_hosts TEXT NOT NULL DEFAULT '[]',
    warnings TEXT NOT NULL DEFAULT '[]',
    source_content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_assessments (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    tool_call_id TEXT NOT NULL UNIQUE,
    recommendation TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    constraint_checks TEXT NOT NULL DEFAULT '[]',
    strengths TEXT NOT NULL DEFAULT '[]',
    gaps TEXT NOT NULL DEFAULT '[]',
    unknowns TEXT NOT NULL DEFAULT '[]',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    source_content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
```

E.3.2 Use `sequence INTEGER PRIMARY KEY AUTOINCREMENT` for deterministic latest/history ordering. `assessment_id` is a separate `TEXT NOT NULL UNIQUE` column. The store INSERT omits `sequence` (SQLite auto-assigns it) and reads it back via `lastrowid`. Pydantic model uses `sequence: int | None = None` as store-populated output metadata; the model/tool never supplies it. Latest/history queries `ORDER BY sequence`. This removes same-timestamp ambiguity and MAX+1 races.

E.3.3 Add store methods:

```python
def upsert_job(self, job: Job) -> None: ...

def get_job(self, job_id: str) -> dict | None: ...

def upsert_assessment(self, assessment: JobAssessment) -> JobAssessment:
    """Transaction: check for duplicate tool_call_id, insert if new."""
    # Same call_id + semantically identical payload -> return existing row (idempotent replay)
    # Same call_id + different payload -> return typed idempotency_conflict, write nothing

def get_latest_assessment(self, job_id: str, track_id: str) -> dict | None:
    """Return the most recent assessment by sequence DESC."""

def list_assessments(self, job_id: str, track_id: str) -> list[dict]:
    """All assessments for a job/track pair, ordered by sequence ASC."""
```

### E.4 Plain Python actions

**File:** `src/haxjobs/employment/job_actions.py` (create)

`assessment_id` is a stable ID derived from `tool_call_id` via `make_stable_id("asmt", tool_call_id)`. The `IdempotencyConflict` type is defined in `src/haxjobs/employment/job_actions.py` (a tiny `employment/errors.py` is acceptable if the action file grows unwieldy).

Idempotency contract:
- Compare semantic payload excluding generated ID, `sequence`, and `created_at`.
- Hash/current snapshot is loaded server-side before the comparison (see F.5).
- Same call_id + identical semantic payload -> return existing row and include a `replay: true` indicator in the tool result.
- Same call_id + different semantic payload -> return typed `IdempotencyConflict` with details; the caller wraps it as a structured tool error.
- No raw sqlite `IntegrityError` reaches the model.
- Store transaction uses `BEGIN IMMEDIATE` (or one sqlite `with self._conn:` transaction) around the lookup+insert. Note the current single-process assumption.

```python
def import_job_from_fixture(store: CareerStore, fixture_path: str) -> Job: ...

def get_job(store: CareerStore, job_id: str) -> Job | None: ...

def record_assessment(
    store: CareerStore,
    assessment: JobAssessment,
) -> JobAssessment | IdempotencyConflict:
    """Append an assessment. Returns existing or conflict on duplicate tool_call_id."""

def get_latest_assessment(store: CareerStore, job_id: str, track_id: str) -> JobAssessment | None: ...

def list_assessments(store: CareerStore, job_id: str, track_id: str) -> list[JobAssessment]: ...
```

`get_job` returns latest assessment only. Do not include a placeholder `latest_decision`. Plan 005 extends the output with latest decision.

### E.5 One way job import

Run exactly once, controlled by the operator, not at runtime:

```bash
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions \
  import discussion/fixtures/harness/job-49.json
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions \
  import discussion/fixtures/harness/job-328.json
```

Jobs use stable IDs: `job-49`, `job-328`. After import, the runtime never opens fixture files.

### E.6 Tests

**File:** `tests/test_job_actions.py` (create)

```python
def test_import_job_49_from_fixture():
    """Job 49 imports with stable ID job-49, correct title, employer."""

def test_import_job_328_from_fixture():
    """Job 328 imports with stable ID job-328, content_complete=False."""

def test_get_job_returns_none_for_unknown():
    """get_job('nonexistent') returns None."""

def test_record_assessment_and_retrieve():
    """Record assessment, retrieve it as latest."""

def test_assessment_idempotent_replay_same_payload():
    """Same call_id + same payload returns existing row, no new write."""

def test_assessment_idempotency_conflict_different_payload():
    """Same call_id + different payload returns typed idempotency_conflict, writes nothing."""

def test_latest_assessment_uses_sequence_not_created_at():
    """Two assessments within same created_at second: latest uses sequence order."""

def test_assessment_no_fit_score_field():
    """JobAssessment has no numeric fit_score field."""

def test_assessment_no_user_decision_field():
    """JobAssessment has no user decision field."""
```

---

## Phase F: Job source snapshot and hash

### F.1 Problem statement

The `Job` model needs a trusted source content hash. The `inspect_job_source` tool must update the saved Job's current source snapshot (description, completeness, status, warnings, observed_at, hash) through a typed action. The model never supplies the hash.

### F.2 Required changes

**File:** `src/haxjobs/employment/schema.py` (modify)

`Job.source_content_hash` is full SHA-256 computed server side from the normalized description snapshot.

### F.3 Refactor JobSourceFetcher

**File:** `src/haxjobs/employment/job_source.py` (modify)

Refactor `JobSourceFetcher` to accept a saved job source target (a `Job` row dict with `source_url`, `allowed_source_hosts`), not `JobFixture` at normal runtime. Fixtures are import input only.

**Blocking network offload.** The current `fetch` is `async` but calls blocking `socket.getaddrinfo`, `urllib.request.urlopen`, and `.read()`. Wrap the entire blocking resolver/network operation inside `asyncio.to_thread` (or an equally small stdlib offload). This preserves the injected fake resolver and transport determinism. Tests that pass a `resolver` or `transport_factory` still work because the fake path never hits the real network inside `to_thread`. The 15 s network timeout bounds the thread.

Add an event-loop-responsiveness test that uses a blocking fake transport (not an `async` fake) and asserts the event loop is not blocked during the offloaded call. State in the test and the report that cancelling the outer asyncio task cannot kill an already-running `to_thread` thread. The thread runs to completion or hits the 15 s network timeout. Real `async` HTTP client (`httpx`, `aiohttp`) remains deferred.

### F.4 Inspect job source action

**File:** `src/haxjobs/employment/job_actions.py` (modify)

Add. This action is `async` because `JobSourceFetcher.fetch` is async:

```python
async def inspect_job_source(
    store: CareerStore,
    job_id: str,
    fetcher: JobSourceFetcher,
) -> SourceInspectionResult:
    """Fetch source for a saved job and update the Job row's current snapshot."""
    job = get_job(store, job_id)
    if job is None:
        return SourceInspectionResult(ok=False, error="Job not found")

    raw_result = await fetcher.fetch_from_job(job)
    if not raw_result.ok:
        # On failed inspection, preserve old snapshot and return structured failure
        return SourceInspectionResult(ok=False, error=raw_result.error)

    # Compute hash server side
    normalized = normalize_description(raw_result.visible_text)
    content_hash = hashlib.sha256(normalized.encode()).hexdigest()

    # Update Job snapshot in one typed action/transaction.
    # Do NOT blindly set description_complete=True.
    # Preserve prior completeness unless the source adapter returns an explicit completeness signal.
    job.description = normalized
    job.source_content_hash = content_hash
    # Map Job.source_status from SourceObservation.status, not a nonexistent source_status field.
    job.source_status = raw_result.status  # e.g. "current", "gone", "blocked", "unavailable"
    # Set description_kind to a truthful deterministic value such as 'source_page_text'
    # for stripped visible text, or preserve the existing kind if no new text arrived.
    # Preserve content_type in tool output, not as description_kind.
    job.description_kind = _description_kind_for_source(raw_result)
    job.content_type_at_fetch = raw_result.content_type  # preserved in tool output
    job.warnings = raw_result.warnings
    job.observed_at = _utcnow()
    # Only override description_complete if the adapter provides an explicit signal:
    if raw_result.description_complete is not None:
        job.description_complete = raw_result.description_complete
    store.upsert_job(job)

    return SourceInspectionResult(
        ok=True,
        content_hash=content_hash,
        visible_text=raw_result.visible_text,
        ...
    )
```

Hax can still judge thin text even when `description_complete` remains False. Historical source observations remain deferred and are called out as a limitation.

### F.5 Record assessment hash

When `record_job_assessment` is called, the model input contains no hash field. The action loads the current `Job` from the store server-side and copies `source_content_hash`:

```python
def record_assessment(store, assessment):
    job = store.get_job(assessment.job_id)
    if job is None:
        raise ValueError(f"Job {assessment.job_id} not found")
    assessment.source_content_hash = job["source_content_hash"]
    # assessment_id is derived from tool_call_id via make_stable_id
    assessment.assessment_id = make_stable_id("asmt", assessment.tool_call_id)
    # sequence is None (model doesn't supply it); store populates it on INSERT
    ...
```

### F.6 Effect kind for inspection

Because `inspect_job_source` writes the current trusted snapshot to the Job row and calls `JobSourceFetcher.fetch` (async I/O), its handler is `async` and it is marked `EffectKind.INTERNAL_WRITE` and `retry_safe=True` with idempotent upsert semantics.

Historical source observation tables are deferred. The assessment's hash preserves which current snapshot it used. State this limitation in the report.

### F.7 Tests

**File:** `tests/test_job_actions.py` (modify)

```python
def test_source_content_hash_computed_server_side():
    """Hash is SHA-256 of normalized description, not model supplied."""

def test_inspect_updates_job_snapshot():
    """Successful inspection updates Job.description and source_content_hash."""

def test_failed_inspection_preserves_old_snapshot():
    """Failed fetch does not overwrite existing Job snapshot."""

def test_assessment_hash_loads_from_saved_job():
    """Assessment.source_content_hash equals the Job's current source_content_hash."""

def test_source_status_maps_from_observation_status():
    """Job.source_status is mapped from SourceObservation.status ("current", "gone", etc.),
    not a nonexistent source_status field."""

def test_description_kind_is_deterministic_not_content_type():
    """description_kind is set to a truthful value like 'source_page_text',
    not the raw HTTP Content-Type. content_type is preserved separately in tool output."""
```

---

## Phase G: Employment tools

### G.1 Problem statement

`EmploymentHost._build_registry()` defines the single `inspect_job_source` tool inline. With three tools (get_job, inspect_job_source, record_job_assessment), inline definition is unreadable.

### G.2 Required changes

**File:** `src/haxjobs/employment/tools.py` (create)

Move all tool definitions from `EmploymentHost._build_registry` and `review_job.build_stage1_tools` here. Each tool gets:

- A Pydantic input model
- A Pydantic output model
- A description string
- An async handler function that wraps the corresponding action from `job_actions.py`
- `effect_kind` and `retry_safe` metadata

Tools:

1. **`get_job(job_id: str)`**: `EffectKind.READ`, `retry_safe=True`
   - Reads from `CareerStore.jobs` table
   - Returns job fields and latest assessment for active track
   - Unknown job_id returns structured error

2. **`inspect_job_source(job_id: str)`**: `EffectKind.INTERNAL_WRITE`, `retry_safe=True`
   - Resolution: `get_job` from store -> read `source_url` from saved Job -> fetch
   - Model supplies `job_id`, never a URL. The tool resolves the URL from the store
   - On success: updates Job's current source snapshot (description, hash), then returns content
   - On failure: preserves old snapshot, returns error
   - Preserves all existing `JobSourceFetcher` safety: HTTPS only, no redirects, no proxies, host allowlist, public DNS, port check, byte/text/time limits
   - DNS rebinding documented as attended local residual risk

3. **`record_job_assessment(...)`**: `EffectKind.INTERNAL_WRITE`, `retry_safe=False`
   - Uses `context.call_id` as idempotency key
   - Writes to `job_assessments` table via transaction (check+insert)
   - Same call_id + same payload: returns existing row (idempotent replay)
   - Same call_id + different payload: returns typed idempotency_conflict as structured tool error
   - Computes `source_content_hash` by loading saved Job server side

Tool handlers receive `(input_model_instance, ToolExecutionContext)`.

### G.3 Source URL security

The `inspect_job_source` tool resolves `source_url` from the saved `Job` row. The model cannot pass an arbitrary URL. If the saved URL is missing, the tool returns an error.

DNS rebinding is documented as an attended local residual risk: the process resolves the hostname at fetch time, and a DNS rebinding attack between allowlist check and connect could redirect to a private address. This is accepted for attended local use at this stage.

### G.4 Fetched text is untrusted evidence

The `inspect_job_source` result content is returned to the model as a tool result. It never becomes system instructions and never overrides safety rules.

### G.5 Tests

**File:** `tests/test_employment_tools.py` (create)

```python
@pytest.mark.asyncio
async def test_get_job_returns_job_fields():
    """get_job('job-49') returns title, employer, description, etc."""

@pytest.mark.asyncio
async def test_get_job_unknown_returns_error():
    """get_job('job-999') returns ok=False with error."""

@pytest.mark.asyncio
async def test_inspect_job_source_resolves_url_from_store():
    """inspect_job_source('job-49') uses stored source_url, not caller supplied."""

@pytest.mark.asyncio
async def test_inspect_job_source_model_cannot_supply_url():
    """Tool input model has no url field."""

@pytest.mark.asyncio
async def test_record_job_assessment_idempotent_replay():
    """Same call_id + same payload returns existing row."""

@pytest.mark.asyncio
async def test_record_job_assessment_idempotency_conflict():
    """Same call_id + different payload returns structured error, writes nothing."""

@pytest.mark.asyncio
async def test_record_job_assessment_uses_context_call_id():
    """Tool uses context.call_id, not a separate id parameter."""

@pytest.mark.asyncio
async def test_tool_effect_kinds_are_correct():
    """get_job=READ, inspect=INTERNAL_WRITE, record_assessment=INTERNAL_WRITE."""
```

---

## Phase H: Career context

### H.1 Problem statement

The current `build_career_context()` lists skill names and evidence labels but does not include actual evidence content. The model cannot use the evidence to support claims. Evidence is also not deduplicated or capped.

### H.2 Required changes

**File:** `src/haxjobs/employment/context.py` (modify)

H.2.1 Include evidence content, privacy label, source, and verification flag for each evidence item linked to skills on the active track.

H.2.2 Deduplicate evidence by ID. If the same evidence item is linked to multiple skills, include it once.

H.2.3 Deterministic order: evidence sorted by `evidence_id`.

H.2.4 Per item character cap: 500 characters per evidence content. Total evidence section character cap: 8000 characters. If a cap is hit, add `[truncated]` marker and stop.

H.2.5 For private evidence (`privacy_level == "private"`): include content in the context but with a `[PRIVATE: do not expose in public output, but you may use it for reasoning]` prefix. The prompt must protect private evidence, not exclude it automatically.

H.2.6 No embeddings, no vector search, no similarity ranking.

### H.3 Tests

**File:** `tests/test_employment_host.py` (modify)

```python
def test_context_includes_evidence_content():
    """Evidence content appears in context messages, not just labels."""

def test_context_includes_privacy_label():
    """Private evidence has [PRIVATE] prefix in context."""

def test_context_includes_verification_flag():
    """Evidence with verified_at shows the date."""

def test_context_deduplicates_evidence():
    """Same evidence_id linked to two skills appears once."""

def test_context_evidence_ordered_by_id():
    """Evidence items sorted by evidence_id."""

def test_context_evidence_capped():
    """Evidence items > 500 chars are truncated; total section capped at 8000."""
```

---

## Phase I: Stage 0/1 runtime deletion

**EXECUTION-ORDER GATE:** Phase I deletion depends on Phase K replacement trajectories passing. Phase K must execute and pass before Phase I. A linear executor must not delete first. Either move deletion after trajectories in execution order or enforce this gate at the phase heading.

### I.1 Problem statement

The Stage 0/1 experiment runtime (`runtime.py`, `types.py`, `events.py`, `artifacts.py`, `review_job.py`, `experiment_cli.py`) is superseded by the conversational runtime with `AgentSession` and `run_turn()`. After the new fake trajectories pass (Phase K), delete the superseded live source path.

### I.2 Required deletion (after Phase K passes)

**Delete:**
```text
src/haxjobs/agent_core/runtime.py
src/haxjobs/agent_core/types.py
src/haxjobs/agent_core/events.py
src/haxjobs/agent_core/artifacts.py
src/haxjobs/employment/review_job.py
src/haxjobs/interfaces/experiment_cli.py
tests/test_stage0_job_review.py
tests/test_stage1_source_inspection.py
```

**Remove exports/imports:**
```text
src/haxjobs/agent_core/__init__.py: remove runtime, types, events, artifacts exports
src/haxjobs/employment/__init__.py: remove review_job exports
src/haxjobs/interfaces/__init__.py: remove experiment_cli export
src/haxjobs/cli.py: remove experiment review-job subcommand and import
```

### I.3 Update CLI and current docs accordingly

Remove the `experiment review-job` subcommand from `cli.py`. Update current doc references in
`README.md`, `docs/GETTING_STARTED.md`, `docs/PRODUCT.md`, `docs/HAXJOBS.md`, `AGENTS.md`,
and `.agents/skills/haxjobs-pipeline/SKILL.md` to remove live experiment instructions.
Historical reports in `deliverables/` and `docs/implementation-reports/` remain unchanged.

No wrapper. Plan 005 must not carry this deletion.

### I.4 Historical records preserved

Keep historical `plans/`, `reports/`, `deliverables/` and frozen fixture data (`discussion/fixtures/`) as records. Do not delete `deliverables/001-*`, `deliverables/002-*`, or `diagram/003-*` / `diagram/004-*`.

---

## Phase J: Reality doc refresh

After all implementation phases pass, update stale current state claims in these files only where they describe code that no longer exists or behavior that has changed:

```text
AGENTS.md
docs/HAXJOBS.md
docs/PRODUCT.md
README.md
docs/GETTING_STARTED.md
.agents/skills/haxjobs-pipeline/SKILL.md
```

Do not rewrite product direction. Only correct stale claims about live code, CLI commands, module structure, and interfaces.

---

## Phase K: Acceptance trajectories

### K.1 Job 328 trajectory (fake, no network)

```text
Given: Jobs 49 and 328 imported into career store
Given: Career graph migrated
Given: Session created with person_id and track_id scope
When: User prompts "What do you think of job 328?"
Then:
  1. get_job("job-328") is called (tool call persisted before handler)
  2. Job is returned with content_complete=False
  3. Hax detects thin evidence
  4. inspect_job_source("job-328") is called
  5. Fake fetcher returns thin/error result
  6. record_job_assessment(recommendation="needs_more_information") is called
     - tool_call_id used as idempotency key
     - source_content_hash loaded from saved Job server side
     - Assessment persisted
  7. Natural reply explains the gap
  8. All tool call/result messages are durable
  9. Close session
  10. Resume session and ask "What did you say about job 328?"
  11. Session loads prior history, Hax retrieves the same assessment
```

Expected test file: `tests/test_trajectory_job_328.py` (create)

```python
@pytest.mark.asyncio
async def test_job_328_incomplete_assessment_trajectory():
    """Full fake trajectory: thin job -> source inspection -> needs_more_information."""

@pytest.mark.asyncio
async def test_job_328_assessment_survives_resume():
    """Close and resume: assessment is retrievable."""
```

### K.2 Job 49 trajectory (constraint mismatch)

```text
Given: Job 49 imported (IT Support Analyst vs Backend Python Engineer track)
When: User asks about job 49
Then:
  1. get_job("job-49") returns full job
  2. Hax checks constraints: title/role mismatch with backend track
  3. record_job_assessment(recommendation="skip", constraint_checks containing fail)
  4. Natural reply explains the mismatch
```

### K.3 State order tests

**File:** `tests/test_durable_tool_effects.py` (create)

Additionally, in `tests/test_turn_runtime.py`, the `_fake_registry()` helper currently defines two identical `_TestOutput` classes. Remove the duplicate definition as a tiny scoped cleanup.

```python
@pytest.mark.asyncio
async def test_tool_call_persisted_before_handler():
    """ToolCallMessage row exists before handler function executes."""

@pytest.mark.asyncio
async def test_tool_result_persisted_before_next_model_call():
    """ToolResultMessage row exists before second model stream starts."""

@pytest.mark.asyncio
async def test_dangling_call_appends_unknown_outcome():
    """Unmatched ToolCallMessage on resume -> synthetic ToolResultMessage."""

@pytest.mark.asyncio
async def test_duplicate_call_id_same_payload_returns_existing():
    """Two record_job_assessment calls with same call_id and payload -> one row, first returned."""

@pytest.mark.asyncio
async def test_duplicate_call_id_different_payload_conflict():
    """Same call_id + different payload -> conflict error, no write."""

@pytest.mark.asyncio
async def test_fixed_session_scope():
    """Session created for person A cannot resume for person B."""

@pytest.mark.asyncio
async def test_measurement_has_no_content():
    """Measurement rows contain no prompt text, response text, or tool arguments."""

@pytest.mark.asyncio
async def test_persist_failure_before_handler_aborts():
    """ToolCallMessage persistence failure prevents handler dispatch."""

@pytest.mark.asyncio
async def test_persist_failure_after_handler_stops_turn():
    """ToolResultMessage persistence failure after handler stops before next model call."""
```

### K.4 Real provider manual run

Controller owned. Occurs only after fake trajectory and source changes pass. Use a disposable session DB:

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan004-live.db uv run -- haxjobs chat --new
```

Manual steps:
1. Ask about job 49: observe tool lifecycle events, assessment recommendation
2. Ask about job 328: observe source inspection attempt
3. Close and resume: verify history loaded
4. Verify no raw career output in terminal

The controller records safe run IDs, hashes, and verdicts. Manual proof stores safe metadata and rubric results, not raw PTY transcripts or career/model text in git.

---

## Rollback and recovery

### Rollback design

This plan delivers recovery by design, not a separate rollback script:

1. **Stable deterministic IDs** (Phase A): two migrations of the same fixture produce identical IDs. Re running migration is safe.
2. **Append only assessments** (Phase E): no data is mutated. Rollback means stop writing assessments. Old data is intact.
3. **Idempotent tool execution** (Phase B/E): duplicate `tool_call_id` with same payload returns existing row. No duplicate writes.
4. **Idempotency conflict** (Phase E): duplicate `tool_call_id` with different payload writes nothing and returns a structured error. No silent data corruption.
5. **Synthetic unknown_outcome** (Phase B): dangling tool calls on resume get a synthetic result. The model is informed, not confused.
6. **Disposable session DB** (Phase K): live testing uses a temp DB. Operator can delete it and start over.

### Recovery scenarios

- **Migration corruption:** Stop active processes, create a SQLite-consistent `0600` backup, rebuild into a separate temporary database from the approved fixture, run `PRAGMA integrity_check`, verify row counts, then swap atomically. Never delete the only career database first.
- **Session DB corruption:** Preserve the damaged file as a `0600` backup and start with a new session database path. Conversation history is useful personal data even though canonical employment facts live separately.
- **Stuck dangling call:** Resume the session. Synthetic `unknown_outcome` is appended. Never retry automatically. A later explicit read or idempotent action may reconcile the outcome.
- **Accidental tool call replay:** `tool_call_id` UNIQUE constraint prevents duplicate writes. Idempotency check returns the existing row or a typed conflict.

---

## Files in scope

### Create

```text
src/haxjobs/employment/identifiers.py
src/haxjobs/employment/job_actions.py
src/haxjobs/employment/tools.py
tests/test_job_actions.py
tests/test_employment_tools.py
tests/test_trajectory_job_328.py
tests/test_durable_tool_effects.py
```

### Modify

```text
src/haxjobs/agent_core/tools.py: ToolExecutionContext, EffectKind, handler signature, dispatch(context)
src/haxjobs/agent_core/turn.py: persist_message (required), ToolExecutionContext, user_message_id, TurnResult usage/input_characters
src/haxjobs/agent_core/session.py: persist_message wiring, dangling call detection, session configuration validation
src/haxjobs/agent_core/session_store.py: session_configuration table, turn_measurements table, record_measurement()
src/haxjobs/employment/schema.py: Job, ConstraintCheck, JobAssessment models; CareerFixture person_id/person_name/track_name (required)
src/haxjobs/employment/store.py: jobs and job_assessments tables, link_skill_evidence idempotent
src/haxjobs/employment/migration.py: stable IDs from identifiers.py, person_name from fixture, contradictory gap prevention
src/haxjobs/employment/fixtures.py: required person_id, person_name, track_name fields
src/haxjobs/employment/host.py: tools moved to employment/tools.py, handler signature change
src/haxjobs/employment/context.py: evidence content, privacy, verification, dedup, caps
src/haxjobs/employment/composition.py: session configuration, track selection, multi track error
src/haxjobs/employment/job_source.py: refactor to accept Job row, not JobFixture
src/haxjobs/cli.py: remove experiment review-job subcommand (after Phase K)
tests/test_career_graph.py: migration integrity tests, fixture validation tests
tests/test_turn_runtime.py: tool call/result persistence order, context tests, persist failure tests
tests/test_session.py: dangling call, duplicate persistence, scope/configuration tests, measurement tests
tests/test_employment_host.py: scope tests, evidence content tests
tests/test_session_store.py: configuration round trip tests
tests/fixtures/job_review/career.json: add person_id, person_name, track_name
AGENTS.md: reality doc refresh (Phase J)
docs/HAXJOBS.md: reality doc refresh (Phase J)
docs/PRODUCT.md: reality doc refresh (Phase J)
README.md: reality doc refresh (Phase J)
docs/GETTING_STARTED.md: reality doc refresh (Phase J)
.agents/skills/haxjobs-pipeline/SKILL.md: reality doc refresh (Phase J)
```

### Delete (after Phase K fake trajectories pass)

```text
src/haxjobs/agent_core/runtime.py
src/haxjobs/agent_core/types.py
src/haxjobs/agent_core/events.py
src/haxjobs/agent_core/artifacts.py
src/haxjobs/employment/review_job.py
src/haxjobs/interfaces/experiment_cli.py
tests/test_stage0_job_review.py
tests/test_stage1_source_inspection.py
```

### Modify exports/imports (after Phase K)

```text
src/haxjobs/agent_core/__init__.py
src/haxjobs/employment/__init__.py
src/haxjobs/interfaces/__init__.py
```

### Do not touch

```text
state/
src/haxjobs/model/
src/haxjobs/agent_core/messages.py
src/haxjobs/agent_core/live_events.py
src/haxjobs/cv_variants/
src/haxjobs/config.py
src/haxjobs/interfaces/terminal.py
src/haxjobs/interfaces/profile_cli.py
tests/test_conversation_messages.py
tests/test_live_events.py
tests/test_model_streaming.py
tests/test_terminal.py
tests/test_terminal_pty.py
pyproject.toml
uv.lock
haxjobs.toml
discussion/
deliverables/001-*/
deliverables/002-*/
deliverables/003-*/
diagram/003-*/
diagram/004-*/
```

---

## Explicitly deferred

- Compaction, summaries, retrieval frameworks, token budgets, context window checking
- User decisions (Plan 005)
- Approvals framework
- Numeric fit scores
- Discovery, watches, background work
- Application packs, submission, outreach
- Arbitrary URL fetching
- Subagents
- Coding workspaces
- UI changes
- Plugins or MCP
- Source observation history (current snapshot only; assessment hash preserves which snapshot was used)
- Cross process session locking
- Learning engine

---

## Verification floor

```bash
# Full suite
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/

# Specific new test files
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_job_actions.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_employment_tools.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_trajectory_job_328.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_durable_tool_effects.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_career_graph.py -k "migration"
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_career_graph.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_session.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_turn_runtime.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_employment_host.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_session_store.py

# Compile and lock
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check

# CLI
PYTHONPATH=src:. uv run -- haxjobs --help
PYTHONPATH=src:. uv run -- haxjobs chat --help
```

No test may call a live model or network. No test may mutate the operator's real career DB or session DB.

---

## STOP conditions

STOP and report instead of guessing if:

1. Execution baseline differs from `0c412b0`
2. Existing career graph, session, or terminal tests regress beyond environment drift
3. `persist_message` callback pattern creates deadlocks or ordering violations
4. Dangling call detection cannot distinguish a genuine unmatched call from a correctly paired one
5. `INSERT ... ON CONFLICT DO NOTHING` on skill_evidence requires the conflict target columns to have a matching unique index; verify before executing
6. Stable ID hash collisions occur (12 hex chars from SHA-256 is safe but test it)
7. Session configuration migration for existing databases fails
8. Multi track behavior cannot be proven with synthetic isolated fixtures
9. A proposed change requires agent core to import employment modules
10. Tool handler signature change breaks more than the handlers in scope
11. `record_job_assessment` tool requires model to produce structured Pydantic output that the model cannot reliably generate (test with fake before committing)
12. Idempotency conflict detection cannot distinguish same payload from different payload reliably

---

## Deliverables

**Folder:** `deliverables/004-saved-job-assessment/`

Required contents:

```text
README.md
plan.md                          (copy of this file)
report.md                        (evidence backed completion report)
review-ledger.md                 (reviewer findings and decisions)
manual-proof.md                  (controller owned safe run IDs, metadata, rubric results: not raw PTY transcripts or career/model text)
employment-models.drawio         (Job, Assessment, ConstraintCheck schema)
employment-models.png
tool-effects.drawio              (durable tool execution boundary, dangling calls)
tool-effects.png
conversation-trajectory.drawio   (full job review trajectory)
conversation-trajectory.png
```

### Draw.io requirements

Three clean diagrams of the actual post plan system:

1. **employment-models.drawio:** Person, CareerTrack, Skill, Evidence, Job, ConstraintCheck, JobAssessment: their relationships, foreign keys, idempotency keys. 5 to 7 groups, under 35 cells, thick orthogonal arrows, no file paths.
2. **tool-effects.drawio:** Durable tool execution boundary: ToolCallMessage persistence before handler, ToolResultMessage persistence after handler, persist failure stops, dangling call detection on resume, synthetic unknown_outcome. 5 to 7 groups, under 35 cells, thick orthogonal arrows, no file paths.
3. **conversation-trajectory.drawio:** Full job review trajectory: user -> get_job -> optional inspect -> record_assessment -> resume retrieves. 5 to 7 groups, under 35 cells, thick orthogonal arrows, no file paths.

### Report requirements

The `report.md` must cover:

1. Every file created, modified, or deleted with exact paths
2. Tests written and exact pass/fail counts
3. Real provider manual run results (controller owned safe metadata)
4. Diagrams produced
5. Reviewer findings and repairs
6. Anything skipped or deferred
7. Current risks and known limitations
8. Explicit confirmation of zero employment imports in agent core
9. Removal of the duplicate `_TestOutput` class definition in `tests/test_turn_runtime.py` (two identical class definitions in `_fake_registry()` helper; removed as tiny scoped cleanup)
10. Final commit SHA recorded by controller after acceptance; report must not claim its own containing commit SHA

---

*Plan 004 delivers the first state changing employment workflow: normalized jobs, typed assessments, durable tool execution boundaries, immutable session configuration, content free measurement, and career migration integrity. Current plans stay TODO and do not claim unbuilt work.*
