# Plan 008: Dev/Prod Separation and First-Run UX

> **Executor:** DeepSeek V4 Pro (writer), DeepSeek V4 Flash (reviewers)
> **Depends on:** Plan 007 DONE
> **Drift stamp:** commit `c2a4455` (v0.1.0 tag)
> **Status:** TODO
> **WARNING:** This plan is not final. The executor must compare it against live code before implementing. Deliver a completion report covering what changed, how it changed, and deliverables.

## Goal

A developer working on the checkout must never accidentally write to their real `~/.haxjobs/`. A user installing from PyPI must get clear guidance at every first-run step. No hardcoded settings or personal details anywhere except in tests.

## Why

The fork audit found three gaps:

1. **No dev-mode guard.** Running `PYTHONPATH=src:. uv run -- haxjobs` in the checkout without setting `HAXJOBS_HOME` silently writes to the user's real `~/.haxjobs/` — the same home the installed package uses. A developer testing a chat could overwrite their real career data.

2. **User stuck after setup.** `haxjobs setup` works, but then `haxjobs` prints "Run 'haxjobs migrate' first" with zero guidance about what fixture to use or where to find one. There is no built-in `haxjobs init` command. A brand-new user hits a dead end.

3. **Hardcoded personal values.** The migration module contains Arinze-specific skill lists, salary range, and notice period as Python constants. These should come from the fixture, not the code.

## Scope

### In
- Dev-mode detection: when `PYTHONPATH` or a checkout marker is present, default `HAXJOBS_HOME` to a dev path
- `scripts/dev.sh` that sets up a safe dev environment
- `HAXJOBS_HOME` documentation in a new `docs/DEVELOPMENT.md`
- Remove hardcoded personal values from `migration.py`
- Allow salary_range and notice_period to come from the fixture or be left blank
- No hardcoded skill lists — if skills can't be detected from fixture evidence, they're simply not auto-detected

### Out
- `haxjobs init` command (deferred until onboarding exists)
- Full onboarding flow
- Any UI work

## Files

### Modify
- `src/haxjobs/config.py` — dev-mode detection on import
- `src/haxjobs/employment/migration.py` — remove hardcoded skills, salary, notice period
- `src/haxjobs/employment/context.py` — make skill gap detection optional, driven by fixture data
- `src/haxjobs/cli.py` — improve first-run error messages with concrete guidance

### Create
- `scripts/dev.sh` — `export HAXJOBS_HOME="$(pwd)"; export PYTHONPATH="src:."`
- `docs/DEVELOPMENT.md` — how to set up dev environment, HAXJOBS_HOME, run tests, fake mode
- `deliverables/008-dev-prod-ux/README.md`
- `deliverables/008-dev-prod-ux/report.md`
- `deliverables/008-dev-prod-ux/plan.md`

### Delete
- No file deletions in this plan.

## Phase 1: Dev-mode guard

### Task 1: Detect dev environment

When `config.py` is imported and `HAXJOBS_HOME` is not explicitly set, check if we're running from a development checkout. A checkout is detected by the presence of `pyproject.toml` or `.git` in the current working directory, OR if `PYTHONPATH` contains `src`.

If dev mode is detected, set `HAXJOBS_HOME` to a `dev-home/` directory inside the checkout (gitignored). Print a single line to stderr: "Dev mode: using <path> for runtime data. Set HAXJOBS_HOME to override."

If `HAXJOBS_HOME` IS explicitly set in the environment, never override it — explicit wins.

### Task 2: Create dev.sh

```bash
#!/usr/bin/env bash
# Source this file before running haxjobs in development.
# Usage: source scripts/dev.sh

export HAXJOBS_HOME="$(pwd)"
export PYTHONPATH="src:."
echo "Dev environment: HAXJOBS_HOME=$HAXJOBS_HOME"
```

### Task 3: Add dev-home/ to .gitignore

Add `dev-home/` to `.gitignore` so the auto-created dev state directory is never committed.

## Phase 2: Remove hardcoded personal values

### Task 4: Clean migration.py

Currently `migration.py` has:

```python
_KNOWN_SKILLS = ["Python", "Django", "FastAPI", "SQL", ...]
_GAP_SKILLS = {"React": "working", "TypeScript": "working", ...}
```

And in `migrate_career_fixture()`:

```python
notice_period="immediate",
salary_range="35000-45000 GBP",
```

Changes:

1. **Remove `_KNOWN_SKILLS`.** Auto-detection of skills from evidence content is useful, but the list of skills must come from the fixture, not the code. Add an optional `detect_skills` field to `CareerFixture`:

```python
class CareerFixture(BaseModel):
    ...
    detect_skills: list[str] = Field(default_factory=list)
    gap_skills: dict[str, str] = Field(default_factory=dict)
```

The fixture JSON gains:

```json
{
  "detect_skills": ["Python", "Django", "FastAPI", ...],
  "gap_skills": {"React": "working", "TypeScript": "working", ...}
}
```

Update the tracked synthetic fixture at `tests/fixtures/job_review/career.json` to include these fields.

2. **Remove hardcoded salary/notice.** The `Person` model already has `salary_range` and `notice_period` as optional string fields (default `""`). Instead of hardcoding, pass from the fixture. `CareerFixture` does not currently have these fields, but `Person` does. The migration should pass empty strings unless the fixture provides values.

### Task 5: Update synthetic fixture

Update `tests/fixtures/job_review/career.json` to include `detect_skills` and `gap_skills` matching the current hardcoded values. This preserves the current behavior for tests without baking personal data into code.

## Phase 3: Better first-run messages

### Task 6: Improve CLI error messages

Current output:
```
Error: No people found in career store.
Run 'haxjobs migrate' first.
```

Improved output:
```
No career data found.

To get started, create a career fixture JSON file, then run:

  haxjobs migrate --fixture path/to/your-career.json

A minimal career fixture needs:
  - fixture_id, fixture_version (any string and number)
  - person_id, person_name (identify you)
  - track_name (career direction, e.g. "Backend Python Engineer")
  - career_direction (one-paragraph summary)
  - hard_constraints (list of non-negotiable requirements)
  - evidence (at least one work/project item with label, source, content)

See the example at: https://github.com/haxsysgit/Haxjobs/blob/main/tests/fixtures/job_review/career.json
```

Also add a `haxjobs migrate --help` output that explains what a fixture is and links to the example.

### Task 7: Make migrate --fixture optional when exactly one candidate exists

If the user runs `haxjobs migrate` without `--fixture`, and exactly one JSON file exists in the current directory that looks like a career fixture (has `fixture_id` and `fixture_version` keys), auto-select it and proceed with a confirmation message. Otherwise, print the help text from Task 6.

## Phase 4: Verification

### Task 8: Run all checks

```bash
# Tests
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/

# Compile
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests scripts -name '*.py')

# Lock
uv lock --check

# Dev-mode test: import config in checkout without HAXJOBS_HOME set
PYTHONPATH=src:. uv run -- python3 -c "
import os
os.environ.pop('HAXJOBS_HOME', None)
import haxjobs.config
print('HOME:', haxjobs.config.HAXJOBS_HOME)
assert 'dev-home' in str(haxjobs.config.HAXJOBS_HOME) or 'haxjobs' in str(haxjobs.config.HAXJOBS_HOME)
"

# Dev-mode test: HAXJOBS_HOME explicit override wins
HAXJOBS_HOME=/tmp/test-explicit PYTHONPATH=src:. uv run -- python3 -c "
import haxjobs.config
assert str(haxjobs.config.HAXJOBS_HOME) == '/tmp/test-explicit'
"

# Migrate with no hardcoded values
HAXJOBS_HOME=$(mktemp -d) PYTHONPATH=src:. uv run -- haxjobs migrate \
  --fixture tests/fixtures/job_review/career.json
```

## Deliverables

After implementation, create `deliverables/008-dev-prod-ux/` with:
- `plan.md` — copy of this plan
- `report.md` — implementation report
- `README.md` — deliverable index
