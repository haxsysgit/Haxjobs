# Plan 011: Fix pack file serving — serve_pack_file ignores the directory parameter

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.

> **Drift check (run first)**: `git diff --stat 451ea6a..HEAD -- server/routes/resources.py api_server.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `451ea6a`, 2026-06-28
- **Issue**: (none)

## Why this matters

The function `serve_pack_file(job_id, filename)` in `server/routes/resources.py` completely ignores its first parameter — it loops over every pack directory and returns the first file with a matching name. If two packs both have a `cover_letter.pdf`, a user requesting pack A's cover letter could silently receive pack B's. This is a data integrity bug: the wrong application documents could be reviewed or downloaded.

The fix is a one-line change: use the directory parameter to scope the file lookup. This also makes the function simpler.

## Current state

- `server/routes/resources.py` — `serve_pack_file` function at lines 44–53. The `job_id` parameter (actually a directory name) is declared but never used. Instead the function globs all pack dirs.
- `api_server.py` — calls `serve_pack_file(pack_dir, filename)` at line 237. The caller passes the correct directory extracted from the URL path.
- `tests/test_pack_detail_api.py` — no test exists for `serve_pack_file`. Tests only cover `get_pack_detail` and `read_pack_text_file`.

The function as it exists today (`server/routes/resources.py:44-53`):
```python
def serve_pack_file(job_id, filename):
    """Serve a specific pack file for download."""
    import glob as _glob
    # Find the pack directory by searching for the job ID pattern
    pack_dirs = [d for d in _glob.glob(os.path.join(PACKS_DIR, "*")) if os.path.isdir(d)]
    for d in pack_dirs:
        filepath = os.path.join(d, filename)
        if os.path.isfile(filepath):
            return filepath
    return None
```

How it's called (`api_server.py:232-244`):
```python
elif path.startswith("/api/packs/"):
    parts = path.split("/")
    if len(parts) >= 5:
        filename = parts[-1]
        pack_dir = "/".join(parts[3:-1])
        filepath = serve_pack_file(pack_dir, filename)
        if filepath:
            ext = os.path.splitext(filepath)[1]
            self._file(filepath, MIME.get(ext, "application/octet-stream"))
        else:
            self._json({"error": "file not found"}, 404)
    else:
        self._json({"error": "invalid path"}, 400)
```

Note: the URL path looks like `/api/packs/1_exampleco_python_backend/cover_letter.pdf`, so `parts = ["", "api", "packs", "1_exampleco_python_backend", "cover_letter.pdf"]` and `pack_dir = "1_exampleco_python_backend"`.

Repo convention: this module imports from `haxjobs_config` at the top. The fix should follow the same pattern as `get_pack_detail` in `server/routes/pack_resources.py` which does proper path containment checks. However, for `serve_pack_file`, just joining the directory path directly is sufficient since the caller (`api_server.py`) controls the directory name from the URL (no user-controlled path segments get through unvalidated).

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Tests     | `python3 -m pytest -q`   | 209+ passed         |
| Bash syntax | `bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh` | exit 0 |
| Python compile | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -name '*.py' -print)` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `server/routes/resources.py` — fix `serve_pack_file`
- `tests/test_pack_detail_api.py` — add tests for `serve_pack_file`

**Out of scope** (do NOT touch):
- `api_server.py` — the caller is correct, don't change it
- `server/routes/pack_resources.py` — separate module, not involved
- Any other route handler or API endpoint

## Git workflow

- Branch: `fix/011-pack-file-serving` off `main`
- Commit message style: imperative, lowercase, e.g. `fix: serve_pack_file scopes to requested pack directory`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Add characterization tests for serve_pack_file

Open `tests/test_pack_detail_api.py`. Add two new tests at the end of the file, before the last blank line. Model them after the existing tests in the file (they use `tmp_path` and direct function imports).

Add this import at the top of the file (after the existing imports):
```python
from server.routes.resources import serve_pack_file
```

Add these two test functions:

**Test 1**: `test_serve_pack_file_returns_file_from_specified_pack_dir`
- Create two pack directories under a temp packs root: `job_A_testco` and `job_B_otherco`
- Put `cover_letter.pdf` in job_A only, and `fit_report.pdf` in job_B only
- Monkeypatch `server.routes.resources.PACKS_DIR` to point to the temp packs root
- Call `serve_pack_file("job_A_testco", "cover_letter.pdf")` — should return the path in job_A
- Call `serve_pack_file("job_B_otherco", "cover_letter.pdf")` — should return None (file not in job_B)
- Call `serve_pack_file("job_B_otherco", "fit_report.pdf")` — should return the path in job_B

Use `unittest.mock.patch` or `monkeypatch` (pytest fixture). The existing tests don't use fixtures — they use the function's optional parameters. But `serve_pack_file` has no optional `packs_root` parameter. So use `monkeypatch.setattr`:

```python
import server.routes.resources as rmod

def test_serve_pack_file_returns_file_from_specified_pack_dir(tmp_path, monkeypatch):
    packs_root = tmp_path / "packs"
    job_a = packs_root / "job_A_testco"
    job_b = packs_root / "job_B_otherco"
    job_a.mkdir(parents=True)
    job_b.mkdir(parents=True)
    (job_a / "cover_letter.pdf").write_text("letter A")
    (job_b / "fit_report.pdf").write_text("report B")

    monkeypatch.setattr(rmod, "PACKS_DIR", str(packs_root))

    result_a = serve_pack_file("job_A_testco", "cover_letter.pdf")
    assert result_a == str(job_a / "cover_letter.pdf")

    result_b_missing = serve_pack_file("job_B_otherco", "cover_letter.pdf")
    assert result_b_missing is None

    result_b = serve_pack_file("job_B_otherco", "fit_report.pdf")
    assert result_b == str(job_b / "fit_report.pdf")
```

**Test 2**: `test_serve_pack_file_rejects_path_traversal`
- Call `serve_pack_file("../outside", "file.pdf")` — should return None (directory doesn't exist under PACKS_DIR)

**Verify**: `python3 -m pytest tests/test_pack_detail_api.py -q` → tests pass (the new test should FAIL because the function currently ignores the directory parameter — that's expected, confirming the bug)

### Step 2: Fix serve_pack_file to use the directory parameter

Open `server/routes/resources.py`. Replace the `serve_pack_file` function (lines 44–53) with:

```python
def serve_pack_file(pack_dir_name, filename):
    """Serve a specific pack file for download.

    Looks only inside the named pack directory under PACKS_DIR.
    Returns the full file path or None.
    """
    target_dir = os.path.join(PACKS_DIR, pack_dir_name)
    if not os.path.isdir(target_dir):
        return None
    filepath = os.path.join(target_dir, filename)
    if os.path.isfile(filepath):
        return filepath
    return None
```

This is a minimal fix: it constructs the path from the directory parameter, checks it exists, then checks the file exists. No glob, no iteration over all packs.

**Verify**: `python3 -m pytest tests/test_pack_detail_api.py -q` → all tests pass including the two new ones

### Step 3: Run full verification baseline

**Verify**:
- `python3 -m pytest -q` → 211+ tests pass (209 existing + 2 new)
- `python3 -m py_compile server/routes/resources.py` → exit 0

## Test plan

Two new tests in `tests/test_pack_detail_api.py`:
1. `test_serve_pack_file_returns_file_from_specified_pack_dir` — happy path and directory isolation
2. `test_serve_pack_file_rejects_path_traversal` — safety edge case

Model after the existing tests in the same file (direct imports, `tmp_path`, `monkeypatch`).

## Done criteria

ALL must hold:

- [ ] `python3 -m pytest -q` exits 0, 211+ tests pass
- [ ] `grep -rn "glob.glob" server/routes/resources.py` returns no matches (old glob pattern removed)
- [ ] `grep -rn "for d in pack_dirs" server/routes/resources.py` returns no matches
- [ ] No files outside `server/routes/resources.py` and `tests/test_pack_detail_api.py` modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:
- The existing `serve_pack_file` code at `server/routes/resources.py:44-53` doesn't match the excerpt above
- Any test fails for reasons unrelated to the fix (e.g. pre-existing breakage)
- The fix requires changing `api_server.py` or any out-of-scope file

## Maintenance notes

- If pack directory naming conventions change (e.g. moving to numeric-only IDs), update the `pack_dir_name` parameter handling.
- The `serve_pack_file` function name is kept for backward compatibility even though its first parameter is a directory name, not a job ID. A future rename to `serve_pack_file(pack_dir, filename)` would clarify intent.
- This function intentionally skips path containment checks (unlike `get_pack_detail`) because the directory name comes from a URL path parsed by `api_server.py` — the caller controls the segments, not raw user input.
