# Report: Career Graph Schema Implementation

## Summary
Replaced flat CareerFixture with relational career graph: 8 domain models, SQLite store with 8 tables, migration from fixture, CLI with Rich formatting, and Textual TUI.

## Changed files
| File | Action | Purpose |
|------|--------|---------|
| `src/haxjobs/employment/schema.py` | new | Pydantic models (Person, CareerTrack, Skill, EvidenceItem, SkillEvidence, SkillGap, HardConstraint, Preference) |
| `src/haxjobs/employment/store.py` | new | SQLite store with WAL mode, CRUD for all models, skill tree query |
| `src/haxjobs/employment/migration.py` | new | CareerFixture → graph migration with keyword-based skill extraction |
| `src/haxjobs/interfaces/profile_cli.py` | new | CLI handlers for `profile show/migrate/track/skill/evidence/gap/constraint` |
| `src/haxjobs/interfaces/tui.py` | new | Textual TUI with 3 screens: profile overview, track detail, skill detail |
| `src/haxjobs/cli.py` | modified | Added `profile` subcommand group |
| `src/haxjobs/config.py` | modified | Added `CAREER_DB_PATH` |
| `haxjobs.toml` | modified | Added `[paths]` section needed by config.py |
| `pyproject.toml` | modified | Added `rich` and `textual` dependencies |
| `tests/test_career_graph.py` | new | 22 tests: model validation, store CRUD, migration, CLI |

## Test results
- 22 new tests all pass
- Full suite: 86 tests, 0 regressions
- py_compile clean
- uv lock --check passes
- git diff --check clean

## Skills extracted
From the backend-career fixture evidence:
- Python, pytest, MCP, React, TypeScript (5 skills)

## Gaps created
- React, TypeScript, Docker, CI/CD (4 gaps)

## Limitations
- Migration always creates new tracks (uses UUID-based track_id) — repeated runs produce duplicates
- Skill extraction uses simple keyword matching — no NLP
- TUI requires terminal with true color support
