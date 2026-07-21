# Getting Started with HaxJobs

HaxJobs is a greenfield employment-agent runtime under active development.

The conversational agent interface is live. You can open an inline prompt_toolkit terminal that streams real provider responses, dispatches employment tools, persists canonical conversation history with durable tool execution boundaries, and resumes prior sessions.

## Install for development

```bash
git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync
```

Use Python 3.12 or newer.

## Prerequisites

### 1. Provider credentials

Create `~/.haxjobs/haxjobs.toml`:

```toml
[provider]
name = "deepseek"
model = "deepseek-chat"
api_key = "sk-..."
base_url = "https://api.deepseek.com/v1"
```

### 2. Career graph

Migrate a career fixture into the local graph:

```bash
# Using synthetic test fixture (no private data)
uv run -- haxjobs profile migrate --fixture tests/fixtures/job_review/career.json
```

This writes the local database to `state/career_graph.db`.

### 3. Import jobs (one-way, operator-controlled)

```bash
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions import discussion/fixtures/harness/job-49.json
PYTHONPATH=src:. uv run -- python3 -m haxjobs.employment.job_actions import discussion/fixtures/harness/job-328.json
```

## Launch Hax

```bash
haxjobs
```

Or explicitly:

```bash
haxjobs chat
```

This opens or resumes the latest live session. You'll see:

```
Session ID: abc123def456
Resume: haxjobs chat --resume abc123def456
Type your message. Enter to submit, Ctrl+J for newline, Escape to interrupt.
Ctrl+C to clear (or exit if empty), Ctrl+D to exit when empty.

>
```

## Chat commands

| Command | Behaviour |
|---------|-----------|
| `haxjobs` | Open or resume latest session |
| `haxjobs chat` | Same as above |
| `haxjobs chat --new` | Create a new session |
| `haxjobs chat --new --person-id ID` | New session for a specific person |
| `haxjobs chat --new --track-id ID` | New session for a specific track |
| `haxjobs chat --resume ID` | Resume a specific session |
| `haxjobs chat --fake` | Scripted development mode (no network) |

## Key bindings

| Key | Action |
|-----|--------|
| Enter | Submit |
| Ctrl+J | Insert newline (guaranteed multiline) |
| Escape | Interrupt the active turn |
| Ctrl+C | Clear non-empty editor; exit when empty and idle |
| Ctrl+D | Exit when editor is empty |

## Employment tools

Hax has three tools available in conversation:

- `get_job(job_id)` — retrieve a saved job
- `inspect_job_source(job_id)` — fetch current source page for a job
- `record_job_assessment(...)` — record a typed assessment

Ask about jobs naturally: "What do you think of job 49?" or "Should I pursue job 328?"

## Remaining commands

```bash
haxjobs profile show              # View career graph
haxjobs profile migrate           # Rebuild career graph
haxjobs profile track add ...     # Add a career track
haxjobs profile skill add ...     # Add a skill
haxjobs profile evidence add ...  # Add evidence
haxjobs profile gap add ...       # Add a skill gap
haxjobs profile constraint add ... # Add a hard constraint
```

## Fake mode

For development without provider calls:

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-dev.db haxjobs chat --fake
```

## Current limitations

- Multiple persons/tracks require explicit selection.
- Context is not compacted. Long sessions may hit token limits.
- No approval workflows, background operations, or sub-agents yet.
- No source observation history (current snapshot only).
- No user decisions (Plan 005).
- Concurrent same-session processes are not locked.
- No web or desktop UI.

## Verify the current code

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
```

## Current file map

```text
src/haxjobs/
  model/          provider boundary and canonical model types
  agent_core/     messages, live events, turn runtime, session, session store, tools
  employment/     career graph, host, context, job source, job actions, tools, identifiers, composition, fixtures, migration, store, schema
  interfaces/     terminal client, CLI handlers
  cli.py          installed command entry point
  config.py       path configuration

tests/
  test_conversation_messages.py
  test_live_events.py
  test_model_streaming.py
  test_session_store.py
  test_turn_runtime.py
  test_employment_host.py
  test_session.py
  test_terminal.py
  test_terminal_pty.py (environment-dependent)
  test_career_graph.py
  test_job_actions.py
  test_employment_tools.py
  test_trajectory_job_328.py
  test_durable_tool_effects.py

deliverables/004-saved-job-assessment/
  employment-models.drawio / .png
  tool-effects.drawio / .png
  conversation-trajectory.drawio / .png
```

## Progress documents

- `docs/PRODUCT.md`: product direction and current limitations
- `docs/HAXJOBS.md`: current architecture and built-versus-planned state
- `discussion/`: architecture decisions and research
- `plans/README.md`: completed and corrected implementation stages
- `deliverables/`: reports and diagrams for each completed stage
