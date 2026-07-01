# Handoff

**Current repo:** `/home/hax/haxjobs`

## Completed product-wave plans

- **038** — under-construction signal
- **040** — `uv` + hatchling package under `src/haxjobs/`; repo-root `haxjobs.toml` preserved
- **041** — FastAPI backend at `uv run haxjobs start` on `localhost:8241`
- **042** — Vite + React 19 + shadcn/ui frontend shell, Spotify theme, Lato body + Benne headings
- **044** — provider setup UI/API, credentials in `~/.haxjobs/haxjobs.toml`
- **039** — bare native `Agent.run()` wrapper + prompt registry
- **043** — full native agent harness: Pi-style registry/dispatch, job-search tools, prompt tiers, identity files

## Plan 043 deliverable

Files added/extended under `src/haxjobs/agent/`:

- `registry.py` — `ToolDef`, `register()`, `get_schemas()`, `dispatch()`
- `tools.py` — v1 tools only: `web_search`, `fetch_page`, read-only `db_query`
- `prompt.py` — stable → context → volatile `build_system_prompt()`
- `identity.py` — `~/.haxjobs/soul.md`, `memory.md`, `user.md` loaders with safe default identity
- `agent.py` — keeps `run()` unchanged; adds `run_with_tools(max_turns=5)`

Explicitly **not** added: Pi coding-agent tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`). HaxJobs remains a job-search automation harness, not a coding agent.

## Verification

Latest Plan 043 checks:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/test_agent_full.py tests/test_agent_minimal.py
# 22 passed

PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/
# 277 passed

PYTHONPATH=src:. .venv/bin/python -m py_compile src/haxjobs/agent/*.py tests/test_agent_full.py
# clean
```

## Next

**Plan 045** — Onboarding backend: CV upload, native-agent extraction, wizard API.

## Dirty working tree note

`src/haxjobs/cv_variants/backend_python/_test_output.pdf` is a pre-existing generated PDF modification and should not be included in code commits.
