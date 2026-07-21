# Getting Started with HaxJobs

HaxJobs is a greenfield employment-agent runtime under active development.

The conversational agent interface is now live. You can open an inline prompt_toolkit terminal that streams real provider responses, dispatches employment tools, persists canonical conversation history, and resumes prior sessions.

## Install for development

```bash
git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync
```

Use Python 3.12 or newer.

Run commands from the repository root:

```bash
cd /home/hax/haxjobs
```

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

Migrate your private career fixture into the local graph:

```bash
haxjobs migrate
```

This reads the ignored private fixture at `state/experiments/fixtures/backend-career.json` and writes the local database to `state/career_graph.db`.

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
| `haxjobs chat --resume ID` | Resume a specific session |
| `haxjobs chat --fake` | Scripted development mode (no network) |

## Key bindings

| Key | Action |
|-----|--------|
| Enter | Submit |
| Ctrl+J | Insert newline (guaranteed multiline) |
| Shift+Enter | May work depending on terminal |
| Escape | Interrupt the active turn |
| Ctrl+C | Clear non-empty editor; exit when empty and idle |
| Ctrl+D | Exit when editor is empty |

Assistant text streams in real time. Tool lifecycle events appear from the runtime.

## Remaining commands

```bash
haxjobs profile show              # View career graph
haxjobs profile migrate           # Rebuild career graph
haxjobs experiment review-job     # Stage 0/1 experiments
```

## Fake mode

For development without provider calls:

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-dev.db haxjobs chat --fake
```

```
Session ID: dev-session
Resume: haxjobs chat --resume dev-session
Type your message. Enter to submit, Ctrl+J for newline, Escape to interrupt.
Ctrl+C to clear (or exit if empty), Ctrl+D to exit when empty.

> hello

FAKE: I am a simulated Hax model. The runtime is working correctly.
```

## Current limitations

- One career person and one track are assumed.
- `inspect_job_source` resolves refs 49 and 328 to known fixture paths only.
- Context is not compacted. Long sessions may hit token limits.
- No approval workflows, background operations, or sub-agents yet.
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
  employment/     career graph, host, context, job source, composition, fixtures
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
  test_stage0_job_review.py
  test_stage1_source_inspection.py
  test_career_graph.py

deliverables/003-career-graph/
  conversation-runtime.drawio / .png
  interaction-flow.drawio / .png
```

## Progress documents

- `docs/PRODUCT.md`: product direction and current limitations
- `docs/HAXJOBS.md`: current architecture and built-versus-planned state
- `discussion/`: architecture decisions and research
- `plans/README.md`: completed and corrected implementation stages
- `deliverables/`: reports and diagrams for each completed stage
