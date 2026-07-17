# HaxJobs Agent System

HaxJobs uses a small native agent loop. It is plain Python around an OpenAI-compatible model client.

## What the loop owns

The loop owns only model interaction:

1. build the system prompt
2. send messages and allowed tool schemas
3. receive text or tool calls
4. dispatch tool calls
5. append structured results
6. repeat until text is returned or the turn limit is reached

Business logic stays outside the loop.

## Files

```text
src/haxjobs/agent/
  agent.py          model calls and tool loop
  registry.py       tool registration, schema filtering, dispatch
  tool_modes.py     workflow-specific allowlists
  tools.py          imports tool modules so they register
  tools_product.py  adapters over shared product actions
  tools_profile.py  profile access
  tools_web.py      public web search and page fetch
  tools_db.py       read-only admin SQL
  prompt.py         stable, flow, and volatile prompt assembly
  identity.py       local identity files
  prompts.py        named prompt templates
```

## Registered tools

### Product

- `discover_jobs`
- `evaluate_fit`
- `generate_pack`
- `record_decision`

### Profile

- `profile_read`
- `profile_write`
- `profile_schema`
- `profile_gaps`

### Support

- `web_search`
- `fetch_page`
- `db_query`

There are no placeholder outreach or learning tools. Add them when the underlying action works.

## Tool modes

| Mode | Tools |
|---|---|
| `profile` | profile read, write, schema, gaps |
| `discovery` | discover jobs, profile read, web search, page fetch |
| `evaluation` | evaluate fit, profile read |
| `application` | generate pack, profile read |
| `decision` | record decision |
| `admin` | read-only DB query, profile read, profile schema |

An agent gets no tools by default. A caller must select a mode or explicit allowlist. A mode limits what the model can see. It does not grant permissions outside the registered handler.

## Tool result contract

Dispatch returns JSON text. Failures use:

```json
{"ok": false, "code": "error_code", "error": "human-readable message"}
```

Product actions return an `ok` field plus action-specific data. Do not hide errors behind fake success responses.

## Prompt tiers

The intended prompt order is:

1. Stable identity and safety rules
2. Flow instructions for discovery, evaluation, profile work, or another action
3. Volatile task context such as the selected profile slice and job

Stable text should remain byte-for-byte stable where possible so provider prompt caching can work. Large static schemas should be injected into the relevant flow prompt instead of fetched through a tool call. The current profile schema tool still exists and can be removed when flow prompts fully own that context.

## Safety

- `db_query` is read-only and appears only in the admin mode. Callers must explicitly select that mode or tool.
- `profile_write` is available only in profile mode.
- `fetch_page` validates each redirect target.
- Product tools accept typed IDs and load records themselves.
- The model does not receive shell, arbitrary file-write, application-submit, or message-send tools.
- External side effects need explicit approval.

## Missing fundamentals

The current loop is useful, but it is not yet the long-running career agent described in the product direction. It lacks:

- durable sessions and message history
- run records and checkpoints
- context retrieval and ranking
- context-window and token tracking
- compaction summaries
- child-agent isolation
- resume after partial failure
- per-run tool timelines, latency, and cost records
- tool-level stop signals

These should be designed as one run lifecycle. Adding isolated helpers without a session model would create more drift.

## Terminal playground

```bash
uv run haxjobs agent ask "Who are you?"
uv run haxjobs agent ask --plain "Test the provider"
uv run haxjobs agent ask --tools web_search,fetch_page "Find Example Ltd careers"
```

This is a testing surface. The finished product CLI still needs explicit career commands.
