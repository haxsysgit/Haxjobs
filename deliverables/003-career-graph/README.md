# Plan 003: Career Graph Schema

## What
Replaces the flat `CareerFixture` model with a relational career graph.

## Files
- `src/haxjobs/employment/schema.py` — Pydantic models
- `src/haxjobs/employment/store.py` — SQLite store (stdlib, no ORM)
- `src/haxjobs/employment/migration.py` — fixture → graph migration
- `src/haxjobs/interfaces/profile_cli.py` — CLI handlers
- `src/haxjobs/interfaces/tui.py` — Textual TUI browser
- `tests/test_career_graph.py` — 22 tests

## Quickstart
```bash
# Migrate from fixture
haxjobs profile migrate

# Show profile
haxjobs profile show

# Add a skill
haxjobs profile skill add --track-id <id> --name "Rust" --proficiency learning

# Launch TUI
python -c "from haxjobs.interfaces.tui import run_tui; run_tui()"
```

## Schema diagram
See `diagram.drawio` (open in diagrams.net/draw.io).
