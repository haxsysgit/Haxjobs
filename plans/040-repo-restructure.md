# Plan 040: Restructure repo into installable Python package

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

The repo is a flat directory of Python modules at root. `pip install haxjobs` requires a `pyproject.toml` and code under `src/haxjobs/`. This plan is the foundation — nothing else can ship until the package structure exists. Without it, HaxJobs requires cloning a repo and setting PYTHONPATH manually. With it, `pip install haxjobs && haxjobs start` works.

## Current state

All Python code lives at repo root:
```
haxjobs-private-dev/
├── api_server.py
├── pipeline_db.py
├── haxjobs_config.py
├── haxjobs.toml
├── db/
├── discovery/
├── evaluate/
├── evaluation/
├── packs_builder/
├── server/
├── profile/
├── scripts/
├── tests/
├── dashboard/         # React frontend (old)
├── cron/
├── plans/
└── docs/
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
- Test runner: `PYTHONPATH=. python3 -m pytest -q tests/`

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `PYTHONPATH=. python3 -m pytest -q tests/` | 255 passed |
| Compile check | `python3 -m py_compile src/haxjobs/__init__.py` after creation | clean |
| Verify package | `pip install -e . && haxjobs --help` | shows usage |
| Verify imports | `python3 -c "from haxjobs.db import jobs; print('ok')"` | ok |

## Scope

**In scope**:
- Create `pyproject.toml` at root
- Create `src/haxjobs/` package structure
- Move all Python modules into `src/haxjobs/`
- Update internal imports from `from db.x import y` to `from haxjobs.db.x import y`
- Update `haxjobs_config.py` to find `haxjobs.toml` relative to package
- Create `haxjobs` CLI entry point
- Update test imports

**Out of scope**:
- `dashboard/` — React frontend (handled in plan 042)
- `docs/`, `plans/`, `cron/` — move but don't modify
- `haxjobs.toml` — move to package data, don't change content

## Git workflow

- Branch from `main`, work directly
- Commit: `git commit -m "restructure repo into installable Python package"`
- Do NOT push or open PR

## Steps

### Step 1: Create pyproject.toml

Create `pyproject.toml` at repo root:

```toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

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
    "tomli>=2; python_version < '3.11'",
    "requests>=2.32",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
]

[project.scripts]
haxjobs = "haxjobs.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
haxjobs = ["haxjobs.toml", "py.typed"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"

[tool.setuptools.data-files]
"share/haxjobs" = ["haxjobs.toml"]
```

**Verify**: `python3 -m py_compile pyproject.toml` is a TOML-parse check — skip (tomllib validates on install). Instead: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` → exit 0

### Step 2: Create src/haxjobs/ package structure

```bash
mkdir -p src/haxjobs
```

Create `src/haxjobs/__init__.py`:
```python
"""HaxJobs — self-hosted job search platform."""
__version__ = "1.0.0.dev0"
```

**Verify**: `python3 -c "import sys; sys.path.insert(0,'src'); from haxjobs import __version__; print(__version__)"` → prints `1.0.0.dev0`

### Step 3: Move all Python modules into src/haxjobs/

Move these directories wholesale:
```bash
git mv db src/haxjobs/db
git mv discovery src/haxjobs/discovery
git mv evaluate src/haxjobs/evaluate
git mv evaluation src/haxjobs/evaluation
git mv packs_builder src/haxjobs/packs_builder
git mv server src/haxjobs/server
git mv profile src/haxjobs/profile
git mv scripts src/haxjobs/scripts
```

Move individual root Python files:
```bash
git mv api_server.py src/haxjobs/api_server.py
git mv pipeline_db.py src/haxjobs/pipeline_db.py
git mv haxjobs_config.py src/haxjobs/haxjobs_config.py
git mv generate_ready_packs.py src/haxjobs/generate_ready_packs.py
git mv check_dashboard.py src/haxjobs/check_dashboard.py
```

Move config:
```bash
git mv haxjobs.toml src/haxjobs/haxjobs.toml
```

Move non-Python dirs:
```bash
git mv application_templates src/haxjobs/application_templates
git mv cv_variants src/haxjobs/cv_variants
```

**Verify**: `ls src/haxjobs/db src/haxjobs/discovery src/haxjobs/evaluate` → all three exist

### Step 4: Update internal imports

All imports that were `from db.x import y` must become `from haxjobs.db.x import y`. Same for discovery, evaluate, evaluation, packs_builder, server, profile.

Run this find-replace across ALL `.py` files under `src/haxjobs/`:
```bash
# Update all absolute imports
find src/haxjobs -name "*.py" -exec sed -i \
  -e 's/from db\./from haxjobs.db./g' \
  -e 's/from discovery\./from haxjobs.discovery./g' \
  -e 's/from evaluate\./from haxjobs.evaluate./g' \
  -e 's/from evaluation\./from haxjobs.evaluation./g' \
  -e 's/from packs_builder\./from haxjobs.packs_builder./g' \
  -e 's/from server\./from haxjobs.server./g' \
  -e 's/from profile\./from haxjobs.profile./g' \
  -e 's/import haxjobs_config/import haxjobs.haxjobs_config/g' \
  -e 's/from haxjobs_config/from haxjobs.haxjobs_config/g' \
  {} +
```

Also update `__init__.py` files that do relative imports:
```bash
find src/haxjobs -name "__init__.py" -exec sed -i \
  -e 's/from \.\([a-z]\)/from haxjobs.\1/g' \
  {} +
```

**Verify**: `grep -rn "from db\." src/haxjobs/` → no matches. `grep -rn "from haxjobs.db" src/haxjobs/` → positive matches.

### Step 5: Update haxjobs_config.py to find haxjobs.toml

Edit `src/haxjobs/haxjobs_config.py`. Find where `haxjobs.toml` is loaded (likely `Path("haxjobs.toml")` or `"haxjobs.toml"`). Change to use package resources:

```python
from pathlib import Path

# Find haxjobs.toml: look in current dir first, then package dir
_TOML_PATH = Path("haxjobs.toml")
if not _TOML_PATH.exists():
    _TOML_PATH = Path(__file__).parent / "haxjobs.toml"
```

**Verify**: `grep "haxjobs.toml" src/haxjobs/haxjobs_config.py` → shows the new path resolution

### Step 6: Create CLI entry point

Create `src/haxjobs/cli.py`:

```python
"""HaxJobs CLI entry point."""
import sys

def main():
    print("HaxJobs v1.0.0 — coming soon")
    # ponytail: placeholder until FastAPI is wired in plan 041
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Verify**: `python3 -c "from haxjobs.cli import main; main()"` → prints message, exit 0

### Step 7: Update tests

Tests live at `tests/` (not under `src/`). Update their imports to use the new package paths:

```bash
find tests -name "*.py" -exec sed -i \
  -e 's/from db\./from haxjobs.db./g' \
  -e 's/from discovery\./from haxjobs.discovery./g' \
  -e 's/from evaluate\./from haxjobs.evaluate./g' \
  -e 's/from evaluation\./from haxjobs.evaluation./g' \
  -e 's/from packs_builder\./from haxjobs.packs_builder./g' \
  -e 's/from server\./from haxjobs.server./g' \
  -e 's/from profile\./from haxjobs.profile./g' \
  -e 's/import haxjobs_config/import haxjobs.haxjobs_config/g' \
  -e 's/from haxjobs_config/from haxjobs.haxjobs_config/g' \
  {} +
```

Update `tests/conftest.py` — the monkeypatch target changes:
```python
# Old: monkeypatch.setattr(schema_mod, "DB_PATH", db_path)
# New: unchanged — still monkeypatch haxjobs.db.schema.DB_PATH
# But the import line changes to:
import haxjobs.db.schema as schema_mod
```

**Verify**: `grep -rn "from db\." tests/` → no matches

### Step 8: Run tests with new PYTHONPATH

The test command changes — no more PYTHONPATH shuffle:

```bash
# Old: PYTHONPATH=. python3 -m pytest -q tests/
# New: pip install -e . && python3 -m pytest -q tests/
pip install -e . 2>&1 | tail -3
```

Then:
```bash
python3 -m pytest -q tests/
```

**Verify**: 255 passed (same as before)

### Step 9: Test CLI entry point

```bash
pip install -e . && haxjobs
```

**Verify**: prints version message, exit 0

### Step 10: Commit

```bash
git add -A
git commit -m "restructure repo into installable Python package under src/haxjobs/"
```

**Verify**: exit 0, working tree clean

## Test plan

No new tests. The existing 255-test suite verifies that imports and logic survived the restructure. The critical coverage: `python3 -m pytest -q tests/` returns 255 passed with the new import paths.

## Done criteria

- [ ] `pyproject.toml` exists at repo root
- [ ] All Python code under `src/haxjobs/`
- [ ] `pip install -e .` succeeds
- [ ] `haxjobs` command prints usage
- [ ] `python3 -m pytest -q tests/` → 255 passed
- [ ] No bare `from db.` imports remaining in src/ or tests/
- [ ] `haxjobs.toml` findable by `haxjobs_config.py` from any working directory

## STOP conditions

Stop and report if:

- Test count drops below 255 after import changes
- Any module raises ImportError at install time
- `pip install -e .` fails with setuptools version errors on the user's system
- sed corrupts a file with mixed quote styles — check `git diff` after step 4

## Maintenance notes

The `pyproject.toml` version is `1.0.0.dev0` — bump to `1.0.0` in the final release plan (054). Dependencies are intentionally minimal: FastAPI + uvicorn for the server, requests for scrapers. Add more as needed in later plans, not upfront.
