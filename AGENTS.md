# HaxJobs — Agent Guide

HaxJobs is Arinze's autonomous job discovery and application pipeline. Agents working in this repo must understand the pipeline design and respect its boundaries.

## What HaxJobs does

HaxJobs is a black-box pipeline: jobs enter from discovery scrapers, everything else is automatic until the final report. The user reviews the output — not each step.

### Pipeline stages

```
DISCOVERY → CLASSIFICATION → EVALUATION → PACK GENERATION → REPORT
```

1. **Discovery** — automatic scrapers find jobs. Jobs are normalized, run through pre-discovery hooks (dedup against DB, blacklist companies, duplicate role check), then stored in `discovered_jobs` table. Post-discovery filters leniently remove non-tech or profile-irrelevant jobs. Manual job submissions (paste link/JD) go through the same path.

2. **Classification** — profile-driven from `haxjobs.toml`. Role preferences, work modes, target levels, blacklisted keywords all live in config. No hardcoded role taxonomy.

3. **Evaluation** — pluggable agent system (`evaluate/` directory). Agent choice configured in `haxjobs.toml` (`evaluation.agent`). Results written to `evaluations` table with agent name, fit score, level, gaps.

4. **Pack Generation** — pre-built role templates exist (7 roles for Arinze). L1/L2 jobs auto-fill templates: slots like `{company}`, `{hiring_manager}`, `{jd_match_points}`, `{evidence_story}`, `{gap_note}`. Regenerate PDF/cover letter from filled HTML. L3/L4 jobs appear in the report for manual review — no auto-pack.

5. **Report** — end-of-cycle markdown report of ALL evaluated jobs: links, pack paths, fit analysis, level breakdown. Saved to DB and delivered via configured channels (email, messaging).

### Future: 3-Agent Simulation Loop (v0.3)

After the pipeline produces a pack, a coaching simulation stress-tests it:

- **Recruiter Agent** — plays the hiring manager. Asks questions, raises objections.
- **Applicant Agent** — answers as Arinze on a good day, using only profile evidence.
- **Evaluator Agent** — referee. Checks if the application improved. Separates safe edits from fabrication.

Stops when: shortlisted, rejected with unfixable gaps, no material gain, or max 3 rounds.

Output: `packs/<job>/simulation.json`. This is coaching, not real hiring feedback.

## Repo layout

| Environment | Path | Role |
|---|---|---|
| Jade (local dev) | `/home/hax/haxjobs-private-dev` | Coding, testing, planning |
| Archilles (live VPS) | `/home/hermes/haxjobs` | Cron, API, dashboard, Telegram |
| GitHub | `ha.../Haxjobs-Private` | Source of truth |

Workflow: develop on Jade → push to GitHub → Archilles pulls via update script.

## Config

`haxjobs.toml` is the canonical config. `haxjobs_config.py` is a thin parser. Env vars override TOML values.

Sections: `[paths]`, `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`, `[email]`, `[telegram]`.

## DB layout

- `discovered_jobs` — raw scraped/manual jobs before hooks
- `jobs` — accepted jobs promoted from discovery
- `evaluations` — fit evaluation results per job (agent, score, level, report markdown, pack path)
- `favorites`, `saved_jobs` — user curation
- `decisions` — approval/rejection/skip decisions
- `outreach_drafts` — generated outreach messages
- `activity_log` — pipeline events
- `evaluation_history` — historical scores on re-evaluation

## Verification commands

Run these from the repo root before claiming changes are safe:

```bash
python3 -m pytest -q
python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
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

- **SQLite** (`state/haxjobs.db`) is the source of truth for jobs, evaluations, packs, and outreach.
- **`haxjobs.toml`** drives classification, evaluation agent choice, and level-based auto-pack decisions.
- **Reusable CV variants** live in `cv_variants/`. Seven role variants exist. Packs reference a variant via metadata — never generate a new CV per job.
- **Pack templates** live in `application_templates/`. Each role has a template with fillable slots. L1/L2 auto-fill; L3/L4 are report-only.
- **Cycle reports** are generated at the end of each pipeline run: markdown with links, pack paths, fit analysis.
- **Outreach drafts** are template-generated and require approval before any send action.

## The 3-Agent Simulation Loop (v0.3, future)

Designed but not yet implemented. The loop stress-tests an application pack:

1. **Recruiter Agent** — reads the JD, CV variant, and pack. Outputs: shortlist/reject/continue/needs_clarification. Gives concrete objections.
2. **Applicant Agent** — answers using only profile/CV/pack evidence. Flags claims needing human verification. Suggests edits without writing permanently.
3. **Evaluator Agent** — judges: did the applicant improve? Separates safe edits (evidence-backed) from unsafe (fabrication). Decides: improve/stop_shortlisted/stop_rejected/stop_no_material_gain.

One round: recruiter → applicant → evaluator → repeat or stop. Max 3 rounds. Output: `packs/<job>/simulation.json`.

## Coding style

- Readable Python and TypeScript. No cryptic one-liners.
- `ponytail:` comments mark deliberate simplifications with the upgrade path.
- Tests use temporary SQLite DB monkeypatches.
- Match existing naming: `list_jobs()`, `insert_job()`, camelCase for API fields.
- Python stdlib HTTP server. React + TypeScript + Vite dashboard.
- Config is TOML first: never hardcode paths, agent names, or profile preferences.
