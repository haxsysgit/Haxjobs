# HaxJobs Architecture

HaxJobs is a self-hosted job search platform, not a five-stage pipeline. It runs as a web app at `localhost:8241` with a Python backend, React frontend, and SQLite database. The canonical product vision is in `PRODUCT_ARCHITECTURE.md`.

## Component architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI (React)                         │
│  Dashboard │ Jobs │ Discovery │ Packs │ Outreach │ Profile│
│  Settings  │ Pipeline │ Activity │ Onboarding Wizard     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP REST API
┌────────────────────┴────────────────────────────────────┐
│                 Python API Server                         │
│  /api/profile  /api/jobs  /api/evaluations  /api/packs   │
│  /api/discovery  /api/outreach  /api/decisions           │
│  /api/onboarding (CV upload, profile extraction, wizard) │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                   Pipeline Engine                         │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Discovery │→│Classify  │→│Evaluate  │→│Pack Gen  │ │
│  │(scrapers │  │(config-  │  │(LLM API) │  │(template │ │
│  │ +web)    │  │ driven)  │  │          │  │ fill)    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │Outreach  │  │Learning  │  │Report    │               │
│  │Engine    │  │Engine    │  │Generator │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                   SQLite Database                         │
│  profile │ jobs │ evaluations │ decisions │ outreach     │
│  discovered_jobs │ activity_log │ cycle_state           │
│  job_history │ learning_patterns                        │
└─────────────────────────────────────────────────────────┘
```

## Key design decisions

### 1. Direct LLM API for evaluation, not agent subprocess

Evaluation is a text-in → JSON-out task. Direct API calls (`openai.chat.completions.create()` with `response_format: {type: "json_schema"}`) are faster, cheaper, and more reliable than spawning agent CLIs as subprocesses. Agent adapters stay for interactive use only (the Pi skill, where the agent's own reasoning adds value). For headless cron: direct API.

### 2. Profile is the backbone — and it evolves

The profile JSON (`profile/arinze_profile.local.json`) drives every pipeline stage. It's built during onboarding from CV extraction + targeted questions. It continuously evolves as the learning engine processes user decisions — not static, not hand-maintained.

### 3. Three data tiers for jobs

- `discovered_jobs` — raw scraped, pre-filtering. Temporary.
- `jobs` — promoted, classified, evaluated. Active.
- `job_history` — applied, interviewed, rejected, archived. Permanent record.

### 4. Cycle-based operation

Each pipeline run is a "cycle" (e.g., biweekly). Cycle ID groups all jobs/evaluations/packs from that run. Between cycles: DB cleanup, learning engine processes user decisions. Cycle report shows what's new plus what changed since last time.

### 5. Self-contained, local-first

Ships as a single installable package. Web UI on localhost. SQLite — no Postgres/MySQL. LLM API keys are the only external dependency (user brings their own).

## User journey

```
ONBOARD → DISCOVER → REVIEW → APPLY → LEARN → REPEAT
```

See `PRODUCT_ARCHITECTURE.md` for the full phase-by-phase breakdown.

## Config architecture

`haxjobs.toml` is the canonical config. `haxjobs_config.py` parses it with `tomllib` and applies env var overrides. Every script imports config — no hardcoded paths or agent names.

Sections: `[paths]`, `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`, `[cron]`, `[email]`, `[telegram]`.

## Directory map

```
haxjobs-private-dev/
├── haxjobs.toml              ← canonical config
├── haxjobs_config.py         ← thin parser
├── AGENTS.md                 ← agent guide
├── README.md                 ← project overview
├── pipeline_db.py            ← CLI entry point (18 commands)
├── api_server.py             ← stdlib HTTP API server
├── db/                       ← SQLite layer (schema, jobs, evaluations, etc.)
├── evaluate/                 ← evaluation logic
│   ├── common.py             ← prompt building, JSON parsing, validation
│   ├── chain.py              ← config-driven agent fallback chain
│   ├── run.py                ← evaluate_from_db, batch CLI
│   ├── cv_review.py          ← per-job CV review generation
│   └── agents/               ← agent adapter implementations
├── discovery/                ← job sourcing
│   ├── scrapers/             ← greenhouse.py, ashby.py, lever.py
│   ├── hooks.py              ← post-discovery filtering
│   ├── profile_search.py     ← pre-scrape filtering
│   └── normalize.py          ← canonical job format
├── packs_builder/            ← pack generation
├── application_templates/    ← 7 role-specific pack templates
├── cv_variants/              ← 7 reusable CV variants (HTML + PDF)
├── cron/                     ← scheduling (run_pipeline.sh)
├── dashboard/                ← React + TypeScript + Vite web UI
├── server/                   ← API route handlers
├── profile/                  ← user profile JSON (backbone)
├── reports/                  ← generated cycle reports
├── packs/                    ← generated application packs
├── tests/                    ← test suite
├── plans/                    ← implementation plans
└── docs/                     ← architecture and product docs
```

## Data model

See `DATA_MODEL.md` for the full schema. Key points:

- **Three tiers**: discovered_jobs → jobs → job_history
- **Feedback loop**: decisions table drives learning engine → profile evolution
- **Cycle tracking**: cycle_state table groups work by run
- **Deprecated**: favorites, saved_jobs, evaluation_history (replaced by decisions + cycle_id)
