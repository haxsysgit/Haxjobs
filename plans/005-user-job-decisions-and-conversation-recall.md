# Plan 005: User Job Decisions and Conversation Recall

| Key | Value |
|----|-----|
| **Plan ID** | 005 |
| **Title** | User Job Decisions and Conversation Recall |
| **Design baseline** | Recorded post Plan 004 acceptance |
| **Depends on** | Plan 004 accepted (saved job assessment and durable tool effects) |
| **Status** | TODO |
| **Priority** | P1 |

---

## Executor warning

This plan is not final just because it is written down.

Before editing code, compare every instruction against the live repository AFTER Plan 004 is accepted. Read the source, tests, imports, and current dependency lock. If the plan disagrees with working code, stop and report the drift. Do not silently adapt. Do not preserve stale behavior through compatibility wrappers.

The writer must read these files first:

1. `AGENTS.md`
2. `plans/004-saved-job-assessment-and-durable-tool-effects.md` (accepted)
3. `plans/README.md`
4. `discussion/004-minimal-job-native-harness.md`
5. `discussion/006-pi-inspired-haxjobs-architecture.md`
6. `docs/harness-primitives/05-durable-state.md`
7. `docs/harness-primitives/08-verification-and-observability.md`
8. this plan in full

Then inspect every file under `src/haxjobs/employment/`, `src/haxjobs/agent_core/`, and relevant tests. Treat the post Plan 004 code as authority.

---

## Drift and status

| Check | Status |
|-----|------|
| Plan 004 accepted | MUST BE DONE before executor starts |
| Plan 004 baseline commit | RECORD HERE before starting |
| Test suite post Plan 004 | RECORD HERE before starting |

**STOP** if Plan 004 is not in DONE status.

---

## Purpose

After Hax discusses an assessed saved job, the user says naturally "yeah, skip it," "save this one," "maybe," "I want to apply," or corrects an earlier choice. Hax records the user's decision against the exact job and track. A later session can retrieve and discuss it.

This plan delivers the next stage from `discussion/004-minimal-job-native-harness.md` Stage 3: one saved product decision. It builds on Plan 004's Job, JobAssessment, durable tool execution boundary, and immutable session configuration.

---

## Architecture invariants

1. **Assessments and decisions stay separate.** `JobAssessment` is Hax's analysis. `JobDecision` is the user's choice. They live in different tables and different tools. Hax may recommend, the user decides.
2. **Decisions are append only.** Correction appends a new row. History is retained. Latest is a projection by monotonic sequence column.
3. **'apply' records intent only.** It does not submit, contact, send, queue, create a pack, or imply application happened. It is a typed marker saying "the user intends to pursue this."
4. **Only a direct current user statement can create a decision.** Hax's recommendation in a `JobAssessment` is not a user decision. The model is instructed to call `record_job_decision` only when the user has directly stated a decision in natural language.
5. **Natural language, not rigid intent router.** The model parses the user's intent from natural conversation. No fixed command syntax, no keyword matching in the terminal or session.
6. **Conversation recall from employment state.** Later turns/sessions retrieve decisions from the employment store, not only transcript memory. `get_job` response includes latest assessment and latest decision for the active track (Plan 005 extends Plan 004's output).
7. **Resume keeps same person/track configuration from Plan 004.** No changes to the session configuration mechanism.
8. **Agent core changes only when Plan 005 exposes a real gap.** No generic workflow engine, no approvals, no extra tool metadata beyond Plan 004, no context compaction.
9. **Employment tool handlers must not import/query SessionStore.** The handler receives `user_message_id` from `ToolExecutionContext` and `track_id` from its `EmploymentHost` closure. There is no cross database FK and no atomic authorization claim. The linkage is audit provenance, not semantic authorization.

---

## Phase 0: Preflight

**Files changed:** none

1. Confirm Plan 004 is in DONE status.
2. Confirm `git status --short` shows no unexpected modified tracked files.
3. Run full suite post Plan 004 and record exact pass/fail count.
4. Inspect all callers of `get_job()`, `record_job_assessment()`, `CareerStore`, `JobAssessment`, and `ToolExecutionContext` before changing shared behavior.

**STOP** if Plan 004 is not accepted or the worktree is dirty.

---

## Phase A: Typed JobDecision model and store

### A.1 New Pydantic model

**File:** `src/haxjobs/employment/schema.py` (modify)

Add after `JobAssessment`:

```python
class JobDecision(BaseModel):
    """A user's decision about a job: typed, append only, linked to durable user message."""
    decision_id: str                   # stable ID derived from tool_call_id
    job_id: str
    track_id: str
    tool_call_id: str                  # idempotency key; decision_id is derived from this
    source_user_message_id: str        # links back to the durable UserMessage (audit provenance)
    label: Literal["apply", "maybe", "save", "skip", "reject"]
    reason: str = ""                   # optional concise user stated reason; must not be invented by Hax
    sequence: int | None = None        # store-populated output-only; never model/tool input
    created_at: str = Field(default_factory=_utcnow)
```

Field meanings:

- `apply`: user intends to pursue this role. Records intent only. No submission, contact, or side effect.
- `maybe`: user is unsure, wants to revisit.
- `save`: user wants to keep this job for later consideration.
- `skip`: user has decided not to pursue.
- `reject`: user explicitly rejects this role (stronger than skip).

`decision_id` uses `make_stable_id("dec", tool_call_id)` from `employment/identifiers.py` (shared with Plan 004). The `tool_call_id` has a UNIQUE constraint for idempotency. `sequence` is `INTEGER PRIMARY KEY AUTOINCREMENT` in SQLite, populated by the store, never supplied by model/tool input.

### A.2 Store additions

**File:** `src/haxjobs/employment/store.py` (modify)

A.2.1 Add DDL:

```sql
CREATE TABLE IF NOT EXISTS job_decisions (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    track_id TEXT NOT NULL REFERENCES career_tracks(track_id) ON DELETE CASCADE,
    tool_call_id TEXT NOT NULL UNIQUE,
    source_user_message_id TEXT NOT NULL,
    label TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
```

A.2.2 Latest/history order uses the `sequence` column (SQLite `INTEGER PRIMARY KEY AUTOINCREMENT`). The store INSERT omits `sequence` (SQLite auto-assigns it) and reads it back via `lastrowid`. Pydantic model uses `sequence: int | None = None` as store-populated output metadata.

```python
def upsert_decision(self, decision: JobDecision) -> JobDecision | IdempotencyConflict:
    """Transaction: check for duplicate tool_call_id, insert if new."""
    # Uses BEGIN IMMEDIATE or one sqlite with self._conn transaction around lookup+insert.
    # Same call_id + identical semantic payload (excluding generated ID, sequence, created_at)
    #   -> return existing row with replay:true indicator.
    # Same call_id + different payload -> return typed IdempotencyConflict (from employment layer),
    #   write nothing. No raw sqlite error reaches the model. Current single-process assumption noted.

def get_latest_decision(self, job_id: str, track_id: str) -> dict | None:
    """Return the most recent decision by sequence DESC."""

def list_decisions(self, job_id: str, track_id: str) -> list[dict]:
    """All decisions for a job/track pair, ordered by sequence ASC (oldest first)."""
```

### A.3 Tests

**File:** `tests/test_job_actions.py` (modify)

```python
def test_record_decision_and_retrieve_latest():
    """Record a decision, retrieve it as latest."""

def test_decision_idempotent_replay_same_payload():
    """Same call_id + same payload returns existing row."""

def test_decision_idempotency_conflict_different_payload():
    """Same call_id + different payload returns typed conflict, writes nothing."""

def test_decision_correction_appends_not_mutates():
    """Skip then save -> two rows, latest is save, history preserved."""

def test_decision_labels_are_restricted():
    """Invalid label raises ValidationError."""

def test_latest_decision_uses_sequence():
    """Three decisions: latest by sequence DESC is returned."""

def test_apply_label_has_no_side_effect():
    """apply label creates a row, does not submit, contact, or send."""

def test_reason_not_invented():
    """When reason is empty string, it stays empty. Hax does not fill it."""
```

---

## Phase B: Employment actions and tools

### B.1 Plain Python actions

**File:** `src/haxjobs/employment/job_actions.py` (modify)

Add:

```python
def record_decision(
    store: CareerStore,
    decision: JobDecision,
) -> JobDecision | IdempotencyConflict:
    """Append a user decision. Returns existing or conflict on duplicate tool_call_id."""

def get_latest_decision(store: CareerStore, job_id: str, track_id: str) -> JobDecision | None: ...

def list_decisions(store: CareerStore, job_id: str, track_id: str) -> list[JobDecision]: ...
```

B.1.1 Update `get_job()` action to include latest assessment and latest decision. Plan 004's `get_job` returns latest assessment only. Plan 005 extends the output:

```python
def get_job(store: CareerStore, job_id: str, track_id: str | None = None) -> dict:
    """Retrieve a saved job with latest assessment and latest decision for the active track."""
    job = ...  # existing logic
    result = job.model_dump()
    if track_id:
        result["latest_assessment"] = get_latest_assessment(store, job_id, track_id)
        result["latest_decision"] = get_latest_decision(store, job_id, track_id)
    return result
```

### B.2 New tool: record_job_decision

**File:** `src/haxjobs/employment/tools.py` (modify)

Add tool definition:

- **`record_job_decision(job_id, label, reason)`**: `EffectKind.INTERNAL_WRITE`, `retry_safe=False`

Input model:

```python
class RecordJobDecisionInput(BaseModel):
    job_id: str = Field(description="The stable job ID, e.g. 'job-49'")
    label: Literal["apply", "maybe", "save", "skip", "reject"] = Field(
        description="The user's decision label"
    )
    reason: str = Field(default="", description="Optional concise user stated reason; leave empty if the user did not state one")
```

The handler:

1. Validates `label` is one of the five allowed values (Pydantic handles this)
2. Validates `job_id` exists in the jobs table via `CareerStore`
3. Receives `user_message_id` from `ToolExecutionContext.user_message_id` (created by agent core from the already persisted current UserMessage; the handler trusts this domain free context guarantee)
4. Receives `track_id` from its `EmploymentHost` closure (wired at tool registration time; the model cannot supply it)
5. Constructs `JobDecision` with `decision_id` from `make_stable_id`, `tool_call_id=context.call_id`, `source_user_message_id=context.user_message_id`
6. Calls `job_actions.record_decision()` which uses a transaction for check+insert
7. Same call_id + same payload: returns existing row as idempotent replay
8. Same call_id + different payload: returns typed idempotency_conflict as structured tool error

### B.3 No cross layer store access; v1 semantic guard

The handler does **not** import or query `SessionStore`. The `source_user_message_id` and `track_id` are **not model inputs**. The input model contains only `job_id`, `label`, and `reason`. The handler receives `user_message_id` from `ToolExecutionContext.user_message_id` (created by agent core from the already persisted current `UserMessage`; the handler trusts this domain free context guarantee) and `track_id` from its `EmploymentHost` closure (wired at tool registration time; the model cannot supply it).

There is no cross database FK and no atomic authorization claim. This is audit provenance, not semantic authorization. The model cannot supply `user_message_id` or `track_id`.

**Direct user authority is enforced by prompt/tool description plus behavior tests as the v1 semantic guard.** This is not deterministic natural language authorization. Internal decisions are reversible append only records. Do not falsely claim deterministic authorization.

### B.4 Update get_job tool

Update `get_job` output model to include `latest_assessment` and `latest_decision` fields (both nullable). The `track_id` comes from the `EmploymentHost` closure, not the model.

### B.5 Tests

**File:** `tests/test_employment_tools.py` (modify)

```python
@pytest.mark.asyncio
async def test_record_decision_writes_and_retrieves():
    """record_job_decision writes a row; get_latest_decision returns it."""

@pytest.mark.asyncio
async def test_record_decision_requires_valid_label():
    """Invalid label returns ok=False with validation error."""

@pytest.mark.asyncio
async def test_record_decision_requires_existing_job():
    """Nonexistent job_id returns ok=False."""

@pytest.mark.asyncio
async def test_record_decision_links_user_message():
    """Decision.source_user_message_id matches context.user_message_id."""

@pytest.mark.asyncio
async def test_record_decision_idempotent_replay():
    """Same call_id twice with same payload -> one row, first returned."""

@pytest.mark.asyncio
async def test_record_decision_idempotency_conflict():
    """Same call_id + different payload -> conflict, no write."""

@pytest.mark.asyncio
async def test_get_job_includes_latest_decision():
    """After recording a decision, get_job returns it in latest_decision field."""

@pytest.mark.asyncio
async def test_model_cannot_supply_track_id():
    """Tool input model has no track_id field; it comes from EmploymentHost closure."""

@pytest.mark.asyncio
async def test_model_cannot_supply_user_message_id():
    """Tool input model has no user_message_id field; it comes from context."""
```

---

## Phase C: User authority and truthful interpretation

### C.1 The model must not save its own recommendation as user choice

The `record_job_decision` tool description must explicitly instruct the model:

```
Use this tool ONLY when the user has directly stated their decision about a job in natural language.

Examples of valid triggers:
- "yeah, skip it"
- "save this one"
- "I want to apply"
- "maybe, I'll think about it"
- "actually no, I'll apply after all" (correction: appends a new decision)

DO NOT call this tool:
- To record your own recommendation as if the user decided it
- When the user has not yet expressed a decision
- When it is unclear which job the user is referring to: ask first
```

The handler itself cannot enforce this distinction because it only sees the structured arguments. The prompt is the primary guard. The `source_user_message_id` linkage means every decision is traceable to a specific user message, which provides auditability.

### C.2 Natural language, no rigid intent router

The CLI and terminal do not inspect user text for keywords like "skip" or "apply." The model parses the user's intent from the full conversation context. If the reference is ambiguous ("skip it" with multiple discussed jobs), the model asks "Which job did you mean? We discussed job 49 and job 328." rather than guessing or silently picking.

### C.3 The reason field is optional and concise

The model may fill `reason` with a concise summary of the user's stated reasoning (e.g., "role mismatch with backend track"). It must not invent a rationale the user did not express. If the user just said "skip it" with no explanation, `reason` must be empty. The handler and model description enforce this: reason defaults to `""` and the description says "leave empty if the user did not state one."

### C.4 Tests

**File:** `tests/test_trajectory_job_328.py` (modify)

```python
@pytest.mark.asyncio
async def test_model_recommendation_not_saved_as_decision():
    """After job assessment, no decision exists until user explicitly states one."""

@pytest.mark.asyncio
async def test_decision_traceable_to_user_message():
    """Decision.source_user_message_id points to the specific user message."""

@pytest.mark.asyncio
async def test_reason_empty_when_user_says_skip_only():
    """User says 'skip it' with no reason -> reason field is empty, not invented."""
```

---

## Phase D: Conversation recall

### D.1 Retrieving decisions from employment state

When the user asks "what did I decide about job 49?", the model can:

1. Call `get_job("job-49")`: the response already includes `latest_decision`
2. Or call a dedicated `list_decisions` tool if the user asks about decision history

If no decision exists, `get_job` returns `latest_decision: null`. Hax says "You have not made a decision about this job yet."

### D.2 No decision dump in system prompt

Decisions are not automatically included in career context. They are retrieved on demand through tools. This prevents stale or irrelevant decisions from filling the context window.

### D.3 Resume across sessions

A later session with the same configuration (same person_id, same track_id) can call `get_job("job-49")` and receive the same `latest_decision` from the employment store. The conversation transcript may be empty (new session), but the employment state persists.

### D.4 Tests

**File:** `tests/test_job_decisions.py` (create)

```python
def test_decision_survives_new_session():
    """Decision written in session A is visible via get_job in session B."""

def test_latest_decision_after_correction():
    """Skip -> Save = two rows, latest is Save by seq order."""

def test_get_job_without_decision():
    """get_job returns latest_decision=None when no decision exists."""

def test_list_decisions_includes_history():
    """list_decisions returns all decisions for job/track, oldest first by seq."""
```

---

## Phase E: Acceptance trajectories

### E.1 Job 49 assessed skip; user agrees

```text
Given: Job 49 assessed as "skip" (constraint mismatch)
Given: Session with person_id and track_id configuration
When: User says "yeah, skip it"
Then:
  1. record_job_decision(job_id="job-49", label="skip", reason="") is called
  2. Exactly one linked decision row is saved
  3. source_user_message_id links to the "yeah, skip it" user message
  4. Natural reply acknowledges the decision
  5. Resume session, ask "what did I decide about job 49?"
  6. Hax calls get_job, sees latest_decision=skip, reports it
```

Test: `tests/test_trajectory_job_328.py` (modify/add)

```python
@pytest.mark.asyncio
async def test_job_49_skip_decision_trajectory():
    """Full fake trajectory: assess -> user skips -> decision persisted -> resume retrieves."""

@pytest.mark.asyncio
async def test_skip_decision_survives_resume():
    """Close and resume: decision is still retrievable."""
```

### E.2 User corrects skip to save

```text
Given: Job 49 decision = skip exists
When: User says "actually save this one"
Then:
  1. record_job_decision(label="save") appends new row
  2. History has two rows: [skip, save]
  3. get_latest_decision returns save
  4. list_decisions shows both in order
```

Test:

```python
@pytest.mark.asyncio
async def test_correction_appends_new_decision():
    """Skip then Save: two rows, latest is Save, old skip preserved."""
```

### E.3 Model recommends but user has not decided

```text
Given: Job 328 assessed as "needs_more_information"
When: User says "ok, interesting" (not a decision statement)
Then: No decision row is created
When: User later says "I'll apply for that"
Then: record_job_decision(label="apply") is called
```

Test:

```python
@pytest.mark.asyncio
async def test_no_decision_until_explicit_user_statement():
    """Assessment is not a decision. Non decision user message creates no decision row."""
```

### E.4 Apply label creates no side effect

```text
Given: User says "I want to apply for job 49"
When: record_job_decision(label="apply") is called
Then: Decision row exists with label "apply"
And: No HTTP request, no email, no pack generation, no queue entry
And: Subsequent get_job shows latest_decision.apply = True
```

Test:

```python
@pytest.mark.asyncio
async def test_apply_label_has_no_side_effect():
    """apply label creates decision row, triggers no external action."""
```

### E.5 Ambiguous reference produces no write

```text
Given: Job 49 and Job 328 were both discussed
When: User says "skip it" without specifying which
Then: Model asks "Which job? We discussed job 49 and job 328"
And: No decision row is created
```

This is a behavioral fake trajectory test. The fake model is scripted to respond with a clarification question instead of a tool call. The test asserts:

- **No `ToolCallMessage`** for `record_job_decision` appears in the session history
- **Zero decision rows** exist in the store after the turn

Do not script a positive tool request and then claim ambiguity prevention.

Test:

```python
@pytest.mark.asyncio
async def test_ambiguous_reference_no_tool_call():
    """Ambiguous 'skip it' -> model asks for clarification, no decision tool call, no decision row."""
```

---

## Phase F: Agent core changes

### F.1 Principle

Plan 005 should require minimal agent core changes. The durable tool execution boundary, `ToolExecutionContext`, `persist_message` callback, session configuration, and measurement are all delivered in Plan 004.

### F.2 Expected: zero agent core changes

The `record_job_decision` handler receives everything it needs from Plan 004 interfaces:

- `user_message_id` from `ToolExecutionContext.user_message_id` (created by agent core from the already persisted current UserMessage)
- `track_id` from the `EmploymentHost` closure at tool registration time
- `call_id` from `ToolExecutionContext.call_id` for idempotency

The handler does not import `SessionStore`. The decision action stores `source_user_message_id` as audit provenance, trusting the domain free context guarantee.

If this holds, document explicitly in the report: "Plan 005 required zero agent core changes. All new behavior was added through employment models, actions, and tool handlers using the interfaces delivered in Plan 004."

---

## Rollback and recovery

### Rollback design

1. **Append only decisions** (Phase A): no data is mutated. Correction appends a new row. Old decisions are intact. Rollback means stop writing decisions.
2. **Idempotent tool execution** (Phase A/B): duplicate `tool_call_id` with same payload returns existing row. No duplicate writes.
3. **Idempotency conflict** (Phase A/B): duplicate `tool_call_id` with different payload writes nothing and returns a structured error. No silent data corruption.
4. **Separate storage** (Phase A): decisions live in the career DB, separate from session DB. Session DB corruption does not lose decisions.
5. **No cross DB FK** (Phase B): `source_user_message_id` is audit provenance, not a constraint. Deleting a session does not cascade to decisions.

### Recovery scenarios

- **Wrong decision:** Record a new corrective decision. History preserves the old one. Latest projection reflects the correction.
- **Duplicate tool call:** Idempotency check returns existing row or conflict error. No duplicate write.
- **Session lost:** New session with same configuration retrieves decisions from career DB via `get_job`.

---

## Files in scope

### Create

```text
tests/test_job_decisions.py
```

### Modify

```text
src/haxjobs/employment/schema.py: JobDecision model
src/haxjobs/employment/store.py: job_decisions table, upsert_decision, get_latest_decision, list_decisions
src/haxjobs/employment/job_actions.py: record_decision, get_latest_decision, list_decisions; update get_job to include latest_decision
src/haxjobs/employment/tools.py: record_job_decision tool; update get_job output model
tests/test_job_actions.py: decision action tests
tests/test_employment_tools.py: decision tool tests
tests/test_trajectory_job_328.py: decision trajectory tests
```

### Modify only if a focused test proves it is required

**STOP**: If a focused test proves agent-core work is required, **stop and reconcile Plan 005** rather than edit agent-core ad hoc. The agent-core files below are in Do Not Touch; the durable tool execution boundary, `ToolExecutionContext`, `persist_message` callback, session configuration, and measurement were all delivered in Plan 004 and Plan 005 is designed to require zero agent-core changes.

```text
src/haxjobs/employment/composition.py
src/haxjobs/employment/host.py
src/haxjobs/employment/context.py
```

### Do not touch

```text
state/
src/haxjobs/model/
src/haxjobs/agent_core/
src/haxjobs/employment/migration.py
src/haxjobs/employment/fixtures.py
src/haxjobs/employment/identifiers.py
src/haxjobs/employment/job_source.py
src/haxjobs/interfaces/
src/haxjobs/cli.py
src/haxjobs/config.py
src/haxjobs/cv_variants/
tests/test_career_graph.py
tests/test_conversation_messages.py
tests/test_live_events.py
tests/test_model_streaming.py
tests/test_session_store.py
tests/test_turn_runtime.py
tests/test_session.py
tests/test_employment_host.py
tests/test_terminal.py
tests/test_terminal_pty.py
tests/test_durable_tool_effects.py
pyproject.toml
uv.lock
haxjobs.toml
discussion/
```

Plan 005 must not carry the Stage 0/1 runtime deletion. That deletion is Plan 004 Phase I.

---

## Explicitly deferred

- Employability roadmaps and learning pattern analysis
- Application packs and submission mechanics
- Outreach and messaging
- Discovery, watches, background work, schedulers
- Arbitrary URL fetching beyond job fixture hosts
- Subagents and coding workspaces
- UI changes beyond the Plan 003 terminal
- Approval framework for `apply` transitioning from intent to action
- Context compaction
- Token budgets
- Any generic workflow engine
- Source observation history
- Cross process session locking
- Learning engine

---

## Verification floor

```bash
# Full suite
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/

# Specific test files
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_job_actions.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_employment_tools.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_job_decisions.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_trajectory_job_328.py
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_durable_tool_effects.py

# Compile and lock
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check

# CLI
PYTHONPATH=src:. uv run -- haxjobs --help
PYTHONPATH=src:. uv run -- haxjobs chat --help
```

No test may call a live model or network. No test may mutate the operator's real databases.

---

## STOP conditions

STOP and report instead of guessing if:

1. Plan 004 is not in DONE status
2. Existing tests regress beyond the known post Plan 004 baseline
3. `tool_call_id` uniqueness cannot distinguish two decisions in the same turn (each tool call gets a unique call_id; verify this)
4. The model cannot reliably distinguish "yeah, skip it" from "maybe I should skip it" (test with fake model trajectories)
5. `get_job` output model change breaks the tool schema contract from Plan 004
6. A proposed change requires agent core to import employment modules
7. The `apply` label's "no side effect" constraint cannot be verified by a deterministic test
8. The idempotency conflict detection cannot reliably distinguish same payload from different payload

---

## Deliverables

**Folder:** `deliverables/005-job-decisions/`

Required contents:

```text
README.md
plan.md                      (copy of this file)
report.md                    (evidence backed completion report)
review-ledger.md             (reviewer findings and decisions)
manual-proof.md              (controller owned safe run IDs, metadata, rubric results: not raw PTY transcripts or career/model text)
decision-model.drawio        (JobDecision, JobAssessment separation, decision lifecycle)
decision-model.png
recall-flow.drawio           (get_job -> latest_assessment + latest_decision)
recall-flow.png
```

### Draw.io requirements

Two clean diagrams of the actual post plan system:

1. **decision-model.drawio:** Job, JobAssessment, JobDecision: separation of concerns, append only correction, tool_call_id as idempotency key, source_user_message_id linkage. 5 to 7 groups, under 35 cells, thick orthogonal arrows, no file paths.
2. **recall-flow.drawio:** Session creates decision -> employment store persists -> new session calls get_job -> returns job + latest assessment + latest decision. 5 to 7 groups, under 35 cells, thick orthogonal arrows, no file paths.

### Report requirements

The `report.md` must cover:

1. What changed from Plan 004 baseline
2. Every file created or modified with exact paths
3. Tests written and exact pass/fail counts
4. Manual commands and observed behavior (controller owned safe metadata)
5. Diagrams produced
6. Reviewer findings and repairs
7. Anything skipped or deferred
8. Current risks: model reliability on decision parsing, apply label staying as intent only, decision history growth over time
9. Final commit SHA (recorded by controller, not self claimed)
10. Explicit confirmation of zero agent core changes (or list the minimal changes if any)

---

## Execution protocol

### Writer

One fresh DeepSeek V4 Pro writer in an isolated worktree, starting from the accepted Plan 004 commit. The writer reads the plan and live source before editing, is the only source code writer, uses tests before non trivial implementation, commits the implementation, and produces the full deliverable folder.

### Initial review team

Three independent fresh DeepSeek V4 Flash reviewers:

1. **Architecture and scope**: maps Plan 005 phases to code and tests, verifies Plan 004 dependency, finds missing deliverables or unapproved scope
2. **Correctness, safety, privacy, and tests**: inspects decision idempotency, user_message_id linkage, apply no side effect, correction not mutation, natural language boundary, agent core isolation
3. **Deliverables, diagrams, and manual proof**: checks report accuracy, Draw.io artifacts, manual proof, decision/assessment separation

Reviewers are read only. They inspect the actual diff, run checks, cite file and line evidence, return APPROVED or NEEDS FIXES.

### Repair rounds

- One fresh DeepSeek V4 Pro writer applies only accepted findings
- Run full verification floor again
- Three new independent reviewers against the repaired commit
- Maximum two repair rounds
- Never merge a known correctness, security, or data loss blocker just to obey the cap

### Merge gate

- Full suite passes
- Manual interaction proof is complete
- Diagrams parse, export, and pass visual review
- Three DeepSeek V4 Flash reviewers approve the same commit
- Review ledger records findings and decisions
- Plan 004 is merged before Plan 005

---

*Plan 005 delivers the first user product decision through the conversational runtime: typed, append only, linked to durable user messages, retrievable across sessions. Depends on accepted Plan 004. Apply records intent only. Current plans stay TODO and do not claim unbuilt work.*
