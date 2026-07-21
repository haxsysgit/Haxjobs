# Getting Started with HaxJobs

HaxJobs is currently a greenfield employment-agent runtime under active development.

The model boundary, bounded model and tool loop, source-inspection tool, career graph, and experiment runner exist. The interactive agent interface does not exist yet. The discarded Textual prototype was a profile browser and then a fake chat shell. Both missed the product, so they were deleted.

## Install for development

```bash
git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync
```

Use Python 3.12 or newer.

Run commands from the repository root for now:

```bash
cd /home/hax/haxjobs
```

## Current commands

```bash
haxjobs --help
```

### Build the local career graph

```bash
haxjobs migrate
```

This reads the ignored private fixture at:

```text
state/experiments/fixtures/backend-career.json
```

It writes the local database to:

```text
state/career_graph.db
```

### Inspect the career graph

```bash
haxjobs profile show
```

Profile CRUD commands are also available under:

```bash
haxjobs profile --help
```

### Run the observed job-review experiments

No provider call:

```bash
haxjobs experiment review-job --job 49 --fake
haxjobs experiment review-job --job 328 --fake --inspect-source
```

Configured provider:

```bash
haxjobs experiment review-job --job 328 --live --inspect-source
```

The live command needs the private provider configuration and career fixture.

## What works today

| Layer | Current state |
|---|---|
| Model boundary | OpenAI-compatible provider client plus deterministic fake client |
| Agent core | Bounded model and tool loop, active tool enforcement, validated tool inputs and outputs |
| Employment layer | Job review context, frozen fixtures, trusted job-source inspection, career graph schema and persistence |
| Career graph | Person, career tracks, hierarchical skills, evidence, gaps, hard constraints, and preferences |
| Interfaces | CLI commands for experiments and profile administration |
| Interactive agent | Not built yet |

## Why there is no TUI yet

A coding-agent-style terminal interface is not just a text box or a database viewer. It depends on runtime work that HaxJobs has not finished:

- a real conversation or session API
- streamed model events
- user, assistant, tool-call, tool-result, and error events
- cancellation and interruption
- durable conversation state
- context assembly from the career graph
- an employment action boundary the agent can call
- honest tool progress and approval rendering

The next interface must sit on those runtime contracts. It must not contain fake responses or business logic.

## Verify the current code

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
```

## Current file map

```text
src/haxjobs/
  model/          provider boundary and canonical model types
  agent_core/     bounded runtime loop and tool registry
  employment/     career graph, job review, fixtures, and source inspection
  interfaces/     CLI adapters
  cli.py          installed command entry point
  config.py       path configuration

state/
  career_graph.db
  experiments/fixtures/
  harness-runs/

tests/
  test_stage0_job_review.py
  test_stage1_source_inspection.py
  test_career_graph.py

deliverables/
  001-stage0/
  002-stage1/
  003-career-graph/
```

## Progress documents

- `docs/PRODUCT.md`: product direction and current limitations
- `docs/HAXJOBS.md`: current architecture and built-versus-planned state
- `discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md`: runtime design reference
- `plans/README.md`: completed implementation stages
- `deliverables/`: reports and diagrams for each completed stage
