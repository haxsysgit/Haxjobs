# Plan 010: Package HaxJobs as installable engine (v0.1.8)

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. Stop on any STOP condition.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- pyproject.toml setup.py setup.cfg`
> If `pyproject.toml` already exists with a different intent, reconcile — do not overwrite an active packaging config.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: plans/001 through 009 (all must be DONE)
- **Category**: packaging / release / product
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

HaxJobs currently lives as a tightly-coupled personal monorepo: hardcoded `/home/hermes/` paths, Arinze's profile, CVs, company lists, cookies, and personal templates live alongside the engine code. The goal is to split it into two things:

1. **HaxJobs Engine** — `~/haxjobs_prod/` — a clean, uv-installable Python package that Hermes (and later Claude Code / Codex / OpenClaw) can drop into any agent environment.
2. **Arinze's Personal Deployment** — `~/haxjobs/` — his profile, CVs, templates, company lists, and runtime state. This lives where it is today and consumes the engine.

The engine should be a well-designed automation template: agents install it, configure their own company lists and credentials, and get the same discovery → evaluation → pack pipeline Arinze uses.

## Product direction

- **First release (v0.1.8)**: current code, configurable paths, no personal data. Clean enough to point another Hermes user at and say "uv add haxjobs, configure, run."
- **Versioning**: continue from 0.1.7 → 0.1.8 → 0.1.9 → 0.2.0. Tags and GitHub releases for each.
- **Target consumers**: Hermes agents first. Other agent platforms later.
- **Not in v0.1.8**: auto-setup scripts, interactive wizards, multi-user support. Those are 0.1.9+.

## Current state

Relevant files (all under `/home/hax/haxjobs/`):
- `api_server.py` — hardcodes `/home/hermes/haxjobs`, wildcard CORS (until Plan 002 fixes it)
- `evaluate_with_hermes.py` — hardcodes `BASE_DIR`, `PROFILE_PATH`, `INTAKE_DIR`
- `pipeline_db.py`, `db/` — hardcodes DB path
- `cron/` — hardcodes Archilles paths and SSH references
- `discovery/` — hardcodes company lists and API URLs
- `profile/` — Arinze's personal profile (must not ship)
- `cv_variants/` — Arinze's CVs (must not ship)
- `application_templates/` — mix of personal and reusable templates
- `packs_builder/job_pack.py` — hardcodes paths
- No `pyproject.toml` or packaging config exists
- No git tags or GitHub releases exist after 0.1.7 (if 0.1.7 was ever tagged)

Current excerpts that will need replacement:
- `evaluate_with_hermes.py:16-18`: `BASE_DIR = "/home/hermes/haxjobs"`, `INTAKE_DIR = os.path.join(BASE_DIR, "intake")`, `PROFILE_PATH = os.path.join(BASE_DIR, "profile", "arinze_profile.local.json")`
- `api_server.py:13-18`: `DASHBOARD_DIR`, `PACKS_DIR`, `PROFILE_PATH` all hardcode absolute paths
- `db/schema.py:5`: `DB_PATH = os.environ.get("PIPELINE_DB", os.path.join("/home/hermes/haxjobs/state/pipeline.db"))` — has env var but defaults to personal path
- `discovery/` files: company slugs hardcoded in `.txt` files and scraper scripts

Repo conventions to carry forward:
- Python stdlib + SQLite + pytest, no FastAPI
- Tests use temp DB monkeypatches — these already work with configurable paths
- Readable code standard applies

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Run from config path | `haxjobs serve --help` | prints usage |
| Evaluator with config | `haxjobs evaluate --help` | prints usage |
| Engine tests | `cd ~/haxjobs_prod && uv run python3 -m pytest -q` | exit 0 |
| Import check | `uv run python3 -c "import haxjobs; print(haxjobs.__version__)"` | prints `0.1.8` |
| No personal data | `grep -r 'arinze\|0\.0\.0\.0\|elenasulu\|linkedin_cookies' ~/haxjobs_prod/haxjobs/` | exit 1 (no matches) |
| Dashboard build | `cd ~/haxjobs_prod/dashboard && npm run build` | exit 0 |
| Git tag | `git tag v0.1.8` | creates tag |

## Scope

In scope:
- Create `~/haxjobs_prod/` as new git repo with clean commit history
- Write `pyproject.toml` with uv support, entry points (`haxjobs serve`, `haxjobs evaluate`, `haxjobs pipeline`)
- Move engine source to `haxjobs/` package directory under `~/haxjobs_prod/`
- Strip all personal data: Arinze's name, email, profile, CVs, cookies, company lists, hardcoded Archilles paths
- Replace hardcoded paths with `HAXJOBS_HOME` env var or config file (`~/.config/haxjobs/config.toml`)
- Keep discovery scrapers generic: config-driven company lists, empty by default; include a setup guide
- Include dashboard source (it's part of the product)
- Tag v0.1.8 and create GitHub release with release notes
- Keep `~/haxjobs/` as Arinze's personal deployment — it should point to the engine package

Out of scope:
- Publishing to PyPI (GitHub-only)
- Auto-install scripts for other users
- Migrating Arinze's runtime data (state/pipeline.db stays where it is)
- Interactive setup wizard
- Multi-user database support
- Removing `~/haxjobs/` — it stays as Arinze's personal deployment

## Git workflow

- The engine gets a NEW repo: `~/haxjobs_prod/`
- Remote: `https://github.com/haxsysgit/haxjobs-engine.git` (create this)
- OR: keep `https://github.com/haxsysgit/Haxjobs.git` and use a `release/0.1.8` branch
- Decision point: the user needs to confirm whether to use a new repo or the existing one

- Branch: `main` (fresh), then `git tag v0.1.8`
- Commit style: imperative, conventional commits preferred (`feat: add entry points`, `chore: strip personal data`)

## Steps

### Step 1: Create the engine repository structure

```bash
mkdir -p ~/haxjobs_prod/haxjobs
```

Package layout:
```
~/haxjobs_prod/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── AGENTS.md                    ← agent guide (from Plan 008, adapted)
├── haxjobs/
│   ├── __init__.py              ← __version__ = "0.1.8"
│   ├── server.py                ← renamed api_server, configurable
│   ├── evaluate.py              ← evaluator, configurable paths
│   ├── pipeline.py              ← pipeline runner
│   ├── pack_builder/            ← pack generation (copy from packs_builder/)
│   ├── db/                      ← database layer
│   ├── discovery/               ← generic scrapers (no personal data)
│   ├── config.py                ← unified config loader
│   └── cli.py                   ← entry points (serve, evaluate, pipeline)
├── dashboard/                   ← React + TypeScript + Vite (copy from dashboard/)
├── tests/                       ← tests (copy and adapt)
├── config.example.toml          ← template config
└── discovery_companies.example/ ← example company lists (empty or generic)
```

Verify structure exists with `ls -la ~/haxjobs_prod/haxjobs/`.

### Step 2: Write pyproject.toml

Use uv-compatible format:

```toml
[project]
name = "haxjobs"
version = "0.1.8"
description = "Agent-native job discovery and application pipeline"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    # Only stdlib + Playwright for discovery scrapers
    "playwright",
]
[project.scripts]
haxjobs = "haxjobs.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Verify: `uv run python3 -c "import haxjobs"` works from `~/haxjobs_prod/`.

### Step 3: Move engine source and strip personal data

For each source file being moved from `~/haxjobs/` to `~/haxjobs_prod/haxjobs/`:

1. Copy the file
2. Replace hardcoded personal paths with config lookups via `haxjobs.config`
3. Remove personal data: Arinze's name, email, profile facts, CV content, company lists, LinkedIn cookies
4. Keep the logic, structure, and algorithms

**Files to move and clean:**

| Source | Destination | Personal data to strip |
|---|---|---|
| `api_server.py` | `haxjobs/server.py` | `DASHBOARD_DIR`, `PACKS_DIR`, `PROFILE_PATH`, `0.0.0.0` binding, wildcard CORS (fixed by Plan 002) |
| `evaluate_with_hermes.py` | `haxjobs/evaluate.py` | `BASE_DIR`, `INTAKE_DIR`, `PROFILE_PATH`, profile facts in prompt builder, Arinze's name/location/preferences in `build_profile_blurb()` |
| `pipeline_db.py` + `db/` | `haxjobs/db/` + `haxjobs/pipeline.py` | `DB_PATH` default, any hardcoded `/home/hermes/` |
| `packs_builder/` | `haxjobs/pack_builder/` | Path defaults |
| `discovery/` scrapers | `haxjobs/discovery/` | Company lists, cookie paths, Archilles SSH references |
| `generate_ready_packs.py` | `haxjobs/pack_builder/ready.py` | Path defaults |
| `cron/run_pipeline.sh` | N/A — becomes `haxjobs pipeline` CLI command | Archilles SSH, hardcoded paths |
| `profile/` | Stay in `~/haxjobs/` | N/A — never moves |
| `cv_variants/` | Stay in `~/haxjobs/` | N/A — never moves |
| `application_templates/` | `haxjobs/templates/` (reusable subset) | Arinze-specific wording — keep template structure, strip personal voice |

**No personal data check:** `grep -ri 'arinze\|elenasulu\|/home/hermes' ~/haxjobs_prod/haxjobs/` must return nothing except the word "arinze" appearing only in AGENTS.md as a documented example.

Verify: `uv run python3 -m pytest -q` from `~/haxjobs_prod/`.

### Step 4: Add config system

Create `haxjobs/config.py`:

```python
"""Unified config loader for HaxJobs.

Reads from (in order):
1. Environment variables (HAXJOBS_HOME, HAXJOBS_DB, etc.)
2. ~/.config/haxjobs/config.toml
3. Built-in defaults

Usage:
    from haxjobs.config import config
    db_path = config.db_path
"""

import os
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class HaxJobsConfig:
    home: Path = field(default_factory=lambda: Path(os.environ.get("HAXJOBS_HOME", os.path.expanduser("~/.local/share/haxjobs"))))
    db_path: Path | None = None
    profile_path: Path | None = None
    packs_dir: Path | None = None
    intake_dir: Path | None = None
    dashboard_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8800

    def __post_init__(self):
        if self.db_path is None:
            self.db_path = self.home / "state" / "pipeline.db"
        if self.packs_dir is None:
            self.packs_dir = self.home / "packs"
        if self.intake_dir is None:
            self.intake_dir = self.home / "intake"
        if self.profile_path is None:
            self.profile_path = self.home / "profile" / "profile.json"
        if self.dashboard_dir is None:
            self.dashboard_dir = Path(__file__).parent.parent / "dashboard" / "dist"

config = HaxJobsConfig()
```

Include `config.example.toml`:
```toml
# HaxJobs configuration
# Copy to ~/.config/haxjobs/config.toml and edit

home = "/home/you/haxjobs-data"
host = "127.0.0.1"
port = 8800
```

Verify: `uv run python3 -c "from haxjobs.config import config; print(config.home)"`.

### Step 5: Add CLI entry points

Create `haxjobs/cli.py`:

```python
"""HaxJobs CLI entry points.

Commands:
    haxjobs serve           Start API + dashboard server
    haxjobs evaluate --next  Evaluate next pending job
    haxjobs pipeline         Run one pipeline tick
"""
import sys

def cmd_serve():
    from haxjobs.server import run
    run()

def cmd_evaluate(args):
    from haxjobs.evaluate import evaluate_next
    evaluate_next()

def cmd_pipeline():
    from haxjobs.pipeline import run_tick
    run_tick()

def main():
    if len(sys.argv) < 2:
        print("Usage: haxjobs {serve|evaluate|pipeline}")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "serve":
        cmd_serve()
    elif cmd == "evaluate":
        cmd_evaluate(sys.argv[2:])
    elif cmd == "pipeline":
        cmd_pipeline()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
```

Verify: `uv run haxjobs --help` prints usage.

### Step 6: Copy and adapt tests

Copy tests from `~/haxjobs/tests/` to `~/haxjobs_prod/tests/`. Adapt imports from `import pipeline_db` to `from haxjobs.db import ...`. Keep temp DB monkeypatch patterns. Strip any tests that verify personal data content.

Verify: `uv run python3 -m pytest -q` executes tests from `~/haxjobs_prod/`.

### Step 7: Copy dashboard source

Copy `dashboard/` (React + TypeScript + Vite) to `~/haxjobs_prod/dashboard/`. Keep it as-is — it's already a generic SPA. Build it as part of engine setup. The server in `haxjobs/server.py` serves the built `dashboard/dist/`.

Verify: `cd ~/haxjobs_prod/dashboard && npm ci && npm run build` exits 0.

### Step 8: Write README and CHANGELOG

`README.md` for the engine (not Arinze's personal one):

```
# HaxJobs Engine

Agent-native job discovery, evaluation, and application pack pipeline.

## Quick Start

uv add haxjobs
mkdir -p ~/.config/haxjobs
cp config.example.toml ~/.config/haxjobs/config.toml
# Edit config: set your profile path, add company lists
haxjobs serve

## Requirements

- Python 3.10+
- Node.js 22+ (for dashboard build)
- Playwright (for browser scrapers)
- Hermes CLI (for LLM fit evaluation)
```

`CHANGELOG.md`:

```
## v0.1.8 (2026-06-27)

First packaged release.

- Extracted engine from personal monorepo
- Config-driven paths via HAXJOBS_HOME and config.toml
- CLI entry points: haxjobs serve, haxjobs evaluate, haxjobs pipeline
- Generic discovery scrapers with config-driven company lists
- Stripped all personal data
- Dashboard included as built asset
```

### Step 9: Git init, tag v0.1.8, push, release

```bash
cd ~/haxjobs_prod
git init
git add .
git commit -m "feat: HaxJobs engine v0.1.8 — first packaged release"
git tag v0.1.8

# Create GitHub repo and push
gh repo create haxsysgit/haxjobs-engine --public --source=. --push
# OR if using existing repo:
# git remote add origin https://github.com/haxsysgit/Haxjobs.git
# git push origin main --tags

# Create GitHub release
gh release create v0.1.8 --title "HaxJobs Engine v0.1.8" --notes-from-tag
```

Verify: `git tag -l v0.1.8` shows the tag. GitHub release exists.

### Step 10: Point Arinze's personal deployment at the engine

Keep `~/haxjobs/` as-is for Arinze's personal use. Add a note in `~/haxjobs/README.md`:

```
## Engine

This deployment uses the HaxJobs Engine package at ~/haxjobs_prod/.
To update: cd ~/haxjobs_prod && git pull && uv sync
```

Do NOT delete or modify `~/haxjobs/` runtime data.

## Test plan

- Engine tests pass in clean environment: `cd ~/haxjobs_prod && uv run python3 -m pytest -q`
- No personal data survives: grep for Arinze's name, email, hardcoded paths
- CLI entry points print usage
- Config loads from env var and config file
- Dashboard builds and can be served by the engine server
- GitHub release is accessible

## Done criteria

- [ ] `~/haxjobs_prod/` exists with clean package structure
- [ ] `pyproject.toml` enables `uv run haxjobs`
- [ ] `haxjobs serve`, `haxjobs evaluate`, `haxjobs pipeline` entry points exist
- [ ] No personal data in engine source (profile, CVs, companies, cookies, hardcoded paths)
- [ ] Config system (`haxjobs/config.py`) resolves paths from env/TOML
- [ ] Engine tests pass (`uv run python3 -m pytest -q`)
- [ ] Dashboard builds and is served
- [ ] `v0.1.8` git tag created
- [ ] GitHub release published with changelog
- [ ] `~/haxjobs/` remains intact as personal deployment
- [ ] `plans/README.md` row 010 updated when done

## STOP conditions

Stop and report if:
- The user wants a different repo name or org than `haxsysgit/haxjobs-engine`
- Any file contains personal data that cannot be safely config-ified without breaking core logic
- Dashboard build requires environment secrets not available in a clean checkout
- GitHub credentials are not available for repo creation and release

## Maintenance notes

- Version bumps follow `haxjobs/__init__.py` → `pyproject.toml` → git tag → GitHub release
- New features go into the engine first, then Arinze's personal deployment pulls updates
- The personal deployment (`~/haxjobs/`) and engine (`~/haxjobs_prod/`) have separate git histories
- Discovery company lists are config-driven; engine never ships with real company names
