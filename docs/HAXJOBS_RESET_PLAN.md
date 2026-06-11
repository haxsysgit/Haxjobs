# HaxJobs Reset Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reset HaxJobs around Arinze's real workflow: profile truth, source-first discovery, role-family CV variants, per-job prep packs, Telegram reports, and LinkedIn outreach.

**Architecture:** Keep the useful pieces, but remove split-brain behavior. SQLite becomes the job source of truth. CVs become stable reusable variants. Packs become per-job prep material, not per-job CV factories. Browser automation stays as a future-safe lane, not the center of the product.

**Tech Stack:** Python stdlib, SQLite, Playwright, Hermes CLI on Archilles, React/Vite dashboard, system cron, Telegram via Archilles.

---

## 0. Current diagnosis

The project drifted because it tried to become a full autonomous application machine before the core workflow was stable.

Current problems:

1. Per-job CV generation is mixed into pack generation.
2. `pipeline.db`, `intake/*.json`, pack folders, and dashboard sync all act like sources of truth.
3. The active pipeline evaluates jobs, but does not reliably create the per-job materials Arinze needs.
4. Telegram reporting is not the main product surface yet.
5. LinkedIn is set up, but not integrated into a clean discovery/outreach model.
6. Some code is legacy, experimental, or future automation and should not stay in the active path.
7. Cron jobs exist, but the runtime story is unclear and too noisy.

The reset should be done in small commits. Do not rewrite everything at once.

---

## 1. Target architecture

```text
profile/
  master_profile.json
  role_taxonomy.json

cv_variants/
  backend_python/
  fullstack_python_react/
  ai_engineer_llm/
  ai_automation_agents/
  junior_software/
  data_python/
  platform_backend/

discovery/
  linkedin_jobs.py
  ats_sources.py
  normalize.py
  source_quality.py

evaluation/
  score_job.py
  classify_role_family.py
  recommend_cv_variant.py

packs/
  <job_id>/
    fit_report.md
    cover_letter.md
    field_answers.md
    interview_questions.md
    telegram_summary.md
    metadata.json

outreach/
  people_finder.py
  outreach_queue.py
  message_drafts.py

cron/
  discover_jobs.sh
  evaluate_jobs.sh
  send_digest.sh

state/
  pipeline.db
```

Important: `packs/` and `state/` are runtime/generated and should not be committed.

---

## 2. Reset rules

### Rule 1: No per-job CV by default

A job pack must recommend a CV variant. It should not generate a fresh CV unless Arinze explicitly asks.

### Rule 2: SQLite is the job source of truth

`intake/*.json` can be kept as raw archive/import files, but the active pipeline should read and write jobs from SQLite.

### Rule 3: Telegram is the primary delivery surface

Dashboard is useful for review, but Telegram is where Archilles talks to Arinze.

### Rule 4: Browser automation is staged

Automation levels:

```text
0 discovery/ranking only
1 copy-paste docs and answers
2 prefill forms
3 upload docs and stop before submit
4 approved submit for known safe forms
5 full automation for trusted repeatable flows
```

Only levels 0 to 2 are core reset scope. Level 3 can remain experimental. Levels 4 to 5 are future.

### Rule 5: No auto LinkedIn outreach

LinkedIn automation may search/read/draft. It must not connect or message without approval.

---

## 3. Implementation phases

## Phase 1: Product anchor and repo cleanup

Goal: make the repo understandable before touching behavior.

### Task 1.1: Commit product spec and reset plan

**Files:**
- Create: `docs/HAXJOBS_PRODUCT_SPEC.md`
- Create: `docs/HAXJOBS_RESET_PLAN.md`

**Verification:**

```bash
git diff --check
git status --short
```

Expected: only docs changed, no whitespace errors.

**Commit:**

```bash
git add docs/HAXJOBS_PRODUCT_SPEC.md docs/HAXJOBS_RESET_PLAN.md
git commit -m "document HaxJobs product reset"
```

### Task 1.2: Add repo map

**Objective:** create one file that explains which folders are active, generated, legacy, or future.

**Files:**
- Create: `docs/REPO_MAP.md`

**Content sections:**

```text
Active runtime
Generated runtime
Profile and CV source
Discovery
Evaluation
Dashboard
Legacy candidates
Future automation candidates
```

**Verification:**

```bash
test -f docs/REPO_MAP.md
```

### Task 1.3: Move legacy candidates behind an explicit boundary

Do not delete yet. Move to `legacy/` after confirming nothing active imports them.

Candidate files:

```text
process_pending_intakes.py
infographic/
discovery/auto_apply.py
discovery/site_knowledge.json
```

Before moving, verify imports:

```bash
grep -R "process_pending_intakes\|auto_apply\|site_knowledge" -n . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=dashboard/dist
```

If no active runtime imports exist, move:

```bash
mkdir -p legacy/discovery legacy/visuals
mv process_pending_intakes.py legacy/process_pending_intakes.py
mv infographic legacy/visuals/infographic
mv discovery/auto_apply.py legacy/discovery/auto_apply.py
mv discovery/site_knowledge.json legacy/discovery/site_knowledge.json
```

**Verification:**

```bash
python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh scripts/haxjobs-update
```

**Commit:**

```bash
git add -A
git commit -m "separate legacy automation code"
```

---

## Phase 2: Role taxonomy and CV variant model

Goal: stop generating a different CV for every job.

### Task 2.1: Create role taxonomy schema

**Files:**
- Create: `profile/role_taxonomy.json`

**Initial content shape:**

```json
{
  "backend_python": {
    "label": "Python Backend Engineer",
    "cv_variant": "backend_python",
    "titles": ["Python Developer", "Backend Developer", "Backend Engineer", "FastAPI Developer"],
    "positive_keywords": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Redis", "API"],
    "negative_keywords": ["senior manager", "head of engineering", "sales engineer"]
  }
}
```

Include these families:

```text
backend_python
fullstack_python_react
ai_engineer_llm
ai_automation_agents
junior_software
data_python
platform_backend
```

**Verification:**

```bash
python3 -m json.tool profile/role_taxonomy.json >/dev/null
```

### Task 2.2: Add role family classifier tests

**Files:**
- Create: `tests/test_role_taxonomy.py`
- Create/modify: `evaluation/role_family.py`

Test cases:

```text
Python Developer → backend_python
Full Stack Developer React Python → fullstack_python_react
Junior AI Engineer → ai_engineer_llm
AI Automation Developer → ai_automation_agents
Graduate Software Engineer → junior_software
Data Mining Python Developer → data_python
Platform Backend Engineer → platform_backend
```

Run:

```bash
pytest tests/test_role_taxonomy.py -v
```

Expected first run: fail because module does not exist.

### Task 2.3: Implement role family classifier

**Files:**
- Create: `evaluation/role_family.py`

Minimal API:

```python
def classify_role_family(title: str, description: str = "") -> dict:
    return {
        "role_family": "backend_python",
        "confidence": 0.82,
        "matched_terms": ["Python", "FastAPI"]
    }
```

Run:

```bash
pytest tests/test_role_taxonomy.py -v
```

Expected: pass.

### Task 2.4: Create CV variants folder

**Files:**
- Create: `cv_variants/README.md`
- Move/copy from: `base_cvs/`

Target structure:

```text
cv_variants/backend_python/Arinze_Elenasulu_Backend_Python_CV.pdf
cv_variants/fullstack_python_react/Arinze_Elenasulu_Full_Stack_CV.pdf
cv_variants/ai_engineer_llm/Arinze_Elenasulu_AI_Engineer_CV.pdf
cv_variants/ai_automation_agents/Arinze_Elenasulu_AI_Automation_CV.pdf
cv_variants/junior_software/Arinze_Elenasulu_Junior_Software_CV.pdf
cv_variants/data_python/Arinze_Elenasulu_Data_Python_CV.pdf
cv_variants/platform_backend/Arinze_Elenasulu_Platform_Backend_CV.pdf
```

Keep HTML sources if they are the edit source.

**Verification:**

```bash
find cv_variants -name '*.pdf' | wc -l
```

Expected: at least 5.

---

## Phase 3: Database alignment

Goal: one job truth source.

### Task 3.1: Add fields for role family and CV recommendation

**Files:**
- Modify: `db/schema.py`
- Add migration logic if schema uses ad-hoc SQLite alterations

Fields:

```text
role_family TEXT
role_family_confidence REAL
recommended_cv_variant TEXT
source_quality TEXT
apply_url TEXT
pack_status TEXT
telegram_sent_at TEXT
outreach_status TEXT
```

**Test:**
- Add `tests/test_db_schema.py`
- Verify init creates columns.

Run:

```bash
pytest tests/test_db_schema.py -v
```

### Task 3.2: Normalize discovered jobs before insert

**Files:**
- Create: `discovery/normalize.py`
- Add tests: `tests/test_discovery_normalize.py`

Function:

```python
def normalize_job(raw: dict, source: str) -> dict:
    ...
```

Output must contain:

```text
title, company, location, source, source_quality, source_url, apply_url, description, discovered_at
```

---

## Phase 4: Replace per-job CV pack generation

Goal: job packs reference stable CV variants.

### Task 4.1: Create pack generator tests

**Files:**
- Create: `tests/test_pack_generator.py`
- Create: `packs_builder/job_pack.py`

Test expectations:

1. Pack creates `fit_report.md`.
2. Pack creates `cover_letter.md`.
3. Pack creates `field_answers.md`.
4. Pack creates `interview_questions.md`.
5. Pack creates `telegram_summary.md`.
6. Pack creates `metadata.json` with `recommended_cv_variant`.
7. Pack does not create a new CV file.

### Task 4.2: Implement markdown-first pack generator

**Files:**
- Create: `packs_builder/job_pack.py`

Minimal API:

```python
def build_job_pack(job: dict, evaluation: dict, profile: dict, cv_variant: dict) -> dict:
    return {
        "pack_dir": "packs/<job_id>",
        "files": [...]
    }
```

Verification:

```bash
pytest tests/test_pack_generator.py -v
```

### Task 4.3: Wire pack generation only after evaluation and threshold

**Files:**
- Modify: `evaluate_with_hermes.py` or create a separate `generate_ready_packs.py`

Preferred: separate script.

```text
evaluate jobs → save scores
build packs for jobs where:
  fit_score >= threshold
  pack_status is empty
  recommended_cv_variant exists
```

Do not bundle into the evaluator until tests exist.

---

## Phase 5: Telegram digest

Goal: Archilles sends useful, short reports.

### Task 5.1: Create Telegram summary renderer

**Files:**
- Create: `notifications/telegram_digest.py`
- Tests: `tests/test_telegram_digest.py`

Function:

```python
def render_job_digest(jobs: list[dict]) -> str:
    ...
```

Must include:

```text
role/company
fit score
recommended CV variant
apply link
why it fits
gaps
outreach action
```

Must not exceed a sane character budget for Telegram.

### Task 5.2: Create Archilles send script

**Files:**
- Create: `cron/send_telegram_digest.sh`

Command should use Archilles only:

```bash
hermes send -t telegram:-1003991695885:18 "$(python3 notifications/telegram_digest.py)"
```

High-fit urgent jobs can use topic 22.

---

## Phase 6: LinkedIn discovery and outreach

Goal: integrate LinkedIn safely.

### Task 6.1: Save LinkedIn search script as source

**Files:**
- Create: `discovery/linkedin_jobs.py`

Requirements:

- use `/home/hermes/.linkedin-profile/`
- read-only job search
- low volume
- output normalized jobs
- no auto-apply
- no messaging

### Task 6.2: Add people discovery queue

**Files:**
- Create: `outreach/people_queue.py`
- Tests: `tests/test_people_queue.py`

Data shape:

```json
{
  "company": "ExampleCo",
  "job_id": "...",
  "person_name": "...",
  "linkedin_url": "...",
  "role": "Recruiter",
  "reason": "Posted the role / hiring for Python engineers",
  "status": "found"
}
```

### Task 6.3: Draft outreach only

**Files:**
- Create: `outreach/draft_messages.py`

No send action in this phase.

---

## Phase 7: Cron simplification

Goal: make Archilles predictable.

### Task 7.1: Replace noisy crontab with named scripts

Desired system cron:

```text
# Discovery
0 8 * * * /home/hermes/haxjobs/cron/discover_jobs.sh

# Evaluation
30 8,12,16 * * * /home/hermes/haxjobs/cron/evaluate_jobs.sh

# Digest
0 18 * * * /home/hermes/haxjobs/cron/send_telegram_digest.sh

# Health
*/30 * * * * /home/hermes/haxjobs/cron/healthcheck.sh
```

Do not edit crontab until scripts are tested manually.

### Task 7.2: Add healthcheck

**Files:**
- Create: `cron/healthcheck.sh`

Check:

```text
API port 8800
Vite port 5173
database readable
LinkedIn profile exists
latest discovery timestamp
latest digest timestamp
```

Only alert Telegram on real failure or stale age threshold.

---

## 4. Cut list

Move to `legacy/` after import check:

```text
process_pending_intakes.py
infographic/
discovery/auto_apply.py
discovery/site_knowledge.json
```

Keep but refactor:

```text
cron/run_pipeline.sh
evaluate_with_hermes.py
db/
api_server.py
dashboard/
discovery/browser_scraper.py
discovery/job_classifier.py
cv_generate.py
cv_validator.py
base_cvs/
```

Rename or replace:

```text
base_cvs/ → cv_variants/
discovery/job_classifier.py → evaluation/role_family.py
packs as CV factory → packs as per-job prep material
```

---

## 5. Verification commands before each push

```bash
cd /home/hax/haxjobs
python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n scripts/haxjobs-update cron/*.sh
cd dashboard && npm run build
```

If tests exist:

```bash
pytest -q
```

Then:

```bash
git status --short
git add -A
git commit -m "short clear message"
git push origin main
```

Archilles update:

```bash
ssh archilles haxjobs-update
```

---

## 6. Definition of done for reset

The reset is done when:

1. Product spec exists and matches Arinze's actual goal.
2. Legacy code is separated from active runtime.
3. Role taxonomy exists and classifies jobs into 5 to 7 families.
4. CV variants exist and are reused.
5. Per-job packs no longer generate fresh CVs by default.
6. SQLite is the active source of truth.
7. Telegram digest shows jobs with recommended CV variant and next action.
8. LinkedIn discovery can add jobs and people without sending messages.
9. Archilles cron is small, named, and observable.
10. `haxjobs-update` keeps Archilles synced from GitHub.
