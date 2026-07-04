# HaxJobs Internal Agent Harness

HaxJobs has an internal agent harness, but it is **not** a general chatbot and it is **not** a coding agent clone.

It is a small job-search automation layer inside the HaxJobs product. Its job is to let HaxJobs reason with an LLM, optionally call tightly-scoped job-search tools, and return useful results back into the HaxJobs pipeline, dashboard, or CLI.

The harness lives in:

```text
src/haxjobs/agent/
  agent.py       # Agent.run() and Agent.run_with_tools()
  registry.py    # tool registration, filtering, dispatch
  tools.py       # v1 job-search tools
  prompts.py     # named prompt templates from Plan 039
  prompt.py      # system prompt tier builder
  identity.py    # ~/.haxjobs identity/memory/user loaders
```

A terminal playground exists at:

```bash
uv run haxjobs agent ask "Who are you?"
uv run haxjobs agent ask --plain "Test my model connection."
uv run haxjobs agent ask --tools web_search,fetch_page "Find backend roles at Faculty AI."
uv run haxjobs agent ask --tools db_query "How many jobs are in my DB by status?"
```

---

## The short version

A normal chatbot does this:

```text
user text → LLM → assistant text
```

The HaxJobs agent harness does this:

```text
HaxJobs state/profile/job context
        ↓
controlled system prompt
        ↓
LLM call
        ↓
optional tool calls: web_search / fetch_page / db_query / profile_read / profile_write / profile_schema / profile_gaps
        ↓
structured result for HaxJobs workflow
```

The difference is ownership:

- The chatbot owns the conversation.
- HaxJobs owns the workflow.
- The agent is a reasoning component inside that workflow.

That means Python services still own the database, files, packs, decisions, and safety rules. The LLM is allowed to reason and call a few approved tools. It can update only the scoped runtime profile through `profile_write`; it is not allowed to freely browse the filesystem, run shell commands, edit arbitrary files, send outreach, or submit applications.

---

## Why HaxJobs needs an agent harness at all

HaxJobs is built around this loop:

```text
ONBOARD → DISCOVER → CLASSIFY → EVALUATE → DECIDE → LEARN
```

Some parts are deterministic and should stay normal Python:

- SQLite reads/writes
- scraper normalization
- deduplication
- config parsing
- pack file creation
- user decision recording
- API routes

Other parts need language reasoning:

- extracting profile facts from a CV
- asking targeted onboarding questions
- interpreting messy job descriptions
- deciding whether a job is a strong fit
- explaining gaps honestly
- searching for jobs or career pages when existing scrapers are not enough
- summarizing database state in human language

The harness exists for the second group. It keeps language reasoning available without turning the whole product into an uncontrolled chat session.

---

## Design principle: HaxJobs is not a coding agent

The harness borrows internals from Pi, but not Pi's coding-agent surface.

Pi has tools like:

```text
read, write, edit, bash, grep, find, ls
```

Those make sense for a coding agent. They do **not** belong in HaxJobs v1 because HaxJobs is a job-search automation product.

HaxJobs v1 exposes only job-search-native and scoped profile tools:

```text
web_search
fetch_page
db_query
profile_read
profile_write
profile_schema
profile_gaps
```

`profile_write` is the only write-capable tool. It is scoped to the runtime profile file and exists for onboarding/profile enrichment, not arbitrary filesystem writes. Everything else is deferred until a real workflow earns it.

For example:

- `bash` might later be useful for admin automation, but only with a strict allowlist.
- `read` might later be useful for approved local artifacts, but current services can pass the needed text directly.
- `write`/`edit` might later patch approved templates, but pack/profile services should own writes first.

This is deliberate. The smallest safe harness is easier to trust, debug, and integrate.

---

## What was borrowed from Pi

Pi's useful idea is not "give the model a shell." The useful idea is the harness shape:

```text
define tool → expose schema to model → model requests tool → dispatch handler → feed result back
```

HaxJobs maps that to Python:

| Pi concept | HaxJobs equivalent |
|---|---|
| `defineTool()` | `register(name, schema, handler, check_fn=None)` |
| TypeBox schema | plain JSON Schema dict |
| tool allowlist | `Agent(tools=[...])` |
| `excludeTools` | `Agent(exclude_tools=[...])` |
| tool dispatch | `dispatch(name, args)` |
| session prompt loop | `Agent.run_with_tools()` |
| system prompt state | `build_system_prompt()` |
| resource loading | `identity.py` loaders |

What HaxJobs did **not** copy:

- Pi's coding tools
- TUI/session tree
- event streaming
- extension system
- MCP
- large context compaction system
- subagents

Those are useful in a coding agent. They are unnecessary for HaxJobs v1.

---

## What was borrowed from Hermes

Hermes influenced the prompt architecture more than the tool architecture.

The useful Hermes idea is prompt tiering:

```text
stable tier   → identity and standing behavior
context tier  → project/product/user context
volatile tier → memory, current profile snapshot, timestamp
```

HaxJobs implements this in `src/haxjobs/agent/prompt.py`:

```python
build_system_prompt(
    identity=...,      # stable behavior
    context_files=..., # product or task context
    memory=...,        # learned facts / previous decisions
    user_profile=...,  # candidate profile snapshot
    platform="web",   # web / cli / cron behavior hint
)
```

The goal is to keep stable instructions stable and pass per-task data separately.

For example, evaluation should not rebuild a totally different system prompt for every job. The stable rubric should remain stable, while the specific job description belongs in the user message.

That matters for reliability and future provider-side prompt caching.

---

## Provider configuration

The agent loads provider credentials from the provider setup system:

```text
~/.haxjobs/haxjobs.toml
```

That file is different from the repo-root product config:

```text
./haxjobs.toml
```

The split is:

| File | Purpose |
|---|---|
| repo-root `haxjobs.toml` | product config: paths, roles, discovery, evaluation settings |
| `~/.haxjobs/haxjobs.toml` | private provider credentials: API key, base URL, model |

`Agent._load_config()` first tries the setup service. If no setup config exists, it can fall back to environment variables such as `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`.

---

## The two agent modes

The agent has two execution modes.

### 1. `Agent.run()` — single-turn mode

Defined in `src/haxjobs/agent/agent.py`.

Flow:

```text
optional system prompt
        ↓
user prompt
        ↓
OpenAI-compatible chat completion
        ↓
return raw text
```

This mode is for tasks where Python already has all the needed context.

Examples:

- CV extraction
- wizard question generation
- job evaluation
- cover-letter drafting
- outreach draft generation

Callers who need JSON should use:

```python
from haxjobs.evaluate.common import extract_json
```

The agent intentionally does **not** own JSON parsing. HaxJobs already has a battle-tested parser in the evaluation package.

### 2. `Agent.run_with_tools()` — short tool loop mode

Also defined in `src/haxjobs/agent/agent.py`.

Flow:

```text
system/user messages
        ↓
LLM call with allowed tool schemas
        ↓
if model returns final text: stop
        ↓
if model requests tool:
    parse tool args
    dispatch tool handler
    append tool result
    call model again
        ↓
repeat up to max_turns
```

Default limit:

```text
max_turns = 5
```

This is for discovery and research tasks where the model needs to look something up before answering.

Examples:

```bash
uv run haxjobs agent ask --tools web_search,fetch_page \
  "Find backend Python roles at companies similar to Faculty AI."
```

```bash
uv run haxjobs agent ask --tools db_query \
  "Summarize my current jobs by status and top companies."
```

If the model keeps calling tools and never produces a final answer, the loop returns a clear max-turns message instead of recursing forever.

---

## Tool registry internals

The registry lives in `src/haxjobs/agent/registry.py`.

The central object is:

```python
@dataclass
class ToolDef:
    name: str
    schema: dict[str, Any]
    handler: Callable[..., Any]
    check_fn: Callable[[], bool] | None = None
```

A tool has four pieces:

| Piece | Meaning |
|---|---|
| `name` | the name the model calls |
| `schema` | OpenAI-compatible function schema |
| `handler` | Python function that actually runs |
| `check_fn` | optional availability gate |

Tools are stored in:

```python
TOOLS: dict[str, ToolDef]
```

### Registration

A tool is registered like this:

```python
register("fetch_page", schema, fetch_page)
```

`tools.py` registers the built-in job-search tools at import time.

`agent.py` imports `haxjobs.agent.tools` once so the module-level registrations happen.

### Schema filtering

`get_schemas(names=None, exclude=None)` returns only the tools available for a run.

This supports two safety patterns:

```python
Agent(tools=["web_search", "fetch_page"])
```

Only those tools are visible to the model.

```python
Agent(exclude_tools=["db_query"])
```

All registered tools except `db_query` are visible.

If a tool has `check_fn` and it returns false, the model never sees that tool.

### Dispatch

When the model requests a tool call, the loop calls:

```python
dispatch(name, args)
```

The dispatcher:

1. finds the registered tool
2. checks availability
3. calls the Python handler
4. converts dict/list results to JSON
5. catches exceptions and returns an error JSON string

Errors go back to the model as tool results. They do not crash the agent loop.

---

## The v1 tools

The v1 tools live in `src/haxjobs/agent/tools.py`.

### `web_search`

Purpose:

```text
Find job listings or company career pages when configured scrapers are not enough.
```

Current implementation:

- uses stdlib `urllib.request`
- queries DuckDuckGo HTML search
- extracts compact result titles and URLs
- caps output to a small number of results

Example use:

```bash
uv run haxjobs agent ask --tools web_search \
  "Search for junior backend Python roles in London."
```

This is intentionally basic. It avoids adding another dependency until the built-in search is proven insufficient.

Future upgrade path:

- replace internals with a proper search API if DuckDuckGo HTML becomes unreliable
- keep the same tool name/schema so callers do not change

### `fetch_page`

Purpose:

```text
Fetch a public job page or company page and return readable text.
```

Current implementation:

- accepts only `http://` and `https://`
- blocks `localhost`
- blocks private, loopback, link-local, multicast, and unspecified IPs
- uses a timeout
- sends a HaxJobs user-agent
- reads a bounded number of bytes
- strips script/style/html tags with simple regex
- truncates text output to keep prompts small

This gives the agent just enough page-reading ability for job discovery without giving it filesystem or internal network access.

Example use:

```bash
uv run haxjobs agent ask --tools fetch_page \
  "Read this job page and summarize requirements: https://example.com/job"
```

### `db_query`

Purpose:

```text
Read HaxJobs SQLite state for summaries/debugging.
```

Current implementation:

- accepts only SQL whose first token is `SELECT` or `WITH`
- installs a SQLite authorizer that denies writes, DDL, transactions, attach/detach, and PRAGMA
- limits output to 50 rows
- returns rows as JSON-compatible dicts

Example use:

```bash
uv run haxjobs agent ask --tools db_query \
  "What are my top 10 highest-scored unevaluated jobs?"
```

Important: `db_query` is a read-only inspection tool. Product writes still go through normal Python services, not model-generated SQL.

---

## Tool safety model

The model only sees tools that Python chooses to expose for that run.

This means different parts of HaxJobs can use different tool policies.

| Workflow | Recommended agent mode | Tools |
|---|---|---|
| CV extraction | `run()` | none |
| onboarding questions | `run()` | none |
| job evaluation | `run()` | none |
| discovery research | `run_with_tools()` | `web_search`, `fetch_page` |
| dashboard summaries | `run_with_tools()` | `db_query` |
| outreach drafting | `run()` | none by default |

The important rule:

> Tools are not global. Tools are granted per run.

That is what makes the harness different from giving a chatbot permanent access to everything.

---

## How it fits into the HaxJobs job-search process

### 1. Onboarding

Planned flow:

```text
CV upload
  ↓
Python extracts text
  ↓
Agent.run() extracts structured profile JSON
  ↓
Python validates/saves profile draft to state/profile.json
  ↓
Agent uses profile tools to inspect gaps and ask targeted follow-up questions
  ↓
state/profile.json becomes the runtime backbone
```

Onboarding may use `profile_read`, `profile_write`, `profile_schema`, and `profile_gaps` so the agent can enrich the scoped profile. It still cannot read arbitrary files, run shell commands, submit applications, or send outreach.

### 2. Discovery

Current HaxJobs discovery already has deterministic scrapers for ATS sources such as Greenhouse, Ashby, and Lever.

The agent adds a second discovery path:

```text
profile/preferences
  ↓
agent with web_search + fetch_page
  ↓
find company career pages / job URLs / role pages
  ↓
Python normalizes results into discovered_jobs
  ↓
existing hooks promote accepted jobs into jobs
```

The key point: the agent can help **find and interpret pages**, but Python still owns normalization, deduplication, filtering, and database writes.

### 3. Classification

Classification is config-driven from repo-root `haxjobs.toml` and role definitions.

The agent is not required for basic classification. It may later assist with ambiguous jobs, but deterministic classification should remain the default because it is cheaper and easier to test.

### 4. Evaluation

Planned evaluation flow:

```text
job row + full profile snapshot
  ↓
Agent.run()
  ↓
raw model response
  ↓
evaluate.common.extract_json()
  ↓
validation
  ↓
evaluations table
```

Evaluation should **not** use tools by default.

Reason: evaluation should judge a known job against a known profile. If the model can browse during evaluation, scores become less reproducible and harder to debug.

If HaxJobs needs extra company context, that should happen in discovery/enrichment first, then be stored as input data before evaluation.

### 5. Decision loop

The decision loop is primarily UI + database:

```text
user marks apply / skip / reject
  ↓
decisions table
  ↓
learning engine later processes patterns
```

The agent can help summarize decisions, explain patterns, or ask clarifying questions, but it should not make final decisions for the user.

### 6. Pack generation

Pack generation should stay template/service-driven:

```text
evaluation + job + selected CV variant
  ↓
pack builder
  ↓
cover letter / field answers / fit report
```

The agent can draft text sections, but it should not create a new CV per job and should not bypass the reusable CV variant system.

### 7. Outreach

The product rule is strict:

> HaxJobs may draft outreach. It must not send outreach without explicit user approval.

The agent can help with:

- finding possible contacts
- summarizing why a contact is relevant
- drafting a message

But sending remains a user-approved action outside the current harness.

### 8. Learning

The learning engine will process decisions and update preferences.

The agent may help turn messy decision history into summaries, but actual profile writes should remain normal Python service operations with validation.

---

## What this adds beyond a normal chatbot

### 1. Grounding in HaxJobs state

A normal chatbot forgets or invents context unless you paste it in.

HaxJobs has durable state:

- SQLite database
- profile JSON
- decisions table
- evaluations table
- packs
- cycle reports
- config

The harness lets the model reason over selected pieces of that state through controlled inputs/tools.

### 2. Tool permissions are explicit

A chatbot with browsing might search whenever it wants.

HaxJobs exposes tools only when the caller asks for them:

```python
Agent(tools=["web_search", "fetch_page"])
```

No tools means no tools.

### 3. The workflow owns the result

A chatbot answer is usually the final product.

In HaxJobs, the answer is usually an intermediate product:

- extracted profile JSON
- evaluation JSON
- discovered URL candidates
- summary for dashboard
- draft cover letter text

Python validates, stores, and displays the result.

### 4. Safety boundaries match the product

The agent cannot currently:

- send applications
- send outreach
- edit files
- run shell commands
- write database rows through tools
- inspect arbitrary local files

That matches HaxJobs' actual safety boundaries.

### 5. Repeatable pipeline, not endless conversation

HaxJobs is cycle-based. The agent is called at specific points in a pipeline.

A normal chatbot is open-ended. HaxJobs should be boring and repeatable:

```text
same profile + same job + same prompt ≈ same evaluation
```

That is why evaluation uses `run()` without tools.

---

## How the architecture was designed around the harness

HaxJobs is intentionally not "agent first." It is workflow first.

The architecture is layered:

```text
React UI
  ↓
FastAPI feature routes
  ↓
service layer
  ↓
SQLite / files / scrapers / pack builders
  ↓
agent harness only where language reasoning is needed
```

This means the agent is replaceable. If the model changes, the rest of HaxJobs should still work. If one provider fails, the product can show an error instead of corrupting state. If a prompt is bad, deterministic scrapers and DB code are unaffected.

### Feature-based backend

FastAPI mounts feature modules such as:

```text
features/jobs
features/onboarding
features/discovery
features/evaluation
features/decisions
features/packs
features/profile
features/setup
```

Each feature should call the agent only for the reasoning part.

Example:

```text
features/onboarding/service.py
  parse upload
  call Agent.run()
  validate extracted JSON
  save profile
```

Not:

```text
agent decides where to save files and mutates everything itself
```

### SQLite is the source of truth

The harness does not replace the database. It reads selected state and returns outputs that services persist.

That gives HaxJobs:

- auditability
- testability
- cycle reports
- decision history
- repeatable cleanup/learning passes

### Profile is the backbone

The profile is not just chat memory. It is a structured product artifact.

The agent may help create and refine it, but the profile is stored and versioned by HaxJobs services.

This is important because every later stage depends on it:

```text
profile → discovery queries
profile → classification preferences
profile → evaluation rubric
profile → pack personalization
profile → learning updates
```

### Prompt tiers support product modes

`build_system_prompt()` supports `platform` hints:

```text
web  → output intended for dashboard
cli  → concise terminal output
cron → unattended durable-work mindset
```

This lets the same harness work in different HaxJobs surfaces without becoming multiple agents.

### Tools are kept flat and boring

There is one registry and one built-in tools module.

No plugin system yet. No AST discovery. No external tool packages. No MCP.

That is because HaxJobs currently has three tool needs, not thirty.

When more workflows exist, the same registry shape can grow without changing callers.

---

## Current state vs intended integration

### Current state

Implemented now:

- provider-backed `Agent`
- single-turn `run()`
- tool-loop `run_with_tools()`
- registry/dispatch
- `web_search`, `fetch_page`, `db_query`
- identity and prompt tier helpers
- CLI playground: `haxjobs agent ask`
- tests for the harness

### Not fully integrated yet

Future plans still need to connect the harness to product features:

- Plan 045: onboarding backend uses `Agent.run()` for CV extraction and questions
- Plan 047: discovery API may use `web_search` / `fetch_page`
- Plan 048: evaluation uses `Agent.run()` + `extract_json()`
- Later: dashboard summaries may use `db_query`

Until those plans land, the harness is usable directly from CLI, but not yet deeply wired into the web UI workflow.

---

## Example end-to-end future flow

A realistic future discovery/evaluation cycle could look like this:

```text
1. Cron starts discovery cycle

2. Python loads profile and configured target roles

3. Deterministic scrapers run:
   - Greenhouse
   - Ashby
   - Lever

4. Agentic discovery runs for gaps:
   Agent(tools=["web_search", "fetch_page"])
   → find direct company pages not covered by scrapers

5. Python normalizes candidate jobs
   → discovered_jobs

6. Hooks run:
   - blacklist
   - location filter
   - duplicate check
   - already-applied check

7. Accepted jobs promote to jobs table

8. Evaluation runs:
   Agent.run()
   → extract_json()
   → validate
   → evaluations table

9. L1/L2 jobs generate packs
   → reusable CV variant + template-filled cover letter

10. Dashboard shows jobs ranked by fit

11. User decides apply / skip / reject

12. Learning engine updates preferences for next cycle
```

The agent appears in steps 4 and 8, but it does not own the entire process.

That is the architecture: agent-assisted workflow, not chatbot-controlled workflow.

---

## Why no full autonomous loop yet

A larger agent system could include:

- persistent sessions
- memory compaction
- tool plugins
- browser automation
- filesystem tools
- shell tools
- multi-agent review
- automatic outreach sending

HaxJobs does not need those for v1.

The product risks are different from a coding agent. The dangerous actions are:

- applying to jobs
- sending messages
- corrupting the profile
- generating false CV claims
- overfitting to bad job matches
- spamming job sources

So the v1 harness is intentionally small. It gives HaxJobs language reasoning and limited research ability while keeping product state and user-approved actions under normal application control.

---

## Mental model

Think of the HaxJobs agent harness as a **reasoning engine with adapters**, not a person in a chat box.

```text
Chatbot:
  conversation is the product

HaxJobs:
  job-search workflow is the product
  the agent is one engine inside it
```

That is why the harness is small, boring, and scoped.

It is powerful enough to help HaxJobs discover, interpret, evaluate, summarize, and draft.

It is not powerful enough to silently mutate your job search life.

That is the point.
