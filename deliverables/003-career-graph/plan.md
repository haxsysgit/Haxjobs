# Plan 003: Career Graph Schema

## Purpose
Replace the flat `CareerFixture` model with a relational career graph schema.

## Architecture
- **schema.py**: Pydantic models for Person, CareerTrack, Skill, EvidenceItem, SkillEvidence, SkillGap, HardConstraint, Preference
- **store.py**: SQLite persistence via stdlib sqlite3, WAL mode, no ORM
- **migration.py**: One-time migration from CareerFixture JSON to graph schema
- **profile_cli.py**: CLI handlers for `haxjobs profile ...` commands
- **tui.py**: Textual TUI app for browsing the career graph

## Key Decisions
- SQLite in WAL mode with foreign keys enabled
- Synchronous API — no async needed for local DB
- Skills extracted from evidence via keyword matching against known tech list
- Migration is idempotent via upserts (creates new tracks each run)
- Rich for CLI table formatting, Textual for TUI
