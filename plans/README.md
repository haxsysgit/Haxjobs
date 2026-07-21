# Greenfield HaxJobs implementation plans

Generated on 2026-07-17 from `discussion/` and the pinned Pi/Hermes source study.

This plan set grows HaxJobs through observed job-search slices:

```text
Stage 0 and 1
  observed job review, then one trusted source tool

Plan 003
  career graph, durable conversation, and inline terminal

Plan 004 and 005
  saved job assessment, durable tool effects, then user decisions
```

## Current execution blockers

Plan 004 has one controller-owned prerequisite before its live verification gate:

- update ignored `state/experiments/fixtures/backend-career.json` with required `person_id`, `person_name`, and `track_name`
- keep the private fixture mode `0600`
- automated tests use tracked synthetic fixtures and isolated databases; they must never require or mutate operator state

Other execution facts:

- Plan 004 design baseline: `0c412b0`
- Delivery models: exact `deepseek-v4-pro` writer and exact `deepseek-v4-flash` reviewers
- Product provider: configured and verified outside tracked files
- Plan 005 remains blocked until Plan 004 is accepted and restamped against its final commit

## Execution order and status

| Plan | Title | Priority | Effort | Depends on | Status | Final commit | Report reference | Notes |
|---|---|---:|---:|---|---|---|---|---|
| [001](001-stage0-observed-job-review.md) | Build the Stage 0 observed job review | P1 | L | clean reconciled execution baseline | DONE | `e396fd2` | pending | First no-tool observed job review. |
| [002](002-stage1-source-inspection-loop.md) | Stage 1 bounded source-inspection loop | P1 | L | Plan 001 DONE at a28d5ba | DONE | `6d64624` | deliverables/002-stage1/ | Live runs completed 2026-07-20; Flash reviewers found 0 blockers, 1 minor (code NameError fixed in follow-up). |
| [003](003-career-graph-schema.md) | Career graph schema, persistence, and profile CLI | P1 | M | Plan 002 DONE | DONE | `9ee53be` | deliverables/003-career-graph/ | Career graph retained. The completed plan's Textual TUI was later deleted because it was not an agent interface. |
| [003-corrected](003-career-graph-schema.md) | Career graph and first real conversation (corrected) | P1 | M | Plan 003 career graph DONE | DONE | `d6fa361` | deliverables/003-career-graph/ | Four fresh DeepSeek V4 Pro release reviewers approved the same commit. Real provider PTY conversation and same-session resume passed. Baseline 0c412b0 verified at 217 passed. |
| [004](004-saved-job-assessment-and-durable-tool-effects.md) | Saved job assessment and durable tool effects | P1 | L | Plan 003-corrected DONE | DONE | `8511c0b` | deliverables/004-saved-job-assessment/report.md | 248 tests passed before final documentation count correction. Luna final review found no remaining code blocker after the final repair; controller-owned live provider proof remains deferred. |
| [005](005-user-job-decisions-and-conversation-recall.md) | User job decisions and conversation recall | P1 | L | Plan 004 DONE | TODO | - | - | Typed append-only user decisions linked to durable messages, retrievable across sessions. Apply records intent only. Assessment and decision stay separate. |

The advisor/operator owns this table. Executors do not edit it.

## Deliverable folder convention

Every plan collects its deliverable artifacts into one labelled folder
under `deliverables/<plan-slug>/`: the implementation report, diagram
source and PNG, fixture files, rubric, and a short `README.md`. The
plan text is copied in as `plan.md`. Code in `src/` and test fixtures
in `tests/` stay where they are. Do not symlink; copy sources so the
folder can be archived or shared independently.

Status values:

- `TODO`
- `IN PROGRESS`
- `DONE`
- `BLOCKED: reason`
- `REJECTED: reason`

## Dependency graph

```text
Plan 001: Stage 0
  Job 49 -> human review
  Job 328 -> human review
        |
        v
Plan 002: Stage 1
  inspect_job_source(job_ref) tool
  bounded model-tool loop
        |
        v
Plan 003: Career Graph Schema (corrected)
  tracks, skills, evidence, gaps, persistence, CLI, inline terminal
        |
        v
Plan 004: Saved Job Assessment and Durable Tool Effects
  normalized jobs, typed assessments, durable tool execution,
  immutable session configuration, content-free measurement,
  career migration integrity, Stage 0/1 runtime deletion
        |
        v
Plan 005: User Job Decisions and Conversation Recall
  append-only decisions, natural language parsing,
  cross-session recall, apply-as-intent-only
```

Plans 004 and 005 are written and remain TODO. Plan 004 executes first. Plan 005 must be reconciled and restamped after Plan 004 is accepted.

Tests passing alone do not admit Plan 002. Arinze's completed Job 328 rubric and the Plan 001 report must identify source inspection as the next missing capability.

## Architecture boundary accepted for this wave

The user's current planning instruction explicitly chooses Pi-like architecture and separation of concerns for this build wave.

```text
haxjobs.model
  provider and normalized model boundary

haxjobs.agent_core
  internal messages, bounded execution, tools, events, result

haxjobs.employment
  Hax instructions, career/job context, employment actions

haxjobs.interfaces
  thin CLI now, web and worker later
```

Keep these as modules inside one Python distribution. No package monorepo.

This acceptance resolves the architecture-shape and one-package questions in `discussion/006` for Stage 0 and Stage 1. It does not decide future document workspaces, coding workspaces, or bash isolation.

The deleted legacy agent must not return. Plan 004 removes the remaining Stage 0/1 experiment runtime only after its replacement trajectories pass. Historical plans, reports, fixtures, and deliverables remain as evidence.

## Required delivery team

### Sole writer

- exact model: `deepseek-v4-pro`
- one fresh Pi `worker` session
- isolated git worktree
- only writer
- no implementation delegation
- no fallback

The Pi advisor/orchestrator launches it with an explicit model override, fresh context, the full plan, and the clean worktree path. Runtime metadata must show canonical model ID and session ID.

### Initial independent review team

Three fresh Pi `reviewer` sessions use exact `deepseek-v4-flash` against the same frozen candidate:

1. architecture and scope
2. correctness, safety, privacy, and tests
3. report, draw.io diagram, and manual CLI use

Reviewers are read-only and do not see each other's findings.

### Repair and final review

1. The Pi advisor/orchestrator adjudicates every finding as accepted, rejected, or duplicate.
2. The same Pro writer fixes accepted items, updates tests and the tracked report, reruns checks, and commits.
3. Three new independent Flash reviewers repeat the same three scopes against the repaired commit.
4. If any finds an accepted blocker or major issue, allow one second Pro repair and another full three-reviewer round.
5. Stop after the second repair if an accepted blocker or major remains.

Final acceptance requires three approvals on the same unchanged commit.

After the final team accepts the unchanged commit, the advisor/operator records the external verdict, immutable commit SHA, report SHA-256, reviewer session IDs, and date in this index. The tracked report does not hash itself or claim its own containing commit SHA.

## Human review gate

The Pro executor and Flash reviewers do not replace the decided human fixture review.

After the Pro writer commits a deterministic candidate, the advisor/controller owns live runs. The writer and Flash reviewers do not receive provider credentials and do not complete the human rubric.

After every live Job 49 or Job 328 run:

1. the controller runs the configured-provider command
2. execution pauses
3. Arinze receives the final answer and local `review.md` path
4. Arinze records an accepted or rejected human verdict
5. the controller returns only safe run IDs, hashes, statuses, and verdicts to the same Pro writer
6. execution resumes only after that verdict exists

Raw review details remain local when they contain private material. The tracked report records only the safe outcome and hashes.

## Deliverables required from every plan

| Deliverable | Plan 001 | Plan 002 | Plan 004 | Plan 005 |
|---|---|---|---|---|
| Working boundary | one model call | one trusted source tool | saved assessment with durable tool effects | append-only user decision and recall |
| Deterministic tests | fake model | fake resolver and transport | fake assessment trajectories and crash boundaries | fake decision and correction trajectories |
| Manual interface | experiment CLI | experiment CLI with source inspection | existing inline chat | existing inline chat |
| Live proof | Jobs 49 and 328 | Stage 0/1 comparison | saved assessment and resume | decision, correction, and recall |
| Private evidence | ignored local receipts | ignored local receipts | safe metadata only | safe metadata only |
| Deliverable folder | `deliverables/001-stage0/` | `deliverables/002-stage1/` | `deliverables/004-saved-job-assessment/` | `deliverables/005-job-decisions/` |
| Draw.io source and PNG | required | required | three actual-state diagrams | two actual-state diagrams |
| Review ledger | required | required | required | required |
| External verdict | required | required | required | required |

The Markdown report is the diagram companion. It records actual files, call paths, commands, outputs, run IDs, safe hashes, initial review findings, deferrals, and residual risks.

The report contains hashes for the draw.io source and PNG. It does not contain its own hash or its containing commit SHA. Those are recorded here after final review.

## Manual interface progression

This is a repository experiment interface, not a finished distributable career CLI.

### Plans 001-003 (DONE)

After Plan 001:

```bash
# Zero-cost smoke run with tracked synthetic career data
PYTHONPATH=src:. uv run -- haxjobs experiment review-job \
  --job 49 --fake \
  --career-fixture tests/fixtures/job_review/career.json

# Real configured-provider run with the ignored truthful career fixture
PYTHONPATH=src:. uv run -- haxjobs experiment review-job \
  --job 49 --live \
  --career-fixture state/experiments/fixtures/backend-career.json
```

After Plan 002:

```bash
# Fully fake, including source transport. No socket opens.
PYTHONPATH=src:. uv run -- haxjobs experiment review-job \
  --job 328 --fake --inspect-source \
  --career-fixture tests/fixtures/job_review/career.json

# Real configured provider and trusted-fixture source inspection
PYTHONPATH=src:. uv run -- haxjobs experiment review-job \
  --job 328 --live --inspect-source \
  --career-fixture state/experiments/fixtures/backend-career.json \
  --max-model-steps 3
```

Live calls are always explicit. There is no provider fallback.

### Plans 004-005 (TODO)

After Plan 004:

```bash
# Import job fixtures one way (operator-controlled)
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions \
  import discussion/fixtures/harness/job-49.json
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions \
  import discussion/fixtures/harness/job-328.json

# Conversational job assessment (fake, no network)
PYTHONPATH=src:. uv run -- haxjobs chat --new --fake
# Type: "What do you think of job 328?"

# Live conversation with real provider (auto-selects single person/track,
# or specify explicitly with flags valid only with --new)
PYTHONPATH=src:. uv run -- haxjobs chat --new
PYTHONPATH=src:. uv run -- haxjobs chat --new --person-id person-abc123 --track-id track-abc123

# Resume latest session
PYTHONPATH=src:. uv run -- haxjobs chat
```

After Plan 005:

```bash
# Record a decision in conversation
PYTHONPATH=src:. uv run -- haxjobs chat
# Type: "yeah, skip job 49"
# Type: "what did I decide about job 49?"
# Hax retrieves from employment store, not just transcript
```

Live calls are always explicit. There is no provider fallback.

## Verification floor

Plan-specific commands are authoritative. The shared floor is:

```bash
uv lock --check
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile \
  $(find src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')
PYTHONPATH=src:. uv run -- haxjobs --help
PYTHONPATH=src:. uv run -- haxjobs chat --help
git diff --check
```

The old frontend verification path is outside this wave because the current greenfield cleanup removes the frontend. The committed design baseline must make the repository-wide CI decision explicit before Plan 001 is restamped.

Unit tests never call a live model or public network. Live provider/source runs are separate evidence steps.

## Draw.io rule

Use `.agents/skills/clean-drawio/SKILL.md`.

Each diagram must:

- show only code present after the plan
- use five to seven grouped swimlanes
- stay under roughly 35 cells
- keep file paths out of nodes
- use thick orthogonal inter-group arrows
- include geometry for every edge
- parse as XML
- export through the local draw.io command
- regenerate the tracked PNG from the final source
- pass visual clipping, overlap, and readability review
- live in the plan's self-contained deliverable folder
- be linked from the completion report and deliverable README

## Deferred work

Plans 004 and 005 deliberately exclude:

- context compaction, summaries, embeddings, and token budgets
- arbitrary URL intake and broad discovery
- company watches, schedulers, and background workers
- employability roadmaps and learning-pattern analysis
- application packs, submission, outreach, and external effects
- approval workflows
- document and coding workspaces
- generic filesystem and shell tools
- subagents, plugins, MCP, and workflow engines
- web UI and API work
- source-observation history and cross-process session locking

## Planning decisions for this wave

- Measure context pressure before building compaction.
- Persist tool calls before effects and results before another model call.
- Keep Hax assessments separate from user decisions.
- Treat `apply` as user intent only. It causes no application or outreach effect.
- Keep source URLs behind saved job IDs. The model never supplies arbitrary fetch targets.
- Delete the superseded experiment runtime only after replacement trajectories pass.
- Keep Plan 005 out of agent core. If it exposes an agent-core gap, stop and reconcile the plan.

## Not audited or planned

This planning pass focused on saved jobs, assessments, durable tool effects, and user decisions. Discovery, packs, employability roadmaps, continuous operation, coding workspaces, outreach, deployment, and web interfaces remain outside Plans 004 and 005.
