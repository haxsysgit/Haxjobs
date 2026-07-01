# HaxJobs — Agent Guide

HaxJobs is Arinze's self-hosted job search platform. It builds a structured profile from a CV upload, discovers jobs, evaluates fit, generates application packs, learns from user decisions, and helps with outreach — all through a web UI at `localhost:8241` with automation under the hood.

Agents working in this repo must understand the full user journey, not just the pipeline.

## What HaxJobs does

HaxJobs is a platform with six phases:

```
ONBOARD → DISCOVER → CLASSIFY → EVALUATE → DECIDE → LEARN
```

**0. Onboarding** (one-time) — user uploads CV, LLM extracts structured profile, targeted questions fill gaps. Output: `profile/arinze_profile.local.json` — the backbone of everything. No hand-writing JSON.

**1. Discovery** — web search + ATS scrapers (Greenhouse, Ashby, Lever) find jobs matching the profile. Profile-aware pre-filtering at scraper level. Jobs normalized and stored in `discovered_jobs`, promoted to `jobs` after hooks (dedup, blacklist, location filter).

**2. Classification** — profile-driven from `haxjobs.toml` `[[roles]]`. Role preferences, work modes, target levels, blacklisted keywords all live in config. No hardcoded role taxonomy.

**3. Evaluation** — direct LLM API calls (not agent subprocess) score fit 0-100 against the full profile. Returns fit_score, level (1-4), matches, gaps, sponsorship risk. Results written to `evaluations` table.

**4. Decision loop** — user reviews jobs in the dashboard, marks each as apply/skip/reject. `decisions` table records every action. Applied jobs are excluded from future discovery cycles.

**5. Learning** — system processes decisions to evolve profile preferences. Preferred companies pattern, salary trends, role refinements. Profile gets sharper over time.

**Outreach** — find hiring managers/team leads via LinkedIn and company pages. Generate personalized messages from templates. Track status: drafted → sent → replied → interview. All requiring user approval before sending.

### Pack generation

L1/L2 jobs (score 50+) auto-generate packs: role-specific CV review, cover letter from templates, per-job keyword injection. L3/L4 jobs appear in reports for manual review. CV variants live in `cv_variants/` — 7 reusable role-specific variants, never generate a new CV per job.

### Cycle reports

End-of-cycle markdown report of all evaluated jobs: links, scores, levels, pack paths, user decisions. Saved to `reports/<cycle>.md` and delivered via configured channels.

## Repo layout

| Environment | Path | Role |
|---|---|---|
| Jade (local dev) | `/home/hax/haxjobs-private-dev` | Coding, testing, planning |
| Archilles (live VPS) | `/home/hermes/haxjobs` | Cron, API, dashboard, Telegram |
| GitHub | `ha.../Haxjobs-Private` | Source of truth |

Workflow: develop on Jade → push to GitHub → Archilles pulls via update script.

## Config

`haxjobs.toml` is the canonical config. `haxjobs_config.py` is a thin parser. Env vars override TOML values.

Sections: `[paths]`, `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`, `[cron]`, `[email]`, `[telegram]`.

## DB layout

- `discovered_jobs` — raw scraped/manual jobs before hooks
- `jobs` — accepted jobs promoted from discovery
- `evaluations` — fit evaluation results per job (agent, score, level, report, pack path, cycle_id)
- `decisions` — apply/skip/reject decisions per job (user feedback loop)
- `outreach_drafts`, `outreach_contacts` — outreach messages and contact tracking
- `activity_log` — pipeline events
- `whitelist` — company/role patterns that prevent auto-skip

**Future** (per `PRODUCT_ARCHITECTURE.md`):
- `cycle_state` — track each pipeline run cycle
- `job_history` — permanent archive of applied/rejected/archived jobs
- `learning_patterns` — learned preferences from user decisions

## Verification commands

Run these from the repo root before claiming changes are safe:

```bash
PYTHONPATH=. python3 -m pytest -q tests/
PYTHONPATH=. python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh
cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build
```

## Read/write boundaries

**Never commit:**
- `intake/`, `packs/`, `state/`, `reports/`, `outreach/` (runtime dirs)
- SQLite databases (`.db`)
- `.env` files
- LinkedIn cookies or browser profiles
- Generated CV PDFs/HTML (under `cv_variants/*/`)
- `node_modules/`, `dist/`, Vite build artifacts

**Read but don't modify:**
- Live runtime data on Archilles (`/home/hermes/haxjobs/state/haxjobs.db`)
- Archilles crontab (use `crontab -l` read-only)

## Safety rules

- **Do not** submit applications, connect on LinkedIn, or send outreach messages. These require Arinze's explicit approval.
- **Do not** send Telegram messages except through the approved delivery channel configured in `haxjobs.toml`.
- **Do not** generate per-job CVs. Use the reusable CV variant system (7 variants, template-fill approach).
- **L1/L2 evaluation levels**: pack generation is automatic (template fill from role templates). **L3/L4**: manual review only.
- **Do not** bind the API server to `0.0.0.0` without explicit configuration (`HAXJOBS_API_HOST`).
- **Do not** read or print `.env` values, tokens, or passwords.
- **Do not** set the `HAXJOBS_API_TOKEN` env var unless you intend to enable token auth.

## Product rules

- **Profile JSON** (`profile/arinze_profile.local.json`) is the backbone — built by onboarding wizard, drives all pipeline stages
- **Direct LLM API** for headless evaluation — faster and more reliable than agent subprocess
- **SQLite** (`state/haxjobs.db`) is the source of truth for jobs, evaluations, packs, decisions, and outreach
- **`haxjobs.toml`** drives classification, evaluation config, and level-based auto-pack decisions
- **Decisions drive the feedback loop** — every apply/skip/reject teaches the system
- **Reusable CV variants** live in `cv_variants/`. Seven role variants exist. Packs reference a variant via metadata — never generate a new CV per job
- **Pack templates** live in `application_templates/`. Each role has a template with fillable slots. L1/L2 auto-fill; L3/L4 are report-only
- **Cycle reports** are generated at the end of each pipeline run: markdown with links, pack paths, fit analysis
- **Outreach drafts** are template-generated and require approval before any send action

## Coding style

- Readable Python and TypeScript. No cryptic one-liners.
- `ponytail:` comments mark deliberate simplifications with the upgrade path.
- Tests use temporary SQLite DB monkeypatches via `tests/conftest.py`.
- Match existing naming: `list_jobs()`, `insert_job()`, camelCase for API fields.
- Python stdlib HTTP server. React + TypeScript + Vite dashboard.
- Config is TOML first: never hardcode paths, agent names, or profile preferences.
