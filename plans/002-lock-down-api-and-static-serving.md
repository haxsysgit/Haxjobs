# Plan 002: Lock down API and static file boundaries

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report instead of improvising.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- api_server.py server/routes/jobs.py server/routes/resources.py server/routes/pack_resources.py tests`
> If any in-scope file changed, compare Current state excerpts with live code before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: security
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

The HaxJobs API controls personal job-search state, pack generation, outreach approvals, and pipeline execution. It currently binds to all interfaces, allows wildcard CORS, has unauthenticated mutating routes, serves static files without a path containment check, and accepts filesystem paths for pack generation from request bodies. That is too much trust for a local/VPS control surface.

## Current state

Relevant files:
- `api_server.py` — stdlib HTTP server and route dispatcher.
- `server/routes/jobs.py` — job action routes, including `generate_job_pack`.
- `server/routes/resources.py` — pack download/static-ish resource helpers.
- `server/routes/pack_resources.py` — safer pack detail path pattern to reuse.
- `tests/test_pack_detail_api.py` — existing path traversal tests for pack detail.

Current excerpts:
- `api_server.py:53-56`: `_cors()` sends `Access-Control-Allow-Origin: *` and broad methods.
- `api_server.py:183-186`: static fallback joins `DASHBOARD_DIR` with `path.lstrip('/')` and serves it if `os.path.isfile(filepath)`.
- `api_server.py:196-199`: `do_POST` parses JSON before route dispatch without malformed-body handling.
- `api_server.py:202-292`: POST routes mutate jobs, packs, profile, whitelist, favorites, saved jobs, and outreach without auth.
- `api_server.py:301-305`: server binds `HTTPServer(("0.0.0.0", port), APIHandler)`.
- `server/routes/jobs.py:116-122`: API request body controls `output_root`, `registry_path`, `profile_path`, and `threshold` for pack generation.
- `packs_builder/job_pack.py:50-66`: pack generation creates directories and writes files under supplied `output_root`.

Repo conventions:
- Keep Python stdlib style. There is no FastAPI framework here.
- Existing safety helper `server/routes/pack_resources.py` uses `Path.resolve()` and `relative_to()` to restrict paths. Reuse that style.
- Do not read or print secrets. Do not touch `.env`.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Focused tests | `python3 -m pytest tests/test_pack_detail_api.py tests/test_manual_pack_generation.py -q` | exit 0 |
| Full Python tests | `python3 -m pytest -q` | exit 0 |
| Python syntax | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)` | exit 0 |

## Scope

In scope:
- `api_server.py`
- `server/routes/jobs.py`
- `server/routes/resources.py`
- `server/routes/pack_resources.py` if shared helpers are useful
- Tests under `tests/` for API helper behavior
- `.env.example` only if documenting a new non-secret env var

Out of scope:
- Replacing the stdlib HTTP server with FastAPI.
- Public internet deployment changes outside repo files.
- Reading `.env` values or printing tokens.
- Implementing a full user/account system.

## Git workflow

- Branch suggestion: `advisor/002-lock-down-api-boundaries`
- Use one or two logical commits: API boundary changes, then tests/docs.

## Steps

### Step 1: Add static file containment

Before serving a dashboard file, resolve the requested path and require it to remain under the resolved dashboard root. Reject escaped paths with a JSON 404/400. Do not rely on string prefix checks; use `Path.resolve()` plus `relative_to()` like `server/routes/pack_resources.py`.

Verify: add a regression test that a path like `/../profile/arinze_profile.local.json` or encoded traversal is not served, then run `python3 -m pytest <new test file> -q` → exit 0.

### Step 2: Remove client-controlled filesystem paths from the HTTP pack generation route

In `server/routes/jobs.py`, `generate_job_pack(body)` should accept only `job_id` for normal HTTP use. Do not pass `output_root`, `registry_path`, or `profile_path` from `body`. Keep CLI/test-level configurability in `generate_ready_packs.generate_pack_for_job`; only the HTTP route should stop trusting request paths.

Update tests that relied on API body path overrides by calling the lower-level function directly or monkeypatching constants safely. Add a route-level regression test proving body path overrides are ignored.

Verify: `python3 -m pytest tests/test_manual_pack_generation.py -q` → exit 0.

### Step 3: Add minimal server-side API protection

Pick the smallest protection compatible with local/VPS usage:
- Prefer binding to `127.0.0.1` by default and allow `HAXJOBS_API_HOST` override for Archilles only if required.
- Add optional token auth for mutating `/api/*` POST routes using an env var such as `HAXJOBS_API_TOKEN`. If the token env var is set, require `Authorization: Bearer <token>` or `X-HaxJobs-Token`. Do not log the token. If not set, allow local loopback clients only.
- Restrict CORS to configured local dashboard origins, e.g. `http://127.0.0.1:5173`, `http://localhost:5173`, plus same-origin production. Avoid wildcard CORS for credentialed/mutating paths.

If the repo has a deployment script that assumes `0.0.0.0`, update it or document the env var in `.env.example`/README without secrets.

Verify: add tests/helper checks for authorized vs unauthorized mutation requests if practical. At minimum run Python compile and focused tests.

### Step 4: Return structured 400 for malformed POST bodies

Wrap JSON parsing in a helper that catches malformed JSON and invalid lengths, caps body size to a reasonable value, and returns `{"ok": false, "error": "invalid JSON"}` with HTTP 400. Ensure unknown valid routes still return existing JSON 404.

Verify: add a small handler/helper test if possible; otherwise run Python compile and full tests.

## Test plan

Add/adjust tests for:
- Static traversal rejected.
- `/api/jobs/generate-pack` ignores request-controlled path fields or rejects them.
- Malformed JSON returns 400 JSON instead of crashing.
- Existing safe pack detail tests still pass.

Use `tests/test_pack_detail_api.py` and `tests/test_manual_pack_generation.py` style: direct helper calls, temp dirs, and monkeypatching instead of starting a real server where possible.

## Done criteria

- [ ] Static files cannot escape `DASHBOARD_DIR` after resolving paths.
- [ ] HTTP pack generation no longer accepts client-controlled filesystem paths.
- [ ] Mutating API routes have a documented protection boundary.
- [ ] Malformed POST bodies get structured 400 JSON.
- [ ] Focused tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python compile command exits 0.
- [ ] No secrets are read, printed, or committed.
- [ ] `plans/README.md` row 002 updated when done.

## STOP conditions

Stop and report if:
- Archilles deployment truly requires public unauthenticated API access.
- Adding auth would require modifying gateway secrets or live `.env` values.
- Tests require starting the live Archilles service instead of local helper-level tests.

## Maintenance notes

A future Telegram action loop should depend on this API boundary. Reviewers should check that no route reintroduces request-body filesystem paths.
