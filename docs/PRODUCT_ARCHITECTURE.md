# HaxJobs Product Architecture

## What HaxJobs Is

HaxJobs is a **self-hosted job search platform**. It's a single application you run on your machine that:

1. Builds a deep structured profile of you (from CV upload + guided questions)
2. Continuously discovers jobs matching that profile across the web
3. Evaluates every job against your full profile using LLMs
4. Generates application packs (CV + cover letter) for good fits
5. Learns from your decisions — gets smarter the more you use it
6. Helps you network with hiring managers and track outreach

It ships as a **web app** (Python backend + React frontend + SQLite) that runs locally at `localhost:8241`. No cloud, no accounts, no vendor lock-in. Your data lives on your machine.

---

## User Journey

```
ONBOARD → DISCOVER → REVIEW → APPLY → LEARN → REPEAT
```

### Phase 1: Onboarding (one-time, ~10 minutes)

```
User opens http://localhost:8241
  ├─ Uploads CV (PDF/DOCX/HTML) — or multiple CVs
  │   └─ LLM extracts: name, skills, experience, education, projects, work auth
  ├─ Fills gaps with targeted questions (LLM-driven, minimal)
  │   └─ "We see you worked at Vigilis. What was your title?"
  │   └─ "Any roles you'd never accept? (e.g. frontend-only, DevOps)"
  │   └─ "Salary range?"
  ├─ Result: profile.json — the backbone of everything
  │   └─ Confirmed facts with safe_wording rules
  │   └─ Skills list with proficiency levels
  │   └─ Role preferences, location preferences, work mode preferences
  │   └─ Explicit exclusions (companies, keywords, levels)
  │   └─ Guardrails for evaluation (what the system should penalize/reward)
  └─ Onboarding complete. System is ready to discover jobs.
```

### Phase 2: Discovery (continuous)

```
System wakes up on schedule (configurable, e.g. every 2 weeks)
  ├─ Web search for jobs matching profile
  │   └─ Search queries derived from role preferences + locations
  │   └─ Results normalized into discovered_jobs table
  ├─ API scrapers for configured ATS boards
  │   └─ Greenhouse, Ashby, Lever, Workday
  ├─ Pre-filtering at scraper level (title + location match profile)
  ├─ Post-discovery hooks (blacklist, duplicate check, already-applied check)
  └─ Promoted to jobs table
```

### Phase 3: Classification & Evaluation (automatic)

```
Each new job:
  ├─ Classified into role family (config-driven from profile)
  ├─ Evaluated by LLM against full profile
  │   └─ Direct API call (not subprocess agent wrapper)
  │   └─ Returns: fit_score, level, matches, gaps, sponsorship risk
  └─ L1/L2 jobs → auto-pack generated
      └─ Per-job CV review (JD keywords injected, relevant experience highlighted)
      └─ Cover letter from role template
      └─ Pack saved to packs/<cycle>/<job_slug>/
```

### Phase 4: User Review (the decision loop)

```
User opens dashboard → sees new cycle report
  ├─ Jobs sorted by fit score
  ├─ Each job shows: score, level, strengths, gaps, pack link
  ├─ User decides:
  │   ├─ APPLY — "I want this one"
  │   │   └─ System tracks: applied at <date>
  │   │   └─ Next cycle: this job/company is remembered
  │   ├─ SKIP — "Good fit but not right now"
  │   │   └─ System notes: why was it skipped?
  │   │   └─ Pattern learning: does user skip certain companies/roles?
  │   └─ REJECT — "This is wrong for me"
  │       └─ System notes: what was wrong?
  │       └─ This company/role/keyword gets deprioritized
  └─ System learns: profile preferences tighten over time
```

### Phase 5: Outreach (semi-automatic)

```
For APPLY jobs:
  ├─ Find hiring manager / team lead
  │   └─ Company LinkedIn page → employees → filter by title
  │   └─ Company website → team page / about
  ├─ Generate personalized outreach message
  │   └─ Template filled with job-specific details
  │   └─ References specific profile facts that match the role
  ├─ User reviews and approves message
  └─ Track outreach status (drafted → sent → replied → interview)
```

### Phase 6: Learning (the feedback loop)

```
Every cycle improves the system:
  ├─ Applied jobs → marked in DB, excluded from future discovery
  ├─ Rejected patterns → deprioritized (companies, keywords, role types)
  ├─ Successful patterns → prioritized (companies that responded, role types that fit)
  ├─ Profile evolves:
  │   └─ Salary expectations adjust based on offered ranges
  │   └─ Preferred locations expand/contract based on market
  │   └─ Role preferences sharpen based on what gets interviews
  └─ DB cleanup between cycles:
      └─ Remove duplicate jobs (same URL, same company+title)
      └─ Archive jobs older than N cycles with no user action
      └─ Preserve applied/replied/interviewed jobs permanently
```

---

## Architecture

### Components

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
│  │          │  │          │  │(LLM API) │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │Outreach  │  │Learning  │  │Report    │               │
│  │          │  │Engine    │  │Generator │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                   SQLite Database                         │
│  profile │ jobs │ evaluations │ decisions │ outreach     │
│  discovered_jobs │ activity_log │ learning │ cycle_state │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. Direct LLM API for evaluation, not agent subprocess**
- Evaluation is a text-in → JSON-out task. Direct API calls are faster, cheaper, more reliable.
- Keep agent adapters for **interactive** use only (the Pi skill, where the agent's own reasoning adds value).
- For headless cron: `openai.chat.completions.create()` with `response_format: {type: "json_schema"}`.

**2. Profile is the backbone — and it evolves**
- Starts from CV extraction during onboarding.
- Refined by user answers to targeted questions.
- Continuously updated by the learning engine based on user decisions.
- Every pipeline stage reads from profile. The learning engine writes to it.

**3. Three data tiers for jobs**
- `discovered_jobs` — raw scraped, pre-filtering. Temporary.
- `jobs` — promoted, classified, evaluated. Active.
- `job_history` — applied, interviewed, rejected, archived. Permanent record.

**4. Cycle-based operation**
- Each pipeline run is a "cycle" (e.g., biweekly).
- Cycle ID groups all jobs/evaluations/packs from that run.
- Between cycles: DB cleanup, learning engine processes user decisions.
- Cycle report shows what's new since last cycle plus what changed.

**5. Self-contained, local-first**
- Ships as a single installable package (`pip install haxjobs` or `uv tool install`).
- Web UI runs on localhost. No cloud dependency.
- SQLite — no Postgres/MySQL setup needed.
- LLM API keys are the only external dependency (user brings their own).

---

## Data Model Changes Needed

### New tables
- `cycle_state` — track cycle ID, start/end times, jobs discovered, jobs evaluated, packs generated
- `job_history` — permanent record of applied/interviewed/rejected/archived jobs (moved from `jobs` after action)
- `learning_patterns` — learned preferences (preferred companies, rejected keywords, salary trends)

### Modified tables
- `jobs` — add `applied_at`, `decision`, `decision_reason`, `cycle_id`
- `decisions` — wire up writers (currently orphaned)
- `outreach_drafts` — wire up writers (currently orphaned)
- `profile_snapshots` — snapshot profile at each cycle start (currently orphaned)

### Tables to remove
- `favorites` / `saved_jobs` — replaced by decisions table (favorite = applied + good fit)
- `evaluation_history` — redundant with evaluations table + cycle_id

---

## What We Have vs What We Need

### Built and working ✅
- SQLite schema (11 tables, need restructuring)
- Discovery scrapers (Greenhouse, Ashby, Lever)
- Profile JSON format (excellent, keep as target)
- Classification engine (config-driven, working)
- Evaluation engine (prompt builder, parser, validator — excellent)
- Pack generation (auto-pack L1/L2, CV review, templates)
- Cycle report generator
- CLI entry point
- React dashboard shell (10 pages, needs major rework)
- API server routes (needs new endpoints)

### Needs building 🔨
1. **Onboarding wizard** — CV upload → LLM extraction → guided refinement → profile.json
2. **Direct LLM API evaluation** — replace agent subprocess with `openai`/`anthropic` API calls
3. **Decision UI** — user marks jobs as apply/skip/reject from the dashboard
4. **Learning engine** — processes decisions, updates profile preferences
5. **Outreach engine** — find hiring managers, generate messages, track status
6. **DB lifecycle** — cycle state tracking, job history archiving, between-cycle cleanup
7. **Product packaging** — pip-installable, one-command startup, no git clone needed
8. **Profile evolution** — profile fields that auto-update based on usage patterns
9. **Web search discovery** — go beyond ATS scrapers, search the open web for jobs

### Needs deletion 🗑️
- Agent adapters for headless evaluation (replace with direct API)
- `favorites` / `saved_jobs` / `evaluation_history` tables (replace with decisions + cycle_id)

---

## Implementation Order

### Wave 6 — Product Foundation (make it usable)
1. **Direct LLM API evaluation** — rip out subprocess adapters, call APIs directly
2. **Onboarding wizard** — CV upload → extract profile → guided questions
3. **Profile evolution** — profile fields that update based on usage
4. **Decision loop** — user marks apply/skip/reject, decisions table wired up

### Wave 7 — Learning & Outreach (make it smart)
5. **Learning engine** — processes decisions, evolves preferences
6. **Outreach engine** — hiring manager discovery, message generation
7. **DB lifecycle** — cycle tracking, job archiving, cleanup

### Wave 8 — Polish & Ship (make it a product)
8. **Product packaging** — `pip install haxjobs`, one-command start
9. **Web search discovery** — open web job search
10. **Comprehensive testing** — end-to-end product tests

---

## Success Metrics

A complete product means a stranger can:
1. Install with one command
2. Open localhost:8241
3. Upload their CV, answer ~10 questions
4. Come back in 10 minutes to see evaluated jobs with packs ready
5. Mark jobs as apply/skip/reject
6. Next cycle: system is smarter — better matches, fewer irrelevant jobs
7. After 3 cycles: profile is sharply tuned to what actually gets interviews
