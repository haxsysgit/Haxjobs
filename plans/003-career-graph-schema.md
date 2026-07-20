# Plan 003: Career Graph Schema — Tracks, Skills, Evidence, Persistence

| Key | Value |
|-----|-------|
| **Plan ID** | 003 |
| **Title** | Career Graph Schema |
| **Drift check stamp** | `a060d3d` — 2026-07-17 bugfix commit |
| **Design baseline** | `7da5786` — immutable greenfield baseline |
| **Depends on** | Plan 001 DONE (`a28d5ba`), Plan 002 DONE (`922f6df`) |
| **Status** | TODO |
| **Priority** | P1 — foundation for all employment workflows |

---

## Purpose

Replace the flat `CareerFixture` model with a relational career graph schema in the employment layer. The schema defines independent career tracks, hierarchical skills, evidence items with one verification flag and gap tracking, hard constraints separated from preferences, and persistence via SQLite. A CLI and basic Textual TUI ship alongside so the user can interact with their career profile immediately.

Everything is built from scratch on the greenfield runtime. No legacy code is ported or consulted.

---

## What changed and why

**From:** Flat `CareerFixture` — a single career direction string, flat evidence list, merged constraints, no skill hierarchy, no persistence beyond a JSON file.

**To:** Relational graph in the employment layer — multiple career tracks each with their own skills (in a tree), evidence items linked to skills, gap records for missing evidence, separate hard-constraint and preference columns, SQLite backing, CLI commands, and a Textual TUI.

**Drivers:**
- The greenfield employment layer needs rich data to assemble context for later workflows (evaluate, generate pack). Flat JSON cannot express "Python is a child of Backend Engineering, evidenced by Vigilis and Pharmax, with React being a noted gap."
- CLI + TUI from day one because the user wants interactive beta testing, not command-typing.
- Evidence is a positioning asset, not a truth ledger. One `verified_at` flag. Gaps are first-class records so Hax can fill them later (rebranded GitHub projects, crafted wording, open-source fork-and-extend).
- Separate hard constraints (won't relocate) from preferences (prefers remote) because evaluation logic needs to know which ones are dealbreakers.

---

## Phase 1: Pydantic models (`src/haxjobs/employment/schema.py`)

New file. No existing module is touched.

### Models

```
Person
  person_id: str                          # "arinze-elensulu"
  name: str
  location: str                           # "London, UK"
  work_authorization: str                 # "No sponsorship required"
  notice_period: str                      # "Immediate"
  salary_range: str                       # "£35,000-£45,000"
  created_at: str                         # ISO 8601
  updated_at: str

CareerTrack
  track_id: str                           # "track-backend-python"
  person_id: str → Person
  name: str                               # "Backend Python Engineer"
  target_role_families: list[str]         # ["backend_python", "fullstack_python_react", ...]
  excluded_role_families: list[str]
  created_at: str
  updated_at: str

Skill
  skill_id: str                           # "skill-python"
  track_id: str → CareerTrack
  name: str                               # "Python"
  parent_skill_id: str | None             # "Backend Engineering" — null if root
  proficiency: str                        # "primary" | "strong" | "working" | "learning"
  created_at: str

EvidenceItem
  evidence_id: str                        # "ev-vigilis-role"
  label: str                              # "vigilis-role"
  source: str                             # "typed_cv_profile:v1"
  content: str                            # description of what this evidence proves
  verified_at: str                        # ISO 8601 — one flag, no freshness scoring
  privacy_level: str                      # "public_ok" | "private"
  created_at: str

SkillEvidence (join table)
  skill_id: str → Skill
  evidence_id: str → EvidenceItem

SkillGap
  gap_id: str                             # "gap-react-frontend"
  track_id: str → CareerTrack
  skill_name: str                         # "React / TypeScript"
  target_proficiency: str                 # "strong"
  note: str                               # "CV mentions React but no production project evidence"
  created_at: str

HardConstraint
  constraint_id: str
  track_id: str → CareerTrack
  constraint_text: str                    # "Must be London-based or fully remote UK"
  created_at: str

Preference
  preference_id: str
  track_id: str → CareerTrack
  key: str                                # "work_mode" | "industry" | "company_size" | "tech_stack"
  value: str                              # "hybrid" | "remote"
  weight: str                             # "strong" | "weak"
  created_at: str
```

### Rules in Pydantic validators

- `parent_skill_id` must either be null (root) or reference an existing skill on the same track
- `Skill.name` must be unique within a track
- `EvidenceItem.verified_at` must be a valid ISO 8601 string (no freshness calculation, just presence)
- `SkillGap.target_proficiency` must be one of `primary | strong | working | learning`
- Every `SkillEvidence` row's `skill_id` and `evidence_id` must exist in their respective tables

---

## Phase 2: SQLite storage layer (`src/haxjobs/employment/store.py`)

New file. No existing module is touched.

### `CareerStore` class

```
__init__(db_path: str | Path)
  - Opens SQLite in WAL mode, creates tables via execute() if not exists
  - Foreign keys enforced: PRAGMA foreign_keys = ON

# Person
get_person(person_id) → Person | None
upsert_person(person: Person) → None

# CareerTracks
get_track(track_id) → CareerTrack | None
list_tracks(person_id) → list[CareerTrack]
upsert_track(track: CareerTrack) → None

# Skills
get_skill(skill_id) → Skill | None
list_skills(track_id) → list[Skill]
upsert_skill(skill: Skill) → None
get_skill_tree(track_id) → dict  # nested dict, root skills → children

# Evidence
get_evidence(evidence_id) → EvidenceItem | None
list_evidence_for_skill(skill_id) → list[EvidenceItem]
upsert_evidence(evidence: EvidenceItem) → None
link_skill_evidence(skill_id, evidence_id) → None

# Gaps
list_gaps(track_id) → list[SkillGap]
upsert_gap(gap: SkillGap) → None

# Constraints / Preferences
list_hard_constraints(track_id) → list[HardConstraint]
upsert_hard_constraint(c: HardConstraint) → None
list_preferences(track_id) → list[Preference]
upsert_preference(p: Preference) → None
```

### Table schema (executed in `__init__`)

```sql
CREATE TABLE IF NOT EXISTS persons (...)
CREATE TABLE IF NOT EXISTS career_tracks (...)
CREATE TABLE IF NOT EXISTS skills (parent_skill_id TEXT REFERENCES skills(skill_id), ...)
CREATE TABLE IF NOT EXISTS evidence_items (...)
CREATE TABLE IF NOT EXISTS skill_evidence (PRIMARY KEY (skill_id, evidence_id), ...)
CREATE TABLE IF NOT EXISTS skill_gaps (skill_name TEXT NOT NULL, ...)
CREATE TABLE IF NOT EXISTS hard_constraints (...)
CREATE TABLE IF NOT EXISTS preferences (...)
```

### Design constraints

- `CareerStore` opens one SQLite connection. No connection pooling or async drivers — single user, single writer.
- All methods are synchronous. The employment layer calls them directly.
- Database path defaults to `state/career_graph.db` via `haxjobs.config`.
- No ORM. Plain `sqlite3` from stdlib with dict-like row factories.

---

## Phase 3: One-way migration from CareerFixture v4

New file: `src/haxjobs/employment/migration.py`

### `migrate_career_fixture(fixture: CareerFixture, db_path: str) → None`

Converts the existing flat `CareerFixture` into the graph schema:

1. Creates a `Person` row from the fixture's identity fields
2. Creates one `CareerTrack` from `career_direction` and `target_role_families`
3. Splits `hard_constraints` into `HardConstraint` rows
4. Creates `Preference` rows from `preferred_locations` and `work_authorization`
5. For each `EvidenceItem` in the fixture:
   - Extracts skill names from the `content` field via keyword matching against a known skill list (Python, Django, FastAPI, SQL, SQLite, PostgreSQL, React, TypeScript, JavaScript, Docker, Git, pytest, MCP, API design, LLM pipelines, agent tooling, CI/CD, Linux)
   - Creates `EvidenceItem` row with `verified_at` set to migration timestamp
   - Creates `Skill` rows for any skills not already present
   - Creates `SkillEvidence` join rows
6. Creates `SkillGap` rows where target role families imply skills not present in evidence (React, TypeScript, Docker, CI/CD)

The migration is one-way. There is no reverse migration. The flat fixture remains as historical input only.

### `migrate_cli_entrypoint()` function

Called by a CLI command. Loads the private fixture, runs migration, reports what was created.

---

## Phase 4: CLI commands (`src/haxjobs/cli.py` extension)

Extend the existing CLI. No new entry points. Keep the `experiment review-job` path intact.

New subcommand group:

```
haxjobs profile show          — pretty-print current Person, Tracks, Skills tree, Evidence, Gaps
haxjobs profile track add     — add a new career track
haxjobs profile skill add     — add a skill to a track (optionally under a parent)
haxjobs profile evidence add  — add evidence and link to skills
haxjobs profile gap add       — record a skill gap
haxjobs profile constraint add — add a hard constraint or preference
haxjobs profile migrate       — run the one-way CareerFixture migration
```

### Implementation notes

- `show` reads from `CareerStore`, formats output with Rich tables and trees
- All `add` commands accept JSON or keyword arguments
- `migrate` loads the private fixture file, runs migration, prints summary
- Each command creates a `CareerStore` instance, calls the relevant method, and exits
- No agent loop involved — these are pure CRUD CLI operations on the career graph

`haxjobs.config` gains: `CAREER_DB_PATH = STATE_DIR / "career_graph.db"`

---

## Phase 5: Textual TUI (`src/haxjobs/interfaces/tui.py`)

New file. Textual app for interactive profile management.

### Minimal v1 scope

```
haxjobs tui   — launches the Textual app
```

**Screens:**

1. **Profile overview** (default on launch) — person details, list of career tracks with skill counts, evidence counts, gap counts
2. **Track detail** — selected track's skills (as a tree), evidence list, gaps list, constraints, preferences
3. **Skill detail** — selected skill's evidence links, proficiency, parent/children

**Navigation:**
- Tab or number keys to switch between tracks
- Enter to drill into a track
- `q` or Escape to go back / quit
- `a` to add (context-sensitive: on track list → add track, on skill tree → add skill, etc.)

**Widgets used:**
- `Tree` for skill hierarchy
- `DataTable` for evidence and gap lists
- `Header` with current path breadcrumb
- `Footer` with keybindings
- `Static` for person summary

No CSS files. Use Textual's built-in theme (dark). No custom widgets — only what Textual ships.

### Textual dependency

Added to `pyproject.toml`: `textual>=2.0,<3.0`

---

## Phase 6: Tests

All tests in `tests/test_career_graph.py` (new file).

### Test categories

| # | Test | What it proves |
|---|------|---------------|
| 1 | `test_person_model_validation` | Person Pydantic model enforces required fields |
| 2 | `test_career_track_validation` | CareerTrack can be created, linked to Person |
| 3 | `test_skill_hierarchy` | Skills with parent_skill_id form a tree; cycle detection in validator |
| 4 | `test_evidence_linking` | Evidence links to skills via SkillEvidence join |
| 5 | `test_gap_records` | SkillGap created, listed, filtered by track |
| 6 | `test_constraints_separate_from_preferences` | HardConstraint and Preference are independent tables |
| 7 | `test_store_create_tables` | CareerStore.__init__ creates all tables without error |
| 8 | `test_store_person_crud` | upsert_person, get_person round-trip |
| 9 | `test_store_track_crud` | upsert_track, get_track, list_tracks |
| 10 | `test_store_skill_tree` | get_skill_tree returns nested structure |
| 11 | `test_store_evidence_with_skills` | upsert_evidence + link_skill_evidence + list_evidence_for_skill |
| 12 | `test_store_gaps` | upsert_gap + list_gaps |
| 13 | `test_migration_creates_correct_rows` | migrate_career_fixture against a real fixture dict produces correct row counts |
| 14 | `test_migration_extracts_skills_from_evidence` | Keyword matching extracts Python, Django, etc. from evidence content |
| 15 | `test_migration_creates_gaps` | Missing target skills produce SkillGap rows |
| 16 | `test_cli_profile_show_output` | CLI runs without error, output contains expected strings |
| 17 | `test_cli_profile_migrate` | CLI migrate command completes without error |
| 18 | `test_store_foreign_key_enforcement` | Inserting a skill with bad track_id raises IntegrityError |

Tests use an in-memory SQLite database (`:memory:`). No file-system side effects.

---

## Files in scope (new or modified)

| File | Action |
|------|--------|
| `src/haxjobs/employment/schema.py` | NEW — Pydantic models |
| `src/haxjobs/employment/store.py` | NEW — CareerStore SQLite layer |
| `src/haxjobs/employment/migration.py` | NEW — one-way fixture migration |
| `src/haxjobs/employment/__init__.py` | MODIFY — export new public symbols |
| `src/haxjobs/config.py` | MODIFY — add CAREER_DB_PATH |
| `src/haxjobs/cli.py` | MODIFY — add `profile` subcommand group |
| `src/haxjobs/interfaces/tui.py` | NEW — Textual app |
| `tests/test_career_graph.py` | NEW — all tests |
| `pyproject.toml` | MODIFY — add textual dependency |

---

## Files explicitly out of scope (do not touch)

- `src/haxjobs/employment/review_job.py` — existing job review logic
- `src/haxjobs/employment/job_source.py` — existing source fetcher
- `src/haxjobs/employment/fixtures.py` — existing CareerFixture/JobFixture models (kept for backward compat during migration, deleted after Plan 004 confirms no callers)
- `src/haxjobs/agent_core/` — agent core is domain-free, this plan adds employment-layer domain logic
- `src/haxjobs/model/` — model boundary unchanged
- `src/haxjobs/interfaces/experiment_cli.py` — existing `review-job` command untouched
- `tests/test_stage0_job_review.py` — no changes
- `tests/test_stage1_source_inspection.py` — no changes
- `state/` — data directory is runtime state, not committed

---

## Verification

```bash
# Backend
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/test_career_graph.py
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/  # full suite, must not regress
PYTHONPATH=src:. .venv/bin/python -m py_compile $(find src tests -name '*.py')
uv lock --check

# CLI (uses in-memory or temp db, no private fixture)
PYTHONPATH=src:. .venv/bin/python -m haxjobs profile show
PYTHONPATH=src:. .venv/bin/python -m haxjobs profile migrate

# TUI smoke (launches and exits immediately)
PYTHONPATH=src:. .venv/bin/python -c "from haxjobs.interfaces.tui import HaxJobsTUI; assert HaxJobsTUI is not None"

# Git hygiene
git diff --check
```

---

## STOP conditions

- **STOP** if `textual` import fails on the target Python (3.12) — report the error, do not patch
- **STOP** if any existing test in `tests/test_stage0_job_review.py` or `tests/test_stage1_source_inspection.py` breaks — they are immutable
- **DO NOT** touch `state/experiments/fixtures/backend-career.json` — it is a private file owned by the operator
- **DO NOT** import or reference any deleted legacy module (`haxjobs.agent`, `haxjobs.product_tools`, `haxjobs.evaluate`, `haxjobs.discovery`, etc.)

---

## Deliverables

After implementation, produce:

1. `deliverables/003-career-graph/plan.md` — copy of this plan
2. `deliverables/003-career-graph/report.md` — evidence-backed completion report (what was built, test counts, decisions made, anything deferred)
3. `deliverables/003-career-graph/diagram.drawio` — clean Draw.io diagram of the new schema relationships
4. `deliverables/003-career-graph/diagram.png` — exported PNG
5. `deliverables/003-career-graph/README.md` — index of all deliverables

---

## Design decisions recorded in this plan

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | One `verified_at` flag, no freshness scoring | Evidence is a positioning asset. Hax decides staleness at context-assembly time. |
| D2 | Skill gaps are first-class records | Hax needs them to build roadmaps, suggest projects, fork-and-extend open-source repos. |
| D3 | Hierarchical skills via `parent_skill_id` self-reference | Rich data for automations. A tree, not a flat list. |
| D4 | Hard constraints and preferences in separate tables | Evaluation needs to distinguish dealbreakers from nice-to-haves. |
| D5 | Synchronous SQLite via stdlib `sqlite3` | Single user, single writer. No async overhead needed. |
| D6 | Textual for TUI, not Rich prompts | User wants interactive terminal UI, not command-question-answer loops. |
| D7 | One-way migration from CareerFixture, no reverse path | The fixture is historical input. The graph schema is the new source of truth. |
| D8 | WAL mode for SQLite | Allows concurrent reads during writes. Standard for local-first apps. |

---

*Executor: read this plan in full before implementing. Compare every file path and import against live code at the drift-check stamp. If live code differs from what this plan assumes, surface it immediately. Do not silently adapt.*
