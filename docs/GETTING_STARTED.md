# Getting Started with HaxJobs

HaxJobs is a career agent harness. Right now it has a career graph (your profile as structured data) and a terminal UI for browsing it. The job review experiments from Stage 0/1 are available as CLI commands.

## Install

```bash
git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync
```

Python 3.12+. The only dependencies are `openai`, `pydantic`, `textual`, and `rich`.

## First run — migrate your profile

HaxJobs needs your career data. Run the one-time migration from your private career fixture:

```bash
haxjobs migrate
```

This reads `state/experiments/fixtures/backend-career.json` (your private file, gitignored, 0600 permissions) and builds the career graph database at `state/career_graph.db`.

If the fixture doesn't exist yet, create it from `src/haxjobs/cv_profile.typed.json`.

## Open the terminal UI

```bash
haxjobs
```

Or explicitly:

```bash
haxjobs tui
```

**Navigation:**
- `↑↓` — move between tracks
- `Enter` — drill into a track (see skills, evidence, gaps)
- `Tab` — switch between panels (skills / gaps / constraints / preferences)
- `Esc` — go back
- `q` — quit

## CLI commands

### Profile

```bash
haxjobs profile show              # View your career graph
haxjobs profile track add \       # Add a career track
  --name "AI Engineer" --person-id arinze-elensulu
haxjobs profile skill add \       # Add a skill to a track
  --track-id track-xxx --name "Rust" --proficiency learning
haxjobs profile evidence add \    # Add evidence for a skill
  --label "rust-cli-tool" --source "github" --content "Built a CLI tool in Rust"
haxjobs profile gap add \         # Record a skill gap
  --track-id track-xxx --skill-name "Kubernetes" --proficiency working
haxjobs profile constraint add \  # Add a hard constraint
  --track-id track-xxx --text "Must be remote within UK"
```

### Experiments (Stage 0/1)

```bash
haxjobs experiment review-job --job 49 --fake               # Fake run, no network
haxjobs experiment review-job --job 328 --fake --inspect-source  # With source inspection
haxjobs experiment review-job --job 328 --live --inspect-source  # Live DeepSeek call
```

## What's built

| Layer | What |
|-------|------|
| **Career graph** | 8-table relational schema (Person, CareerTrack, Skill tree, EvidenceItem, SkillEvidence, SkillGap, HardConstraint, Preference). SQLite WAL mode. |
| **TUI** | Textual app — browse tracks, skills, evidence, gaps. Keyboard navigation. |
| **CLI** | Profile CRUD commands. Migration. Experiment runner. |
| **Agent core** | One-call and bounded tool-loop execution. Tool registry with active-set enforcement. Pydantic validation. |
| **Model boundary** | OpenAI-compatible adapter + fake client. DeepSeek v4 flash configured. |
| **Employment layer** | Hax identity rules, career fixtures, job source inspection (HTTPS-only, no redirects). |

## What's next

Discovery, evaluation, and decision workflows on top of the career graph. The plan is to build one vertical at a time — discover jobs, evaluate fit against your career graph, record decisions — then add conversation sessions, company watches, and employability roadmaps.

## Running in development

```bash
PYTHONPATH=src:. .venv/bin/python src/haxjobs/cli.py           # TUI
PYTHONPATH=src:. .venv/bin/python -m haxjobs                   # Same, via __main__
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/          # 86 tests
PYTHONPATH=src:. .venv/bin/python -m py_compile $(find src tests -name '*.py')  # Compile check
```

## File map

```
src/haxjobs/
  model/          — Provider boundary (client.py, fake.py, types.py)
  agent_core/     — Domain-free loop (runtime.py, tools.py, types.py)
  employment/     — Career domain (schema.py, store.py, migration.py, review_job.py, fixtures.py, job_source.py)
  interfaces/     — User surfaces (cli.py, tui.py, experiment_cli.py, profile_cli.py)
  config.py       — Path resolution from haxjobs.toml

state/
  career_graph.db          — Career graph database (not tracked)
  experiments/fixtures/    — Private career fixture (not tracked)
  harness-runs/            — Experiment traces (not tracked)

tests/
  test_stage0_job_review.py       — 27 tests
  test_stage1_source_inspection.py — 37 tests
  test_career_graph.py            — 22 tests

deliverables/
  001-stage0/   — Stage 0 report + diagram
  002-stage1/   — Stage 1 report + diagram
  003-career-graph/  — Career graph report + schema diagram
```
