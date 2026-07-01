# Plan 040: Restructure repo into installable Python package (uv + hatchling)

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- pyproject.toml`
> If pyproject.toml already exists, this plan may have been partially executed. Compare against live code.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (restructures entire repo, import paths change)
- **Depends on**: none
- **Category**: migration
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The repo is a flat directory of Python modules at root. `uv tool install haxjobs` requires a `pyproject.toml` with a build system and code under `src/haxjobs/`. This plan is the foundation — nothing else can ship until the package structure exists. The user's package manager is **uv** (not pip), so `pyproject.toml` uses `hatchling` as the build backend and `uv add` for dependency management. The CLI entry point uses `argparse` (stdlib, zero deps).

## Current state

All Python code lives at repo root:
```
haxjobs-private-dev/
├── db/ discovery/ evaluate/ evaluation/ packs_builder/ server/ profile/
├── application_templates/ cv_variants/ scripts/
├── api_server.py  pipeline_db.py  haxjobs_config.py  haxjobs.toml
├── generate_ready_packs.py  check_dashboard.py
├── cv_profile.typed.json  cv_template.html
├── tests/  dashboard/  docs/  plans/  cron/  research/  adapter_research/
├── state/  packs/  reports/  (runtime dirs — .gitignored)
├── README.md  AGENTS.md  PI_HANDOFF.md
├── .gitignore  .env  .env.example
├── dashctl.sh  dev-app.sh  (old scripts)
```

Key constraints:
- 255 tests pass with `PYTHONPATH=. python3 -m pytest -q tests/`
- Imports use `from db.jobs import ...`, not relative imports
- `haxjobs_config.py` reads `haxjobs.toml` from the working directory
- `db.schema` has `DB_PATH = "state/haxjobs.db"` (relative path)
- Tests use `conftest.py` `test_db` fixture that monkeypatches `db.schema.DB_PATH`

Repo conventions:
- Python stdlib-focused, no ORM
- Config is TOML-driven via `haxjobs_config.py`
- SQLite via `db/schema.py` `get_db()`
- Test runner: `python3 -m pytest -q tests/`

## What stays at root vs moves into package

| Stay at root (project infra, not installed) | Move into `src/haxjobs/` (installed code) |
|---|---|
| `.git/`, `.gitignore`, `.claude/`, `.venv/` | `db/` → `src/haxjobs/db/` |
| `plans/`, `docs/`, `research/`, `adapter_research/` | `discovery/` → `src/haxjobs/discovery/` |
| `README.md`, `AGENTS.md`, `PI_HANDOFF.md` | `evaluate/` → `src/haxjobs/evaluate/` |
| `tests/` (test suite, not installed) | `evaluation/` → `src/haxjobs/evaluation/` |
| `dashboard/` (old frontend, deleted in plan 042) | `packs_builder/` → `src/haxjobs/packs_builder/` |
| `cron/` (system scheduling, not package) | `server/` → `src/haxjobs/server/` |
| `.env`, `.env.example` | `profile/` → `src/haxjobs/profile/` |
| `state/`, `packs/`, `reports/` (runtime, .gitignored) | `scripts/` → `src/haxjobs/scripts/` |
| | `application_templates/` → `src/haxjobs/application_templates/` |
| | `cv_variants/` → `src/haxjobs/cv_variants/` |
| | `haxjobs.toml` → `src/haxjobs/haxjobs.toml` |
| | `haxjobs_config.py` → `src/haxjobs/config.py` |
| | `api_server.py` → `src/haxjobs/api_server.py` |
| | `pipeline_db.py` → `src/haxjobs/pipeline_db.py` |
| | `generate_ready_packs.py` → `src/haxjobs/generate_ready_packs.py` |
| | `check_dashboard.py` → `src/haxjobs/check_dashboard.py` |
| | `cv_profile.typed.json` → `src/haxjobs/cv_profile.typed.json` |
| | `cv_template.html` → `src/haxjobs/cv_template.html` |

Delete during this plan (already stale):
- `dashctl.sh`, `dev-app.sh` — old dev scripts, replaced by `haxjobs start` in 041

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `uv run pytest -q tests/` | 255 passed |
| Build package | `uv build` | creates dist/*.whl + dist/*.tar.gz |
| Verify CLI | `uv run haxjobs --help` | shows usage |
| Verify imports | `uv run python -c "from haxjobs.db import jobs; print('ok')"` | ok |

## Scope

**In scope**:
- Create `pyproject.toml` at root (hatchling build backend)
- Create `src/haxjobs/` package structure
- Move only the files listed under "Move into src/haxjobs/" above
- Update ALL internal imports from `from db.x import y` to `from haxjobs.db.x import y`
- Rename `haxjobs_config.py` → `config.py` inside the package
- Update `config.py` to find `haxjobs.toml`: CWD first, then package dir
- Create `src/haxjobs/cli.py` with argparse: `haxjobs start` subcommand
- Update test imports to match new package paths
- Delete `dashctl.sh`, `dev-app.sh`

**Out of scope** (do NOT touch):
- `tests/` stays at root — move nothing in, only update imports
- `plans/`, `docs/`, `research/`, `adapter_research/` — stay at root
- `cron/` — stays at root
- `dashboard/` — stays at root (deleted in plan 042)
- `.gitignore` content — don't change
- Behavior of any module — pure find-and-replace on imports, no logic changes

## Git workflow

- Branch from `main`, work directly
- Commit per logical unit (steps 1-3 = one commit, steps 4-5 = one commit, step 6+ = one commit)
- Commit message: `"restructure repo into installable Python package under src/haxjobs/"`
- Do NOT push or open PR

## Steps

### Step 1: Create pyproject.toml

```bash
uv init --package --build-backend hatchling
```

This creates a basic pyproject.toml. Then edit it to match:

```toml
[project]
name = "haxjobs"
version = "1.0.0.dev0"
description = "Self-hosted job search platform"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [{name = "Arinze Elenasulu"}]
readme = "README.md"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "requests>=2.32",
]

[project.scripts]
haxjobs = "haxjobs.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/haxjobs"]

[tool.hatch.build.targets.wheel.force-include]
"src/haxjobs/haxjobs.toml" = "haxjobs/haxjobs.toml"
"src/haxjobs/cv_profile.typed.json" = "haxjobs/cv_profile.typed.json"
"src/haxjobs/cv_template.html" = "haxjobs/cv_template.html"
"src/haxjobs/application_templates" = "haxjobs/application_templates"
"src/haxjobs/cv_variants" = "haxjobs/cv_variants"
```

**Verify**: `uv build` → creates `dist/haxjobs-1.0.0.dev0-py3-none-any.whl` and `.tar.gz`

### Step 2: Create src/haxjobs/ package and move files

```bash
mkdir -p src/haxjobs
```

Create `src/haxjobs/__init__.py`:
```python
"""HaxJobs — self-hosted job search platform."""
__version__ = "1.0.0.dev0"
```

Move code directories:
```bash
git mv db src/haxjobs/db
git mv discovery src/haxjobs/discovery
git mv evaluate src/haxjobs/evaluate
git mv evaluation src/haxjobs/evaluation
git mv packs_builder src/haxjobs/packs_builder
git mv server src/haxjobs/server
git mv profile src/haxjobs/profile
git mv scripts src/haxjobs/scripts
git mv application_templates src/haxjobs/application_templates
git mv cv_variants src/haxjobs/cv_variants
```

Move individual files:
```bash
git mv haxjobs.toml src/haxjobs/haxjobs.toml
git mv haxjobs_config.py src/haxjobs/config.py
git mv api_server.py src/haxjobs/api_server.py
git mv pipeline_db.py src/haxjobs/pipeline_db.py
git mv generate_ready_packs.py src/haxjobs/generate_ready_packs.py
git mv check_dashboard.py src/haxjobs/check_dashboard.py
git mv cv_profile.typed.json src/haxjobs/cv_profile.typed.json
git mv cv_template.html src/haxjobs/cv_template.html
```

Delete stale scripts:
```bash
git rm dashctl.sh dev-app.sh
```

DO NOT move: `tests/`, `plans/`, `docs/`, `research/`, `adapter_research/`, `cron/`, `dashboard/`

**Verify**: `ls src/haxjobs/db src/haxjobs/discovery src/haxjobs/evaluate` → all three exist. `ls dashctl.sh 2>/dev/null` → file not found.

### Step 3: Update all imports

All imports like `from db.x import y` become `from haxjobs.db.x import y`. Same for discovery, evaluate, evaluation, packs_builder, server, profile.

Also: `import haxjobs_config` or `from haxjobs_config import X` → `from haxjobs.config import X`.

```bash
# Update absolute imports in src/haxjobs/
find src/haxjobs -name "*.py" -exec sed -i \
  -e 's/from db\./from haxjobs.db./g' \
  -e 's/from discovery\./from haxjobs.discovery./g' \
  -e 's/from evaluate\./from haxjobs.evaluate./g' \
  -e 's/from evaluation\./from haxjobs.evaluation./g' \
  -e 's/from packs_builder\./from haxjobs.packs_builder./g' \
  -e 's/from server\./from haxjobs.server./g' \
  -e 's/from profile\./from haxjobs.profile./g' \
  -e 's/import haxjobs_config/import haxjobs.config/g' \
  -e 's/from haxjobs_config/from haxjobs.config/g' \
  -e 's/from scripts\./from haxjobs.scripts./g' \
  {} +

# Update __init__.py relative imports
find src/haxjobs -name "__init__.py" -exec sed -i \
  -e 's/from \.\([a-z]\)/from haxjobs.\1/g' \
  {} +

# Update imports in tests/
find tests -name "*.py" -exec sed -i \
  -e 's/from db\./from haxjobs.db./g' \
  -e 's/from discovery\./from haxjobs.discovery./g' \
  -e 's/from evaluate\./from haxjobs.evaluate./g' \
  -e 's/from evaluation\./from haxjobs.evaluation./g' \
  -e 's/from packs_builder\./from haxjobs.packs_builder./g' \
  -e 's/from server\./from haxjobs.server./g' \
  -e 's/from profile\./from haxjobs.profile./g' \
  -e 's/import haxjobs_config/import haxjobs.config/g' \
  -e 's/from haxjobs_config/from haxjobs.config/g' \
  {} +
```

**Verify**: `grep -rn "from db\." src/haxjobs/ tests/` → no matches. `grep -rn "from haxjobs.db" src/haxjobs/` → positive matches.

### Step 4: Update config.py path resolution

Edit `src/haxjobs/config.py`. Find where `haxjobs.toml` is loaded — likely at module level with something like `_TOML = tomllib.load(open("haxjobs.toml", "rb"))`. Change to:

```python
import tomllib
from pathlib import Path

_TOML_PATH = Path("haxjobs.toml")
if not _TOML_PATH.exists():
    _TOML_PATH = Path(__file__).parent / "haxjobs.toml"
if not _TOML_PATH.exists():
    _TOML_PATH = Path.home() / ".haxjobs" / "haxjobs.toml"

def _load_toml():
    if _TOML_PATH.exists():
        with open(_TOML_PATH, "rb") as f:
            return tomllib.load(f)
    return {}
```

**Verify**: `grep "_TOML_PATH" src/haxjobs/config.py` → shows the 3-location resolution

### Step 5: Create CLI with argparse

Create `src/haxjobs/cli.py`:

```python
"""HaxJobs CLI."""
import argparse
import sys

def cmd_start(args):
    """Start the HaxJobs server."""
    from haxjobs.server.main import run
    print("Starting HaxJobs on http://localhost:8241")
    run(host=args.host, port=args.port)

def main():
    parser = argparse.ArgumentParser(prog="haxjobs", description="Self-hosted job search platform")
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="Start the server")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8241)
    start.set_defaults(func=cmd_start)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)

if __name__ == "__main__":
    main()
```

**Verify**: `uv run haxjobs --help` → shows usage. `uv run haxjobs start --help` → shows --host and --port flags.

### Step 6: Run tests

```bash
uv run pytest -q tests/
```

**Verify**: 255 passed. If any fail, the import sed missed something — check the failing test for stale import paths.

### Step 7: Commit

```bash
git add -A
git commit -m "restructure repo into installable Python package under src/haxjobs/"
```

**Verify**: exit 0, working tree clean

## Test plan

No new tests. The existing 255-test suite verifies that imports and logic survived the restructure. Critical: `uv run pytest -q tests/` returns 255 passed.

## Done criteria

- [ ] `pyproject.toml` exists at root with hatchling build backend
- [ ] All application code under `src/haxjobs/`
- [ ] `uv build` succeeds, creates wheel + sdist in `dist/`
- [ ] `uv run haxjobs --help` shows usage with `start` subcommand
- [ ] `uv run pytest -q tests/` → 255 passed
- [ ] No bare `from db.` imports remaining anywhere
- [ ] `haxjobs.toml` findable from CWD, package dir, or `~/.haxjobs/`
- [ ] `dashctl.sh` and `dev-app.sh` deleted
- [ ] `plans/`, `docs/`, `tests/`, `cron/` still at root

## STOP conditions

Stop and report if:

- Test count drops below 255 after import changes
- `uv build` fails — check pyproject.toml syntax with `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`
- sed corrupts a file — check `git diff --stat` after step 3, look for mangled lines
- Any of `plans/`, `docs/`, `tests/`, `cron/` got moved — revert
- `uv init` doesn't exist — old uv version, upgrade: `uv self update`

## Maintenance notes

- `haxjobs_config.py` was renamed to `config.py` inside the package. Any old import of `haxjobs_config` is now `haxjobs.config`.
- The `haxjobs.toml` config file is searched in CWD → package dir → `~/.haxjobs/`. This means a user can copy the default from the package, edit it, and it takes precedence.
- Version is `1.0.0.dev0` — bump via `uv version 1.0.0` in plan 054.
