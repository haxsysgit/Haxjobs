# HaxJobs Architecture

HaxJobs is an autonomous pipeline, not a web-app workspace. Jobs flow through five stages. The dashboard and API are secondary — the primary interface is the cycle report.

## Pipeline architecture

```
                             ┌─────────────────┐
                             │   haxjobs.toml   │
                             │  (user profile,  │
                             │   job prefs,     │
                             │   agent config,  │
                             │   delivery)      │
                             └────────┬────────┘
                                      │ drives everything
                                      ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ DISCOVERY│───▶│CLASSIFICATION│───▶│  EVALUATION  │───▶│ PACK GENERATION│───▶│  REPORT  │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
     │                 │                   │                   │                  │
     ▼                 ▼                   ▼                   ▼                  ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│discovered │    │    jobs      │    │ evaluations  │    │   packs/     │    │ reports/ │
│  _jobs    │    │  (accepted)  │    │ (fit data)   │    │ (templates   │    │ (markdown│
│  (raw)    │    │              │    │              │    │  filled)     │    │  digest) │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
```

### Stage 1: Discovery

Automatic scrapers find jobs. Pre-discovery hooks run:
- Dedup: check source_url against existing jobs
- Blacklist: check company against configured blacklist
- Filter: leniently remove non-tech or profile-irrelevant roles

Accepted jobs promote from `discovered_jobs` to `jobs` table. Manual submissions (paste JD link) go through the same normalization and hooks.

### Stage 2: Classification

Profile-driven from `haxjobs.toml` `[[roles]]` config. Each configured role has keywords, cv_variant, priority. The classifier matches job title/JD against configured roles. Output: role_family, cv_variant, confidence. No hardcoded taxonomy.

### Stage 3: Evaluation

Pluggable agent system (`evaluate/` package). Agent choice from `haxjobs.toml` `[evaluation].agent`. Each agent adapter implements: `call_agent(prompt, timeout_seconds) -> str`. Results written to `evaluations` table with agent name, fit score (0-100), level (1-4), gaps, summary.

Levels:
- L1 (75+): Standard — auto-pack
- L2 (50-74): Quick Apply — auto-pack
- L3 (30-49): Lite — report only, no pack
- L4 (<30): Skip — report only

### Stage 4: Pack Generation

Pre-built role templates live in `application_templates/`. Seven roles, each with cover letter template and pack template. Slots: `{company}`, `{hiring_manager_or_team}`, `{role_title}`, `{jd_match_points}`, `{company_reason}`, `{evidence_story}`, `{gap_note}`.

L1/L2: auto-fill template slots → regenerate PDF/cover letter from HTML.
L3/L4: no pack generation. Appear in cycle report for manual review.

### Stage 5: Report

End-of-cycle markdown report: all evaluated jobs with links, scores, levels, pack paths, fit summaries. Saved to DB (`evaluations.report_markdown`). Delivered via configured channels (email, Telegram).

## DB layout

Single SQLite database (`state/haxjobs.db`):

```
discovered_jobs     — raw scraped/manual jobs before hooks
jobs                — accepted jobs promoted from discovery
evaluations         — fit evaluation results (agent, score, level, report, pack path)
favorites           — user-starred jobs
saved_jobs          — user-saved jobs
decisions           — approval/rejection decisions
outreach_drafts     — generated outreach messages
activity_log        — pipeline event log
evaluation_history  — historical scores on re-evaluation
profile_snapshots   — profile state at evaluation time
whitelist           — company/role whitelist entries
```

## Config architecture

`haxjobs.toml` is the canonical config. `haxjobs_config.py` parses it with `tomllib` and applies env var overrides. Every script imports config — no hardcoded paths or agent names.

Sections: `[paths]`, `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`, `[email]`, `[telegram]`.

## Directory map

```
haxjobs-private-dev/
├── haxjobs.toml              ← canonical config
├── haxjobs_config.py         ← thin parser
├── AGENTS.md                 ← agent guide (this vision)
├── cron/run_pipeline.sh      ← pipeline entry point
├── pipeline_db.py            ← CLI: seed, classify, status
├── db/                       ← SQLite layer (schema, jobs, evaluations, etc.)
├── evaluate/                 ← evaluation agents (common + agent adapters)
├── packs_builder/            ← pack generation (template fill)
├── reports/                  ← cycle report generation
├── server/                   ← API server + routes
├── dashboard/                ← React + TypeScript dashboard
├── cv_variants/              ← 7 reusable CV variants
├── application_templates/    ← role templates with fillable slots
├── profile/                  ← user profile data
├── state/                    ← runtime artifacts (DB, logs)
├── packs/                    ← generated pack directories
├── reports/                  ← generated cycle reports
├── tests/                    ← test suite
└── plans/                    ← implementation plans
```

## Future: 3-Agent Simulation Loop (v0.3)

After pack generation, an optional coaching simulation stress-tests the pack:

```
RECRUITER (asks questions) → APPLICANT (answers from profile) → EVALUATOR (judges improvement)
```

Stops when: shortlisted, rejected with unfixable gaps, no material gain, or max 3 rounds.
Output: `packs/<job>/simulation.json`.
