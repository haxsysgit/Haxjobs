# Plan 008 — Dev/Prod Separation and Documentation

> **Baseline:** `c2a4455` (v0.1.0 tag)
> **Drift stamp:** 2026-07-25
> **Status:** TODO
> **Depends on:** Plan 007 DONE

## Goal

Make the dev checkout and the production install completely independent. A developer running `uv run -- haxjobs` in the checkout must never touch `~/.haxjobs/`. An installed user reading the README must see the installed workflow, not the dev workflow. The first-run experience after `pip install haxjobs` must be clear and not dead-end.

---

## Scope

### In

- Dev-mode guard: `scripts/dev.sh` that sets `HAXJOBS_HOME` to the checkout
- `.gitignore` update: ensure dev state directories are ignored
- README rewrite: installed-user workflow first, dev workflow second
- `docs/GETTING_STARTED.md` rewrite
- `haxjobs migrate` hint: when a user has no career data, tell them what fixture to use and where to find it
- Document `HAXJOBS_HOME` in README

### Out

- Automatic dev-mode detection (explicit env var is simpler and safer)
- Onboarding flow (future plan)
- Built-in default fixture
- Any runtime code changes beyond the migrate hint

---

## Files

### Create

- `scripts/dev.sh` — sets `HAXJOBS_HOME` to checkout, runs `uv run -- haxjobs "$@"`

### Modify

- `README.md` — complete rewrite for installed users
- `docs/GETTING_STARTED.md` — rewrite
- `src/haxjobs/cli.py` — better migrate hint with fixture path guidance
- `.gitignore` — ensure `state/` and `~/.haxjobs`-equivalent paths are ignored

### Do not modify

- `src/haxjobs/config.py` — already correct
- Any test files
- `src/haxjobs/employment/migration.py` — hardcoded skill lists stay (single-user tool)

---

## Phase 1: Dev-mode guard

### Task 1: Create `scripts/dev.sh`

**File:** `scripts/dev.sh` (new)

```bash
#!/bin/bash
# Dev helper — runs haxjobs with checkout state, never touches ~/.haxjobs
export HAXJOBS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="src:."
exec uv run -- haxjobs "$@"
```

Make it executable. This is the only supported dev entry point. Running bare `uv run -- haxjobs` without `HAXJOBS_HOME` set is undefined behavior for devs. The README documents this.

### Task 2: Update `.gitignore`

Ensure these are gitignored if not already:
```
/state/
*.db-journal
*.db-wal
```

The dev checkout's `state/` directory (where `HAXJOBS_HOME` points) must never be committed.

---

## Phase 2: README rewrite

### Task 3: Rewrite README.md

Structure for an installed user landing on GitHub/PyPI:

```markdown
# HaxJobs

Conversational career agent — your personal job-search harness.

## Install

pip install haxjobs

## First run

haxjobs setup          # configure your provider (API key)
haxjobs migrate --fixture path/to/career.json   # load your career data
haxjobs                 # start the conversation

## How it works

HaxJobs is a terminal-based conversational agent that helps you search for jobs,
evaluate opportunities, and track decisions. All data lives in `~/.haxjobs/`.

## Development

git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync
./scripts/dev.sh         # uses checkout state, never touches ~/.haxjobs

## Architecture

[short description of 4-layer model/agent_core/employment/interfaces]
```

### Task 4: Rewrite `docs/GETTING_STARTED.md`

Same information, more detail. Include:
- Provider setup walkthrough (deepseek defaults)
- Career fixture format example (synthetic test fixture)
- Dev workflow with `scripts/dev.sh`
- `HAXJOBS_HOME` explanation

---

## Phase 3: First-run UX

### Task 5: Better migrate hint

**File:** `src/haxjobs/cli.py`

Current:
```python
print("Run 'haxjobs migrate' first.", file=sys.stderr)
```

Change to:
```python
print(
    "No career data found. Load your career fixture:\n"
    "  haxjobs migrate --fixture path/to/career.json\n"
    "\n"
    "A career fixture is a JSON file describing your skills, evidence, and\n"
    "constraints. See docs/GETTING_STARTED.md for the format.",
    file=sys.stderr,
)
```

Also update the "No provider" message similarly to reference `haxjobs setup` with a brief explanation.

---

## Verification

```bash
# Dev mode must not touch ~/.haxjobs
HAXJOBS_HOME=$(mktemp -d) PYTHONPATH=src:. uv run -- haxjobs --help
ls ~/.haxjobs 2>/dev/null  # must not have been created (if didn't exist before)

# Dev script must set HAXJOBS_HOME to checkout
bash -n scripts/dev.sh

# Full test suite
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/   # 290 tests

# README has pip install instructions
grep 'pip install' README.md

git diff --check
```

---

## Deliverables

- `scripts/dev.sh` — dev entry point
- Rewritten README.md — installed user audience
- Rewritten docs/GETTING_STARTED.md
- Better first-run error messages
