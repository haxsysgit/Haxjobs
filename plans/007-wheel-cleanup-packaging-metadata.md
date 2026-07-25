# Plan 007 — Wheel Cleanup and Packaging Metadata

> **Baseline:** `c2a4455` (v0.1.0 tag)
> **Drift stamp:** 2026-07-25 against commit `c2a4455`
> **Status:** TODO
> **Depends on:** Plan 006 DONE

## Goal

Clean the wheel so it contains only package code — no personal CV data, no dead templates, no untracked drafts. Fix packaging metadata: version string, classifiers, license, description. Result: `uv publish` ships a professional-looking package with zero personal data leaks.

---

## Scope

### In

- Exclude `cv_variants/`, `profile/`, `application_templates/`, `cv_profile.typed.json`, `scripts/seed-cv-variants-from-packs`, and `scripts/pull-cv-variants` from the wheel
- Fix `__version__` in `src/haxjobs/__init__.py`
- Fix `description` in `pyproject.toml` (currently "Self-hosted job search platform")
- Add full `classifiers` to `pyproject.toml`
- Add `keywords`, `urls` to `pyproject.toml`
- Create `LICENSE` file with MIT text
- Declare `markdown` dependency or remove `cv_variants/renderer.py` import
- Verify wheel contents with `uv build --wheel && unzip -l dist/*.whl`
- Verify `twine check` passes

### Out

- PyPI publish (user does this)
- Removing files from git (they stay in the repo, just not in the wheel)
- Changing the runtime code
- Version bump beyond metadata fixes

---

## Files

### Modify

- `src/haxjobs/__init__.py` — version string
- `pyproject.toml` — description, classifiers, keywords, urls, license, wheel exclude, markdown dep
- `LICENSE` — create

### Inspect only

- `dist/*.whl` — verify no personal data files
- `uv build --wheel` output

---

## Phase 1: Fix version and description

### Task 1: Fix `__version__`

**File:** `src/haxjobs/__init__.py`

Change line 2 from:
```python
__version__ = "1.0.0.dev0"
```
to:
```python
__version__ = "0.1.0"
```

### Task 2: Fix `description`

**File:** `pyproject.toml`

Change:
```toml
description = "Self-hosted job search platform"
```
to:
```toml
description = "Conversational career agent — your personal job-search harness"
```

---

## Phase 2: Add classifiers, keywords, urls

### Task 3: Add standard PyPI classifiers

**File:** `pyproject.toml`

Add under `[project]`:

```toml
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Topic :: Office/Business",
]
```

### Task 4: Add keywords and urls

```toml
keywords = ["career", "job-search", "agent", "ai", "employment", "cli"]
urls = { GitHub = "https://github.com/haxsysgit/Haxjobs" }
```

---

## Phase 3: Create LICENSE file

### Task 5: Write MIT LICENSE

**File:** `LICENSE` (new)

Standard MIT license with copyright holder placeholder. Use the inline text from `pyproject.toml` as the canonical source.

---

## Phase 4: Exclude personal data from wheel

### Task 6: Add hatchling exclude patterns

**File:** `pyproject.toml`

The current build config is:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/haxjobs"]
```

This includes everything under `src/haxjobs/` — CV variants, profile drafts, application templates, scripts. Add exclusions:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/haxjobs"]
exclude = [
    "src/haxjobs/cv_variants",
    "src/haxjobs/cv_profile.typed.json",
    "src/haxjobs/profile",
    "src/haxjobs/application_templates",
    "src/haxjobs/scripts",
]
```

Note: `scripts/` at the repo root is not under `src/haxjobs/` so doesn't ship. `src/haxjobs/scripts/` if it exists would.

### Task 7: Remove or declare `markdown` dependency

**File:** `pyproject.toml`

`src/haxjobs/cv_variants/renderer.py` imports `markdown`. Since `cv_variants/` is excluded from the wheel, this import won't ship. But we should also clean up:

Option A: Add `markdown` as an optional dependency (adds a dep for dead code)
Option B: Delete `cv_variants/renderer.py` from the repo (simplest, since cv_variants is excluded anyway)

Choose **Option B** — delete the renderer. CV variant rendering is legacy code from the pre-greenfield era. The greenfield runtime generates context from CareerStore, not from template files.

---

## Phase 5: Verify the wheel

### Task 8: Check wheel contents

```bash
uv build --wheel
unzip -l dist/haxjobs-0.1.0-py3-none-any.whl | grep -E 'cv_|profile|application_template|renderer'
```

Must produce NO output — none of the excluded paths should appear.

### Task 9: Verify with twine

```bash
uv run -- twine check dist/*.whl
```

Must pass with no warnings or errors.

---

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/    # all 290 tests pass
uv build --wheel                                           # clean build
unzip -l dist/haxjobs-*.whl | grep -c 'cv_variants'        # 0 matches
uv run -- twine check dist/*.whl                           # passes
git diff --check                                            # clean
```

---

## Stop conditions

- Any personal data file (name, location, CV content, profile) appears in the wheel
- `twine check` fails
- Test suite regresses below 290

---

## Deliverables

- Clean wheel with zero personal data
- Professional PyPI metadata
- LICENSE file
