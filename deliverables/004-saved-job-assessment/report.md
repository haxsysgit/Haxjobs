# Plan 004: Saved Job Assessment Implementation Report

## Status

**IMPLEMENTED — FINAL REVIEW PENDING** — All 238 automated tests pass in this worktree with no private fixture. The focused repair based on exact `285f424` addresses the seven accepted correctness blockers. Final review remains pending and is not approved. Live provider verification is deferred (controller-owned).

## Files created

| Path | Purpose |
|------|---------|
| `src/haxjobs/employment/identifiers.py` | Stable deterministic ID helper (`make_stable_id`) |
| `src/haxjobs/employment/job_actions.py` | Plain Python actions: import, get, record, assess jobs |
| `src/haxjobs/employment/tools.py` | Employment tool definitions (get_job, inspect_job_source, record_job_assessment) |
| `tests/test_job_actions.py` | Job import, source snapshot, migration, assessment, idempotency tests |
| `tests/test_employment_tools.py` | Tool dispatch tests, including top-level idempotency conflict failure (7 tests) |
| `tests/test_trajectory_job_328.py` | Full no-network fake trajectory + resume test (2 tests) |
| `tests/test_job_source.py` | Blocking DNS/transport event-loop heartbeat, DNS timeout, string external-reference, and non-global-address regressions |
| `tests/test_durable_tool_effects.py` | Persistence order, dangling calls, idempotency, scope, cleanup (9 tests) |
| `tests/test_cli.py` | Deterministic rejection of conflicting chat modes/scope flags and implicit migration fixtures (4 tests) |

## Files modified

| Path | Changes |
|------|---------|
| `src/haxjobs/agent_core/tools.py` | Added `ToolExecutionContext`, `EffectKind`, `ToolDefinition` metadata, handler now takes `(input, context)` |
| `src/haxjobs/agent_core/turn.py` | Added `persist_message` callback (required), `user_message_id`, `TurnResult` usage/input_characters fields, truthful interrupted partial assistant persistence, and live failure events for every terminal message-persistence boundary |
| `src/haxjobs/agent_core/session.py` | `persist_message` wiring, dangling call detection on resume, measurement recording on every turn exit path |
| `src/haxjobs/agent_core/session_store.py` | Added `session_configuration` table, `turn_measurements` table, nonblank opaque configuration storage, `record_measurement()`, and config round-trip methods |
| `src/haxjobs/employment/schema.py` | Added `Job`, `ConstraintCheck`, `JobAssessment` models; `CareerFixture` now requires `person_id`, `person_name`, `track_name` |
| `src/haxjobs/employment/store.py` | Added `jobs` and `job_assessments` tables, `list_people()`, job/assessment CRUD methods; `link_skill_evidence` made idempotent with `ON CONFLICT DO NOTHING` |
| `src/haxjobs/employment/migration.py` | Stable IDs from `identifiers.py`, person name from fixture, contradictory gap prevention, explicit fixture path requirement |
| `src/haxjobs/employment/fixtures.py` | Required `person_id`, `person_name`, `track_name` on `CareerFixture` |
| `src/haxjobs/employment/host.py` | Tools moved to `employment/tools.py`, uses `build_employment_tool_registry()` |
| `src/haxjobs/employment/context.py` | Evidence content included (not just labels), privacy label, verification flag, deduplication, character caps |
| `src/haxjobs/employment/composition.py` | Session configuration (immutable person/track scope), person/track auto-selection, cleanup on failure |
| `src/haxjobs/employment/job_source.py` | Added `fetch_from_job()` accepting Job rows; string-safe references, bounded off-loop DNS await, resolver, transport, connection, and reads run via `asyncio.to_thread` |
| `src/haxjobs/cli.py` | Added `--person-id`, `--track-id` to chat; removed experiment review-job subcommand |
| `src/haxjobs/agent_core/__init__.py` | Removed deleted module exports |
| `src/haxjobs/employment/__init__.py` | Removed `review_job` exports |
| `src/haxjobs/interfaces/__init__.py` | Removed `experiment_cli` export |
| `tests/test_career_graph.py` | Uses synthetic fixture; added migration integrity tests (deterministic IDs, person name, contradictory gaps, idempotent links, required fields) |
| `tests/test_turn_runtime.py` | Removed duplicate `_TestOutput`; added ToolExecutionContext, persistence failure event, cancel event, and provider-cancelled failure tests; updated all handler signatures to `(input, ctx)` |
| `tests/test_session.py` | Added unconfigured session, history-read failure settlement, interrupted partial-history, dangling call, no duplicate, no auto-retry, idempotent resume, measurement, and provider-cancelled settlement tests |
| `tests/test_employment_host.py` | Added scope selection tests (single/multi/zero person/track), evidence content tests |
| `tests/test_session_store.py` | Added opaque string/list/arbitrary-text configuration, blank validation, round-trip, transaction, duplicate tests |
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
238 passed (full suite; runtime varies by environment)
```

Verified: `uv lock --check` ok, `py_compile` all src/ and tests/ ok, `git diff --check` ok.

Exact collected/tested per-file count (from `pytest --collect-only -q tests/`, 238 collected and 238 passed):
- `tests/test_career_graph.py`: 28
- `tests/test_conversation_messages.py`: 20
- `tests/test_durable_tool_effects.py`: 9
- `tests/test_employment_host.py`: 20
- `tests/test_employment_tools.py`: 7
- `tests/test_job_actions.py`: 13
- `tests/test_cli.py`: 4
- `tests/test_job_source.py`: 4
- `tests/test_live_events.py`: 19
- `tests/test_model_streaming.py`: 11
- `tests/test_session.py`: 34
- `tests/test_session_store.py`: 22
- `tests/test_terminal.py`: 14
- `tests/test_terminal_pty.py`: 2
- `tests/test_trajectory_job_328.py`: 2
- `tests/test_turn_runtime.py`: 29

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
- `conversation-trajectory.drawio` (21 cells) / `.png` (464×474) — Full job review trajectory: user → get_job → inspect → assess → resume; resume reads current Job + latest assessment through get_job and never records a new assessment

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
3. **Stale doc references.** Test counts were corrected in the earlier repair commit; `--ignore=tests/test_terminal_pty.py` removed; deleted module/CLI descriptions corrected; `state/experiments/` path removed from user-facing docs.

Architecture and correctness reviews were approved on the initial repair candidate with one nonblocking close observation (test-career-store exercises synthetic fixture only; real private DB migration is controller-owned).

## Controller verification findings (0766d56)

Initial controller verification round identified three blocking findings against `0cbff2b`, all repaired at `0766d56`:

1. **PTY test isolation (tests/test_terminal_pty.py):** Both `test_terminal_pty_enter_submits_and_escape_interrupts` and `test_terminal_pty_escape_during_streaming_interrupts` defaulted `HAXJOBS_CAREER_DB` to `state/career_graph.db`, violating Plan 004 Phase A's isolated synthetic-test rule. Fixed by adding `_isolated_career_db()` helper that creates a temp career DB migrated from `tests/fixtures/job_review/career.json` and cleaning up after each test.
2. **Missing PNG exports:** Three `.drawio` files had no PNG exports. All three exported via local `/opt/drawio/drawio -x -f png`. Each PNG verified with valid signature and nonzero IHDR dimensions.
3. **Report metadata:** Report claimed COMPLETE but listed PTY tests as "fail due to environment" and PNGs as deferred. Corrected in the earlier repair commit to report the exact passing suite and present PNGs.

## Current correctness repairs addressed

- `SessionStore.create_session` requires only nonblank opaque text and preserves strings, lists, and arbitrary values unchanged; employment composition validates its expected scope JSON. Historic unconfigured rows fail clearly on resume.
- Tool results are persisted before lifecycle completion/failure events. Failed result persistence stops model progression, emits persistence failure/terminal events, and leaves dangling-call reconciliation intact.
- Runtime source inspection accepts only saved Job data; the fixture-era `fetch(JobFixture, ...)` entry point and Stage 1 experiment wording are gone.
- Assessment input no longer accepts a model track scope. Registry dispatch binds the active track and a two-track regression proves no cross-track/person write.
- Stream cancellation preserves a truthful interrupted partial assistant message, including provider-neutral `RESPONSE_FAILED` events with category `cancelled`; external tool cancellation cancels and joins active tool work, persists only a truthful cancellation failure when possible, emits one interruption, and records measurement/settlement.
- Manual proof states that CLI `--fake` is text-only; saved-job tool trajectory proof is automated and deterministic.
- All three final diagram XML files use orthogonal connectors; the trajectory now routes resume through the `get_job` read path for the current Job and latest assessment, with no assessment write. PNGs were re-exported and checked for valid dimensions.
- Source inspection, bounded DNS offloading, string external references, deterministic trajectory, job-column migrations, idempotency, scope ownership, and initial-message persistence remain covered by deterministic focused tests.

## Focused correctness repair pass

Based on exact `285f424`, this pass repairs: `ipaddress.is_global` source validation; cancellation outcome inspection after handler cancellation; failed session read/setup settlement; mutually exclusive chat mode and scope flags; top-level idempotency conflict envelopes; opaque SessionStore configuration; and the stale migration fixture fallback. Deterministic regressions cover each code blocker. Controller-owned manual/live proof remains honestly deferred.

## Commit

Plan 004 focused correctness repair commit applied at this worktree. Final review is pending, not approved. Report intentionally omits its containing commit SHA; controller records the final SHA after review.
