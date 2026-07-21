# Plan 004: Saved Job Assessment Implementation Report

## Status

**COMPLETE** — All 216 automated tests pass in an isolated fresh worktree with no private fixture. Three independent Flash reviews completed (architecture APPROVED, correctness/privacy APPROVED with nonblocking observation, deliverables blockers repaired). Fresh final review is controller-owned and pending. Live provider verification deferred (controller-owned).

## Files created

| Path | Purpose |
|------|---------|
| `src/haxjobs/employment/identifiers.py` | Stable deterministic ID helper (`make_stable_id`) |
| `src/haxjobs/employment/job_actions.py` | Plain Python actions: import, get, record, assess jobs |
| `src/haxjobs/employment/tools.py` | Employment tool definitions (get_job, inspect_job_source, record_job_assessment) |
| `tests/test_job_actions.py` | Job import, assessment, idempotency tests (9 tests) |
| `tests/test_employment_tools.py` | Tool dispatch tests (7 tests) |
| `tests/test_trajectory_job_328.py` | Full fake trajectory + resume test (2 tests) |
| `tests/test_durable_tool_effects.py` | Persistence order, dangling calls, idempotency, scope (9 tests) |

## Files modified

| Path | Changes |
|------|---------|
| `src/haxjobs/agent_core/tools.py` | Added `ToolExecutionContext`, `EffectKind`, `ToolDefinition` metadata, handler now takes `(input, context)` |
| `src/haxjobs/agent_core/turn.py` | Added `persist_message` callback (required), `user_message_id`, `TurnResult` usage/input_characters fields, ToolCallMessage persisted before handler, ToolResultMessage persisted immediately after handler, AssistantMessage persisted at boundary |
| `src/haxjobs/agent_core/session.py` | `persist_message` wiring, dangling call detection on resume, measurement recording on every turn exit path |
| `src/haxjobs/agent_core/session_store.py` | Added `session_configuration` table, `turn_measurements` table, `record_measurement()`, config round-trip methods |
| `src/haxjobs/employment/schema.py` | Added `Job`, `ConstraintCheck`, `JobAssessment` models; `CareerFixture` now requires `person_id`, `person_name`, `track_name` |
| `src/haxjobs/employment/store.py` | Added `jobs` and `job_assessments` tables, `list_people()`, job/assessment CRUD methods; `link_skill_evidence` made idempotent with `ON CONFLICT DO NOTHING` |
| `src/haxjobs/employment/migration.py` | Stable IDs from `identifiers.py`, person name from fixture, contradictory gap prevention |
| `src/haxjobs/employment/fixtures.py` | Required `person_id`, `person_name`, `track_name` on `CareerFixture` |
| `src/haxjobs/employment/host.py` | Tools moved to `employment/tools.py`, uses `build_employment_tool_registry()` |
| `src/haxjobs/employment/context.py` | Evidence content included (not just labels), privacy label, verification flag, deduplication, character caps |
| `src/haxjobs/employment/composition.py` | Session configuration (immutable person/track scope), person/track auto-selection, cleanup on failure |
| `src/haxjobs/employment/job_source.py` | Added `fetch_from_job()` accepting Job rows, `asyncio.to_thread` offload for blocking I/O |
| `src/haxjobs/cli.py` | Added `--person-id`, `--track-id` to chat; removed experiment review-job subcommand |
| `src/haxjobs/agent_core/__init__.py` | Removed deleted module exports |
| `src/haxjobs/employment/__init__.py` | Removed `review_job` exports |
| `src/haxjobs/interfaces/__init__.py` | Removed `experiment_cli` export |
| `tests/test_career_graph.py` | Uses synthetic fixture; added migration integrity tests (deterministic IDs, person name, contradictory gaps, idempotent links, required fields) |
| `tests/test_turn_runtime.py` | Removed duplicate `_TestOutput`; added ToolExecutionContext, persist failure, cancel event tests; updated all handler signatures to `(input, ctx)` |
| `tests/test_session.py` | Added unconfigured session, dangling call, no duplicate, no auto-retry, idempotent resume, measurement tests |
| `tests/test_employment_host.py` | Added scope selection tests (single/multi/zero person/track), evidence content tests |
| `tests/test_session_store.py` | Added configuration round-trip, transaction, duplicate test |
| `tests/test_live_events.py` | Updated test that referenced deleted events module |
| `tests/fixtures/job_review/career.json` | Added `person_id`, `person_name`, `track_name` |
| `AGENTS.md` | Updated for conversational runtime |
| `docs/HAXJOBS.md` | Updated current state and limitations |
| `docs/PRODUCT.md` | Updated what-is-built section |
| `README.md` | Updated for Plan 004 |
| `docs/GETTING_STARTED.md` | Updated with new commands and tools |

## Files deleted (Phase I)

| Path |
|------|
| `src/haxjobs/agent_core/runtime.py` |
| `src/haxjobs/agent_core/types.py` |
| `src/haxjobs/agent_core/events.py` |
| `src/haxjobs/agent_core/artifacts.py` |
| `src/haxjobs/employment/review_job.py` |
| `src/haxjobs/interfaces/experiment_cli.py` |
| `tests/test_stage0_job_review.py` |
| `tests/test_stage1_source_inspection.py` |

## Test results

```
216 passed in 44.87s
```

Verified: `uv lock --check` ok, `py_compile` all src/ and tests/ ok, `git diff --check` ok.

Breakdown:
- `tests/test_career_graph.py`: 28 passed (23 original + 5 new Phase A)
- `tests/test_turn_runtime.py`: 25 passed (20 original + 5 new Phase B)
- `tests/test_session.py`: 28 passed (18 original + 10 new Phase C/D)
- `tests/test_session_store.py`: 21 passed (17 original + 4 new Phase C)
- `tests/test_employment_host.py`: 16 passed (9 original + 7 new Phase C/H)
- `tests/test_job_actions.py`: 12 passed (all new Phase E/F)
- `tests/test_employment_tools.py`: 7 passed (all new Phase G)
- `tests/test_trajectory_job_328.py`: 2 passed (all new Phase K)
- `tests/test_durable_tool_effects.py`: 9 passed (all new Phase K)
- `tests/test_conversation_messages.py`: 10 passed
- `tests/test_live_events.py`: 7 passed
- `tests/test_model_streaming.py`: 5 passed
- `tests/test_terminal.py`: 44 passed
- `tests/test_terminal_pty.py`: 2 passed (isolated temp career DB, synthetic fixture)

## Architecture invariants confirmed

1. **Layer ownership unchanged.** `model` imports no employment. `agent_core` imports no employment. `employment` owns Hax identity, career logic, and employment tools.
2. **Domain-free agent core.** `turn.py`, `session.py`, `tools.py`, `messages.py` contain no job, CV, company, career, assessment, decision, or person name references.
3. **Employment tools in `employment/tools.py`.** Not inline in `EmploymentHost._build_registry`.
4. **Shared plain Python actions.** `job_actions.py` owns import/get/record/list before tool adapters.
5. **CareerStore sole source.** `EmploymentHost` does not read fixture files at runtime.
6. **Assessments append-only.** Latest selected by `sequence INTEGER PRIMARY KEY AUTOINCREMENT`. No numeric fit score. No user decision field.
7. **Durable tool execution boundary.** `ToolCallMessage` persisted before handler; `ToolResultMessage` immediately after; persist failure stops turn; dangling calls detected on resume.

## Zero employment imports in agent core

Verified: `grep -r "employment\|career\|job\|assessment" src/haxjobs/agent_core/` returns no employment-specific references. The `ToolExecutionContext` is domain-free (session_id, turn_id, call_id, user_message_id, cancel_event). Generic policy metadata (`EffectKind`, `retry_safe`) travels through `ToolDefinition`.

## Duplicate _TestOutput removal

The `_fake_registry()` helper in `tests/test_turn_runtime.py` had two identical `class _TestOutput(BaseModel)` definitions. Removed as scoped cleanup.

## Diagram deliverables

Three draw.io source files and three exported PNGs, all under 35 cells:
- `employment-models.drawio` (34 cells, 32 non-root) / `.png` (640×524) — Person, CareerTrack, Skill, Evidence, Job, JobAssessment relationships; ConstraintCheck noted as embedded field
- `tool-effects.drawio` (22 cells) / `.png` (744×404) — Durable tool execution boundary, persist failures, dangling call detection
- `conversation-trajectory.drawio` (21 cells) / `.png` (464×474) — Full job review trajectory: user → get_job → inspect → assess → resume

All PNGs exported via `/opt/drawio/drawio -x -f png`. Each has a valid PNG signature and nonzero IHDR dimensions.

## Deferred and skipped

- **Live provider manual run:** Controller-owned. Not performed in this worktree.
- **Real career DB migration:** Requires private fixture with `person_id`, `person_name`, `track_name`.
- **Compaction, summaries, token budgets:** Plan 005 territory.
- **User decisions:** Plan 005.
- **Approvals framework:** Deferred.
- **Source observation history:** Current snapshot only; assessment hash preserves which snapshot was used.
- **Cross-process session locking:** Local single-process limitation documented.
- **DNS rebinding residual risk:** Documented as attended local risk (hostname resolved at fetch time).
- **asyncio.to_thread cancellation:** Cancelling the outer task cannot kill an already-running thread; thread runs to completion or 15s timeout.

## Current risks and known limitations

1. **Process death mid-tool:** If handler completes but ToolResultMessage persistence fails, the persisted ToolCallMessage remains dangling. On resume, synthetic `unknown_outcome` is appended. The model is informed, not confused.
2. **No historical source observations:** Only current snapshot stored. Assessment hash preserves which snapshot was used.
3. **Content-free measurement:** Tokens may be NULL when provider omits usage data.
4. **Fetched text is untrusted evidence:** Returned to model as tool result only, never becomes system instructions.

## Deliverables review (Plan 004 repair)

Three independent Flash reviews identified three deliverable blockers against candidate `0766d56`, all repaired in this commit:

1. **Missing review-ledger.md and manual-proof.md.** Created with factual review record and controller-owned proof procedure + verified `--help` output.
2. **Oversized employment-models.drawio (36 non-root cells).** Simplified to 32 non-root cells. PNG re-exported at 640×524.
3. **Stale doc references.** Test counts updated to 216; `--ignore=tests/test_terminal_pty.py` removed; deleted module/CLI descriptions corrected; `state/experiments/` path removed from user-facing docs.

Architecture and correctness reviews were approved on the initial repair candidate with one nonblocking close observation (test-career-store exercises synthetic fixture only; real private DB migration is controller-owned).

## Controller verification findings (0766d56)

Initial controller verification round identified three blocking findings against `0cbff2b`, all repaired at `0766d56`:

1. **PTY test isolation (tests/test_terminal_pty.py):** Both `test_terminal_pty_enter_submits_and_escape_interrupts` and `test_terminal_pty_escape_during_streaming_interrupts` defaulted `HAXJOBS_CAREER_DB` to `state/career_graph.db`, violating Plan 004 Phase A's isolated synthetic-test rule. Fixed by adding `_isolated_career_db()` helper that creates a temp career DB migrated from `tests/fixtures/job_review/career.json` and cleaning up after each test.
2. **Missing PNG exports:** Three `.drawio` files had no PNG exports. All three exported via local `/opt/drawio/drawio -x -f png`. Each PNG verified with valid signature and nonzero IHDR dimensions.
3. **Report metadata:** Report claimed COMPLETE but listed PTY tests as "fail due to environment" and PNGs as deferred. Corrected to report exact 216 passes and present PNGs.

## Commit

Plan 004 repair commit applied at this worktree. Report intentionally omits its containing commit SHA per Plan 004 conventions; controller records final SHA on acceptance.
