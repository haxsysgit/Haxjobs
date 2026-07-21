# HaxJobs

A career agent platform. One job: get the user interviews and make them more employable.

Plan 004 is built. The greenfield runtime has four layers (model → agent_core → employment → interfaces), conversational chat with durable tool effects, typed job assessments, and 216 tests.

## Current state

```
src/haxjobs/
├── model/          provider boundary (OpenAI adapter, fake client)
├── agent_core/     domain-free runtime (messages, tools, turn, session)
├── employment/     Hax identity, career graph, job actions, tools
├── interfaces/     chat CLI, profile management CLI
├── config.py       paths from haxjobs.toml
└── cv_variants/    user CV variant templates (data, not code)
```

## Quick start

```bash
# Migrate career graph (requires private fixture or use synthetic test fixture)
uv run -- haxjobs profile migrate --fixture tests/fixtures/job_review/career.json

# Import job fixtures
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions import discussion/fixtures/harness/job-49.json

# Start a conversation (fake, no network)
uv run -- haxjobs chat --new --fake

# Resume latest session
uv run -- haxjobs chat
```

## Docs

- [`docs/PRODUCT.md`](docs/PRODUCT.md) — what HaxJobs is, Hax persona, product direction
- [`docs/HAXJOBS.md`](docs/HAXJOBS.md) — technical reality, architecture, limitations
- [`discussion/`](discussion/) — architecture decisions and research
- [`docs/harness-primitives/`](docs/harness-primitives/) — agent harness teaching vault

## Verification

```bash
uv lock --check
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
```
