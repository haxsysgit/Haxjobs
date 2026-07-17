# HaxJobs

HaxJobs is a career agent built for one job: help the user get interviews and become more employable.

The product is moving toward a CLI-first design. The CLI, current web app, and future cloud worker must call the same Python actions. There should be one implementation of discovery, evaluation, decisions, packs, and profile work.

## Current state

Working today:

- CV upload and deterministic profile extraction
- Agent-assisted onboarding questions
- Greenhouse, Ashby, and Lever discovery
- Job classification and fit evaluation
- Reusable role-specific CV variants
- Application pack generation
- Apply, maybe, save, skip, and reject decisions
- FastAPI endpoints and a React frontend
- A small native agent loop with 11 registered tools

Still missing:

- First-class CLI commands for the product actions
- Durable agent sessions, context assembly, and compaction
- Career graph and proper multi-track memory
- Employability roadmaps and learning progress
- A durable cloud worker for continuous monitoring
- Working outreach and learning actions

## Run locally

```bash
uv sync
uv run haxjobs start
```

The local app starts on `http://127.0.0.1:8241`.

The current CLI also exposes the agent playground:

```bash
uv run haxjobs agent ask "Show me what you can do"
uv run haxjobs agent ask --tools web_search,fetch_page "Find the careers page for Example Ltd"
```

These are playground commands, not the finished product CLI.

## Development

```bash
./dev start
./dev status
./dev test
```

Full verification:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests cron -name '*.py')
bash -n cron/run_pipeline.sh
cd frontend
npx tsc --noEmit
npm run lint -- --quiet
npm run build
```

## Docs

- [`docs/PRODUCT_ARCHITECTURE.md`](docs/PRODUCT_ARCHITECTURE.md): product direction
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): what the code does today
- [`docs/HAXJOBS_AGENT_HARNESS.md`](docs/HAXJOBS_AGENT_HARNESS.md): agent loop and tool boundary
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md): current storage model and known gaps
- [`docs/ROADMAP.md`](docs/ROADMAP.md): build order
- [`docs/harness-primitives/`](docs/harness-primitives/): plain-language agent-system notes

## Safety

HaxJobs does not submit applications, send outreach, or connect with people without explicit user approval. Generated claims must be backed by the user's profile evidence. Runtime data, credentials, databases, packs, reports, and generated CV files stay out of git.
