# Current Architecture

This file describes the code that exists today. Product direction lives in `PRODUCT_ARCHITECTURE.md`.

## Runtime

```text
CLI                   React frontend
 |                          |
 |                     FastAPI routes
 |                          |
 +---------- shared Python code ----------+
                    |                      |
             product actions          agent tools
                    |                      |
              SQLite, profile, discovery, evaluation, packs
```

The CLI and HTTP API are not at parity yet. Most product actions are available through Python and FastAPI, while the installed CLI exposes only server, agent-playground, and development commands.

## Main components

- `src/haxjobs/cli.py`: installed `haxjobs` command.
- `src/haxjobs/app.py`: FastAPI composition and built-frontend serving.
- `src/haxjobs/features/`: HTTP routes, schemas, and services.
- `src/haxjobs/product_tools.py`: shared discovery, evaluation, pack, and decision actions.
- `src/haxjobs/agent/`: model client, prompt assembly, tool registry, tool modes, and tool adapters.
- `src/haxjobs/discovery/`: Greenhouse, Ashby, and Lever discovery plus promotion.
- `src/haxjobs/evaluate/`: evaluation prompts, parsing, validation, and pipeline entry points.
- `src/haxjobs/packs_builder/`: pack generation using reusable CV variants.
- `src/haxjobs/db/`: SQLite schema and query helpers.
- `src/haxjobs/profile/`: profile schema and validation helpers.
- `frontend/`: current React 19 and Vite interface.
- `cron/run_pipeline.sh`: host-cron pipeline entry point.

## Product actions

`src/haxjobs/product_tools.py` implements:

- `discover_jobs`
- `evaluate_fit`
- `generate_pack`
- `record_decision`

Evaluation, decision, and pack services call these functions. Agent tools do too. Discovery still has a separate FastAPI service path in `src/haxjobs/features/discovery/service.py`; that duplication should be removed. New CLI commands should call the shared functions directly.

## Agent path

`Agent.run()` performs one model call.

`Agent.run_with_tools()` loops over model responses, dispatches allowed tools, appends tool results, and stops when the model returns text or the turn limit is reached.

The current loop has no durable session, retrieval layer, token tracking, compaction, resume state, child-agent dispatch, or tool stop signal.

## Data flow

```text
CV or pasted text
  -> deterministic extraction
  -> optional agent questions
  -> state/profile.json

ATS discovery
  -> discovered_jobs
  -> filters and promotion
  -> jobs
  -> evaluations
  -> optional pack
  -> decision
```

The profile is still a JSON document. Jobs and pipeline records live in SQLite.

## Automation

There are two current automation paths:

- `cron/run_pipeline.sh` runs a host-cron pipeline.
- The discovery API starts an in-process background thread and stores status in process memory.

Neither path is a durable queue or cloud worker. A process restart loses in-memory discovery status.

## Frontend boundary

FastAPI serves `frontend/dist` when it exists. The frontend calls same-origin `/api` endpoints.

The current web workspace is not a durable conversational agent session. Product work should not depend on that UI until the backend session model exists.

## Configuration

- Product config: repo-root `haxjobs.toml`
- Provider credentials: `~/.haxjobs/haxjobs.toml`
- Database: `state/haxjobs.db` by default
- Profile: `state/profile.json` by default
- Runtime path overrides: `HAXJOBS_HOME`, `HAXJOBS_DB`, `HAXJOBS_PROFILE`, and `HAXJOBS_CV_PROFILE`

## Known structural gaps

1. CLI lacks product-action commands.
2. Agent sessions and context management are not durable.
3. Profile storage is too flat for independent career tracks and evidence history.
4. Discovery filters accept roles and locations but do not enforce them in the product action.
5. Background run state is not durable or multi-process safe.
6. Outreach and learning actions do not exist.
7. Package runtime still depends on checkout-level config and frontend assets.
8. The HTTP app has no authentication layer and should remain loopback-only by default.
