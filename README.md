# HaxJobs

A career agent platform. One job: get the user interviews and make them more employable.

Stage 0 is built. The greenfield runtime has four layers (model → agent_core → employment → interfaces), 27 tests, and one CLI command. Everything else rebuilds from scratch.

## Current state

```
src/haxjobs/
├── model/          provider boundary (OpenAI adapter, fake client)
├── agent_core/     domain-free runtime (events, artifacts, one-call loop)
├── employment/     Hax identity, truth rules, fixtures, context assembly
├── interfaces/     experiment CLI
├── config.py       paths from haxjobs.toml
└── cv_variants/    user CV variant templates (data, not code)
```

## Quick start

```bash
uv sync
uv run haxjobs experiment review-job --job 49 --fake --career-fixture tests/fixtures/job_review/career.json
uv run haxjobs experiment review-job --job 49 --live
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
