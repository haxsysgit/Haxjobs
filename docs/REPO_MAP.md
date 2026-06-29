# HaxJobs Repo Map

Last updated: 2026-06-28. Reflects post-cleanup state.

```
haxjobs-private-dev/
├── haxjobs.toml                 # Canonical config (paths, user profile, job search, agent, delivery)
├── haxjobs_config.py            # Thin TOML parser with env overrides
├── AGENTS.md                    # Agent guide — full pipeline vision
├── README.md                    # Project overview
│
├── cron/
│   └── run_pipeline.sh          # Pipeline entry point (discovery → classify → evaluate → report)
│
├── pipeline_db.py               # CLI: seed, classify-roles, status, discover-manual, etc.
├── api_server.py                # HTTP API server (jobs, packs, profile, outreach endpoints)
│
├── db/                          # SQLite layer
│   ├── schema.py                # Table definitions + migrations
│   ├── jobs.py                  # Job CRUD
│   ├── evaluations.py           # Evaluation save/read
│   ├── activity.py              # Activity logging
│   ├── pack_review.py           # Pack review operations
│   ├── role_classification.py   # Classify jobs by role family
│   ├── outreach.py              # Outreach draft operations
│   ├── decisions.py             # Decision recording
│   └── seed.py                  # DB seeding from files
│
├── evaluate/                    # Pluggable evaluation agents (future)
│   ├── common.py                # JSON extraction, validation, prompt building
│   ├── agents/
│   │   └── hermes.py            # Hermes CLI adapter
│   └── run.py                   # Agent selection + evaluation flow
│
├── evaluate_with_hermes.py      # Compatibility shim → evaluate/
│
├── packs_builder/
│   └── job_pack.py              # Template-fill pack generation
│
├── generate_ready_packs.py      # Pack generation trigger (L1/L2 auto, L3/L4 manual)
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
│   ├── arinze_profile.local.json
│   └── role_taxonomy.json       # Legacy — superseded by haxjobs.toml [[roles]]
│
├── state/                       # Runtime artifacts (gitignored)
│   ├── pipeline.db              # SQLite database
│   └── db_backups/              # DB backups
│
├── packs/                       # Generated pack directories (gitignored)
├── reports/                     # Generated cycle reports (gitignored)
├── intake/                      # Legacy intake JSON (gitignored, deprecated)
│
├── tests/                       # Test suite
│   └── test_*.py                # Per-module tests
│
├── plans/                       # Implementation plans
│   ├── README.md                # Plan index with execution order
│   ├── 001-014                  # DONE: cleanup wave
│   ├── 015-019                  # TODO: discovery → report pipeline
│   └── 020-022                  # TODO: docs cleanup, test cleanup, dead file sweep
│
├── docs/                        # Architecture and design docs
│   ├── PRODUCT_VISION.md        # Autonomous pipeline vision
│   ├── ARCHITECTURE.md          # Pipeline architecture diagram
│   ├── APPLICATION_WORKFLOW.md  # End-to-end workflow
│   ├── DATA_MODEL.md            # Database schema
│   ├── HAXJOBS_PRODUCT_SPEC.md  # Product specification
│   ├── HERMES_INTEGRATION.md    # Hermes as one evaluation agent
│   └── ...                      # Additional supporting docs
│
├── scripts/                     # Manual utility scripts
│   ├── check_dashboard.py       # Dashboard integrity checker
│   ├── cv_generate.py           # CV-FRAME pipeline orchestrator
│   └── cv_validator.py          # CV-FRAME validator
│
└── skills/                      # Hermes skill files
    └── fit_evaluator.md         # Fit evaluator prompt
```

## Deleted during cleanup (Stages 1-2)

- `discovery/` — 23 scraper/filter/company-list files (dead code, zero refs)
- `cron/email_intake.py` — dead email intake (zero refs)
- `cron/post_process.py` — dead post-processing (zero refs)
- `cron/sync_db_to_intake.py` — dead DB→intake sync (zero consumers)
- `post_process.py` — dead root script
