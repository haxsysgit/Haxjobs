# Plan 007: Clean Wheel for PyPI Publish

> **Executor:** DeepSeek V4 Pro (writer), DeepSeek V4 Flash (reviewers)
> **Depends on:** Plan 006 DONE
> **Drift stamp:** commit `0cd94fa` (Plan 006), `c2a4455` (v0.1.0 tag)
> **Status:** TODO
> **WARNING:** This plan is not final. The executor must compare it against live code before implementing. Deliver a completion report covering what changed, how it changed, and deliverables.

## Goal

Ship a wheel that contains only the Python package and runtime assets. Zero personal data. Zero dead code. Clean PyPI metadata.

## Why

The review forks found that the current wheel bundles Arinze's actual CV (`cv_profile.typed.json`), 8 personal `cv_source.md` files, personal profile drafts, and 7 application template directories. Publishing to PyPI would expose this publicly. Additionally, `__version__` is stale, `pyproject.toml` description is wrong, there's no LICENSE file, no classifiers, and `cv_variants/renderer.py` imports an undeclared `markdown` dependency.

## Scope

### In
- Exclude all personal data from the wheel (cv_variants/, profile/, application_templates/, cv_profile.typed.json)
- Fix `__version__` to `0.1.0` in `__init__.py`
- Add MIT LICENSE file
- Fix pyproject.toml description, add classifiers, add urls
- Rewrite README.md for PyPI/installed user audience
- Handle `markdown` dependency (exclude renderer.py or declare markdown)
- Verify wheel contents with `uv build --wheel && unzip -l dist/*.whl`

### Out
- PyPI upload itself (owner-controlled)
- Dev/prod separation improvements (Plan 008)
- Code quality refactoring (Plan 009)

## Files

### Modify
- `src/haxjobs/__init__.py` — fix version string
- `pyproject.toml` — description, classifiers, urls, wheel exclusions
- `README.md` — rewrite for installed users

### Create
- `LICENSE` — MIT text
- `deliverables/007-clean-wheel/README.md`
- `deliverables/007-clean-wheel/report.md`
- `deliverables/007-clean-wheel/plan.md`
- `deliverables/007-clean-wheel/wheel-audit.txt` — output of `unzip -l` on the wheel

### Delete or Exclude from Wheel
- `src/haxjobs/cv_variants/` — 8 role-family directories with personal CVs (exclude, do not delete from repo — kept as personal refs)
- `src/haxjobs/profile/` — personal profile drafts (exclude)
- `src/haxjobs/application_templates/` — dead cover letter/brief/pack templates (exclude)
- `src/haxjobs/cv_profile.typed.json` — personal typed profile (exclude)
- `src/haxjobs/cv_variants/renderer.py` — imports undeclared markdown (exclude)

## Phase 1: Exclude personal data from wheel

### Task 1: Configure hatchling exclusions

Hatchling includes everything under `src/haxjobs/` by default. Add explicit exclusions to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/haxjobs"]
exclude = [
    "src/haxjobs/cv_variants",
    "src/haxjobs/profile",
    "src/haxjobs/application_templates",
    "src/haxjobs/cv_profile.typed.json",
    "src/haxjobs/scripts",
]
```

Verify by building the wheel and listing contents:

```bash
uv build --wheel
python3 -c "import zipfile; z=zipfile.ZipFile('dist/haxjobs-0.1.0-py3-none-any.whl'); [print(n) for n in sorted(z.namelist())]"
```

Confirm no `cv_variants/`, `profile/`, `application_templates/`, `cv_profile.typed.json`, or `scripts/` appear.

### Task 2: Verify no code breaks

Run the full test suite. The excluded directories are not imported by any code under `src/haxjobs/`. If any test imports from them, that test is testing dead code and should be deleted.

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
```

Expected: 290 tests pass as before.

## Phase 2: Fix package metadata

### Task 3: Fix `__version__`

In `src/haxjobs/__init__.py`, change:

```python
__version__ = "1.0.0.dev0"
```

to:

```python
__version__ = "0.1.0"
```

### Task 4: Fix pyproject.toml metadata

Replace the current sparse `pyproject.toml` project section. Current:

```toml
[project]
name = "haxjobs"
version = "0.1.0"
description = "Self-hosted job search platform"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [{name = "Arinze Elenasulu"}]
readme = "README.md"
```

New:

```toml
[project]
name = "haxjobs"
version = "0.1.0"
description = "Conversational career agent — your personal job-search harness"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [{name = "Arinze Elenasulu"}]
readme = "README.md"
keywords = ["career", "job-search", "agent", "cli", "employment"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Office/Business",
    "Environment :: Console",
]

[project.urls]
Homepage = "https://github.com/haxsysgit/Haxjobs"
Repository = "https://github.com/haxsysgit/Haxjobs"
Issues = "https://github.com/haxsysgit/Haxjobs/issues"
```

### Task 5: Create LICENSE file

Create `LICENSE` at repo root with standard MIT text:

```text
MIT License

Copyright (c) 2025-2026 Arinze Elenasulu

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

(Use the standard full MIT text from https://opensource.org/license/mit)

## Phase 3: Rewrite README for PyPI and installed users

### Task 6: Rewrite README.md

The current README describes checkout dev workflow (`PYTHONPATH=src:.`, `uv run --`). The PyPI README must describe the installed user experience.

Required sections:
1. **What HaxJobs is** — conversational career agent, runs in terminal, helps you find and evaluate jobs
2. **Install** — `pip install haxjobs` or `uv tool install haxjobs`
3. **First run** — `haxjobs setup` (configure provider), `haxjobs` (start chatting)
4. **Features** — honest list of what's working: terminal chat, career graph, saved jobs, assessments, decisions
5. **Requirements** — Python 3.12+, an OpenAI-compatible API key (DeepSeek, OpenAI, or custom)
6. **Development** — separate section: clone repo, `uv sync --dev`, `PYTHONPATH=src:. uv run -- haxjobs chat --fake`
7. **License** — MIT

Keep it under 80 lines. No em dashes. Natural tone.

## Phase 4: Verification

### Task 7: Full verification

```bash
# Tests
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/

# Compile
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')

# Lock
uv lock --check

# Wheel contents audit
uv build --wheel
python3 -c "
import zipfile
z = zipfile.ZipFile('dist/haxjobs-0.1.0-py3-none-any.whl')
names = sorted(z.namelist())
for n in names:
    print(n)
# Verify no cv_variants, profile, application_templates
assert not any('cv_variants' in n for n in names), 'cv_variants in wheel!'
assert not any('/profile/' in n for n in names), 'profile in wheel!'
assert not any('cv_profile.typed' in n for n in names), 'cv_profile in wheel!'
assert not any('application_templates' in n for n in names), 'templates in wheel!'
print('Wheel audit: CLEAN')
"

# wheel install + import test
uv build --wheel
TMP=$(mktemp -d)
uv venv "$TMP/.venv"
uv pip install --python "$TMP/.venv/bin/python" dist/haxjobs-0.1.0-py3-none-any.whl
"$TMP/.venv/bin/python" -c "import haxjobs; print(haxjobs.__version__); assert haxjobs.__version__ == '0.1.0'"
rm -rf "$TMP"
```

## Deliverables

After implementation, create `deliverables/007-clean-wheel/` with:
- `plan.md` — copy of this plan
- `report.md` — implementation report with changed files, test count, wheel audit output
- `wheel-audit.txt` — full `unzip -l` output showing clean wheel contents
- `README.md` — deliverable index
