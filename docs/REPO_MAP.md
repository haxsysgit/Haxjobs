# HaxJobs Repo Map

Last updated: 2026-06-30. Post-Wave-6 state.

HaxJobs is a self-hosted job search platform. See `PRODUCT_ARCHITECTURE.md` for the full vision and `AGENTS.md` for the agent guide.

```
haxjobs-private-dev/
├── haxjobs.toml                 # Canonical config (paths, user, job_search, roles, evaluation, delivery, discovery, cron)
├── haxjobs_config.py            # Thin TOML parser with env overrides
├── AGENTS.md                    # Agent guide — full pipeline vision
├── README.md                    # Project overview
│
├── cron/
│   ├── run_pipeline.sh          # Pipeline entry point (discovery → classify → evaluate → report)
│   └── generate_cycle_report.py # Cycle report generator (markdown digest)
│
├── pipeline_db.py               # CLI: seed, classify-roles, status, discover-manual, discover-run, scrape-greenhouse
├── api_server.py                # HTTP API server (jobs, packs, profile, outreach endpoints)
│
├── db/                          # SQLite layer
│   ├── schema.py                # Table definitions + migrations
│   ├── jobs.py                  # Job CRUD
│   ├── discovered_jobs.py       # Pre-promotion discovered job CRUD (dedup, promote)
│   ├── evaluations.py           # Evaluation save/read (agent, score, level, pack, report)
│   ├── activity.py              # Activity logging
│   ├── pack_review.py           # Pack review operations
│   ├── role_classification.py   # Classify jobs by role family
│   ├── outreach.py              # Outreach draft operations
│   ├── decisions.py             # Decision recording
│   └── seed.py                  # DB seeding from files
│
├── discovery/                   # Job discovery ingestion spine
│   ├── normalize.py             # Field mapping (scraper → CANONICAL_KEYS)
│   ├── hooks.py                 # Blacklist, non-tech filter, location preference filter
│   ├── profile_search.py        # Profile-aware pre-scrape filtering
│   └── scrapers/
│       ├── greenhouse.py        # Greenhouse ATS scraper
│       ├── ashby.py             # Ashby ATS scraper
│       ├── lever.py             # Lever ATS scraper
│       └── orchestrator.py      # Run all scrapers, summarize results
│
├── evaluate/                    # Pluggable evaluation agents
│   ├── common.py                # JSON extraction, validation, prompt building
│   ├── chain.py                 # Config-driven agent fallback chain
│   ├── run.py                   # Agent selection + evaluation flow + auto-pack
│   ├── cv_review.py             # Per-job CV review generation
│   └── agents/
│       ├── base.py              # BaseAdapter interface
│       ├── codex.py             # Codex CLI adapter (--output-schema)
│       ├── hermes.py            # Hermes CLI adapter
│       ├── pi.py                # Pi headless adapter
│       ├── claude_code.py       # Claude Code adapter (session-native only)
│       └── gemini.py            # Gemini adapter (stub — tier blocked)
│
├── packs_builder/
│   └── job_pack.py              # Template-fill pack generation
│
├── generate_ready_packs.py      # Standalone pack generation (level-aware via AUTO_PACK_LEVELS)
│
├── server/
│   └── routes/
│       ├── jobs.py              # /api/jobs endpoints
│       ├── outreach.py          # /api/outreach endpoints
│       ├── resources.py         # /api/discovery, /api/profile, etc.
│       └── pack_resources.py    # /api/packs endpoints
│
├── dashboard/                   # React + TypeScript + Vite
│   ├── src/
│   │   ├── data/api.ts          # API client
│   │   ├── Dashboard.tsx        # Main dashboard
│   │   ├── JobDetail.tsx        # Job detail view
│   │   ├── Outreach.tsx         # Outreach management
│   │   ├── Profile.tsx          # Profile view
│   │   └── Queue.tsx            # Job queue
│   └── ...
│
├── cv_variants/                 # 7 reusable CV variants
│   ├── registry.json            # Variant registry
│   ├── registry.py              # Registry helpers
│   ├── backend_python/          # CV variant per role
│   ├── ai_engineer_llm/
│   ├── fullstack_python_react/
│   ├── ai_automation_agents/
│   ├── junior_software/
│   ├── data_python/
│   └── platform_backend/
│
├── application_templates/       # Role pack templates with fillable slots
│   ├── cover_letters/           # Cover letter templates per role
│   ├── cv_variant_briefs/       # CV variant descriptions per role
│   ├── pack_templates/          # Full pack templates per role
│   └── COVER_LETTER_GOVERNANCE.md
│
├── profile/                     # User profile data
│   └── arinze_profile.local.json
│
├── state/                       # Runtime artifacts (gitignored)
│   ├── haxjobs.db               # SQLite database
│   └── db_backups/              # DB backups
│
├── packs/                       # Generated pack directories (gitignored)
├── reports/                     # Generated cycle reports (gitignored)
│
├── tests/                       # Test suite
│   ├── conftest.py              # Shared test_db fixture
│   └── test_*.py                # 18 per-module test files
│
├── plans/                       # Implementation plans
│   ├── README.md                # Plan index with execution order
│   ├── 001-029                  # DONE: pipeline foundation + multi-agent research
│   └── 030-034                  # IN PROGRESS: docs alignment for product pivot
│
├── docs/                        # Architecture and product docs
│   ├── PRODUCT_ARCHITECTURE.md  # Canonical product architecture (NEW)
│   ├── ARCHITECTURE.md          # Technical architecture
│   ├── DATA_MODEL.md            # Database schema
│   ├── HAXJOBS_PRODUCT_SPEC.md  # Original 2026-06-11 product spec (historical)
│   ├── ROADMAP.md               # Current roadmap
│   └── REPO_MAP.md              # This file
│
└── scripts/                     # Manual utility scripts (not pipeline code)
    ├── archilles-webui          # Archilles VPS web UI management
    ├── dash-tunnel              # SSH tunnel for dashboard access
    ├── debug_job_pipeline.py    # Debug tool for pipeline stage inspection
    ├── generate-pack            # Manual pack generation helper
    ├── haxjobs-update           # Archilles VPS update script
    ├── pull-cv-variants         # Pull CV variant files
    ├── render-cv-variant        # Render a CV variant to PDF
    ├── review-pack              # Review a generated pack
    ├── seed-cv-variants-from-packs  # Seed CV variants from existing packs
    └── update-archilles-private # Update Archilles private repo
```

## Deleted files

- `discovery/` (23 scraper/filter files) — cleanup wave 1, replaced by `discovery/normalize.py`, `hooks.py`, `scrapers/`
- `cv_generate.py`, `cv_validator.py`, `pack_builder.sh` — Plan 025, superseded by `packs_builder/job_pack.py`
- `build-dash.sh`, `dev-watch.sh` — Plan 025, Vite handles both natively
- `evaluate_with_hermes.py` — Plan 017, replaced by `evaluate/agents/hermes.py` and `evaluate/chain.py`
- `profile/role_taxonomy.json` — Plan 025, superseded by `haxjobs.toml` `[[roles]]`
- `intake/` — deprecated legacy JSON intake
- `docs/PRODUCT_VISION.md`, `APPLICATION_WORKFLOW.md`, `HERMES_DIRECTION_BRIEF.md`, `HERMES_INTEGRATION.md`, `PRIVATE_ARCHILLES_UPDATE.md`, `PRIVATE_WORKFLOW_MAP.md`, `PROFILE_DATA_SETUP.md` — Plan 030, superseded by `PRODUCT_ARCHITECTURE.md`
