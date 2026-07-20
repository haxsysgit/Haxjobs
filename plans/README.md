# Greenfield HaxJobs implementation plans

Generated on 2026-07-17 from `discussion/` and the pinned Pi/Hermes source study.

This plan set starts the new runtime with two controlled experiments:

```text
Stage 0
  one observed provider call, no tools

Stage 1
  the same runtime, one inspect_job_source(job_ref) tool
```

Stage 2 and later plans stay unwritten until Stage 1 traces show the next repeatable failure.

## Current execution blockers

None.

- Design baseline: `7da5786`
- Execution baseline: the clean commit containing the reconciled plan; record its SHA before dispatch
- Delivery models: `deepseek-v4-pro` and `deepseek-v4-flash` confirmed through Pi
- Product provider: authenticated `deepseek-v4-flash` call confirmed with the HaxJobs configuration
- Private fixture: `state/experiments/fixtures/backend-career.json` version 3, derived from the corrected `src/haxjobs/cv_profile.typed.json`, ignored by git, mode `0600`

## Execution order and status

| Plan | Title | Priority | Effort | Depends on | Status | Final commit | Report SHA-256 |
|---|---|---:|---:|---|---|---|---|
| [001](001-stage0-observed-job-review.md) | Build the Stage 0 observed job review | P1 | L | clean reconciled execution baseline | DONE | `e396fd2` | pending |
| [002](002-stage1-source-inspection-loop.md) | Stage 1 bounded source-inspection loop | P1 | L | Plan 001 DONE at a28d5ba | DONE | `6d64624` | deliverables/002-stage1/ | Live runs completed 2026-07-20; Flash reviewers found 0 blockers, 1 minor (code NameError fixed in follow-up). |
| [003](003-career-graph-schema.md) | Career graph schema — tracks, skills, evidence, persistence, CLI, TUI | P1 | M | Plan 002 DONE | DONE | `9ee53be` | deliverables/003-career-graph/ | 3 Flash reviewers approved. 86 tests pass. |

The advisor/operator owns this table. Executors do not edit it.

## Deliverable folder convention

Every plan collects its deliverable artifacts into one labelled folder
under `deliverables/<plan-slug>/`: the implementation report, diagram
source and PNG, fixture files, rubric, and a short `README.md`. The
plan text is copied in as `plan.md`. Code in `src/` and test fixtures
in `tests/` stay where they are. Do not symlink — copy sources so the
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
Plan 003: Career Graph Schema
  tracks, skills, evidence, gaps, persistence, CLI, TUI
```

Later plans (004+) stay unwritten until Plan 003 is accepted.

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

The new runtime must not import or wrap `src/haxjobs/agent/`. The legacy agent stays untouched until a later migration plan proves replacement is warranted.

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

| Deliverable | Plan 001 | Plan 002 |
|---|---|---|
| Working boundary | one model call, no tools | same runtime, one source tool |
| Deterministic tests | fake model | fake model plus fake resolver/transport |
| Manual CLI | `haxjobs experiment review-job` | same command with `--inspect-source` |
| Live fixture runs | Job 49 and Job 328 | Stage 0/1 comparison for both |
| Human rubrics | Arinze completes two | Arinze completes required comparisons |
| Private receipts | ignored `state/harness-runs/` | same |
| Tracked report | `docs/implementation-reports/001-stage0-observed-job-review.md` | `docs/implementation-reports/002-stage1-source-inspection-loop.md` |
| Current-state draw.io | `diagram/003-stage0-observed-job-review.drawio` | `diagram/004-stage1-source-inspection-loop.drawio` |
| PNG from final source | required | required |
| Diagram index/backlink | required | required |
| Flash review ledger | required | required |
| External advisor verdict | required | required |

The Markdown report is the diagram companion. It records actual files, call paths, commands, outputs, run IDs, safe hashes, initial review findings, deferrals, and residual risks.

The report contains hashes for the draw.io source and PNG. It does not contain its own hash or its containing commit SHA. Those are recorded here after final review.

## Manual interface progression

This is a repository experiment interface, not a finished distributable career CLI.

After Plan 001:

```bash
# Zero-cost smoke run with tracked synthetic career data
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 49 --fake \
  --career-fixture tests/fixtures/job_review/career.json

# Real configured-provider run with the ignored truthful career fixture
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 49 --live \
  --career-fixture state/experiments/fixtures/backend-career.json
```

After Plan 002:

```bash
# Fully fake, including source transport. No socket opens.
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source \
  --career-fixture tests/fixtures/job_review/career.json

# Real configured provider and trusted-fixture source inspection
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --live --inspect-source \
  --career-fixture state/experiments/fixtures/backend-career.json \
  --max-model-steps 3
```

Live calls are always explicit. There is no provider fallback.

## Verification floor

Plan-specific commands are authoritative. The shared floor is:

```bash
uv lock --check
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile \
  $(find src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')
PYTHONPATH=src:. uv run haxjobs --help
PYTHONPATH=src:. uv run haxjobs experiment review-job --help
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
- match a second independent export byte-for-byte
- pass Reviewer C's visual clipping/readability check
- be indexed in `diagram/README.md`
- link from `discussion/006` and the implementation report

## Deferred work

These plans deliberately exclude:

- sessions and conversation history
- context retrieval and compaction
- databases and career graph
- company watches and schedulers
- application decisions and packs
- document and coding workspaces
- generic filesystem and shell tools
- approvals and external effects
- browser and search fallback
- web UI and API integration
- streaming and provider fallback
- plugins, skills, sub-agents, and workflow engines
- telemetry and model-judge platforms

## Findings considered and rejected

- **Build the full session/context system first:** rejected. Real job-review traces come first.
- **Use the existing `src/haxjobs/agent/Agent`:** rejected. It mixes provider setup, messages, and tool execution.
- **Delete the legacy agent in Plan 001:** rejected. Replacement has not been proved.
- **Adopt PydanticAI now:** rejected. Plain Python is the decided experiment floor.
- **Add web search or browser fallback in Stage 1:** rejected. A blocked source is valid evidence.
- **Plan coding workspaces now:** rejected for this wave. They do not help the first job-review experiment.
- **Write Stage 2 and Stage 3 plans now:** rejected. Later scope must come from Stage 1 traces.
- **Require `context.md`, `plan.md`, or `progress.md`:** rejected. Those files are not part of the accepted design process.
- **Keep duplicate generated plans from review subagents:** rejected and removed. Only the two linked canonical plans are executable.

## Not audited or planned

This was a focused planning pass, not a whole-repository audit. It did not re-audit:

- the old product pipeline
- FastAPI routes
- database correctness
- discovery scrapers
- packs and CV generation
- packaging and deployment
- company-watch persistence
- future coding-workspace isolation

Those surfaces are outside the first two experiments.
