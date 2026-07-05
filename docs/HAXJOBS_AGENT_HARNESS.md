# HaxJobs Internal Agent Harness

HaxJobs has an internal agent harness, but it is **not** a general chatbot and it is **not** a coding agent clone.

It is a small job-search automation layer inside the HaxJobs product. Its job is to let HaxJobs reason with an LLM, optionally call tightly-scoped job-search tools, and return useful results back into the HaxJobs pipeline, dashboard, or CLI.

The harness lives in:

```text
src/haxjobs/agent/
  agent.py          # Agent.run() and Agent.run_with_tools()
  registry.py       # tool registration, filtering, dispatch
  tools.py          # import aggregator (pulls in domain tool modules)
  tools_web.py      # web_search, fetch_page
  tools_db.py       # db_query (admin/support only)
  tools_profile.py  # profile_read, profile_write, profile_schema, profile_gaps
  tools_product.py  # discover_jobs, evaluate_fit, generate_pack, record_decision (BUILD)
                    # find_contacts, draft_message, analyze_patterns (FUTURE stubs)
  tool_modes.py     # mode → tool list mapping
  prompts.py        # named prompt templates from Plan 039
  prompt.py         # 3-tier system prompt builder
  identity.py       # ~/.haxjobs identity/memory/user loaders
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

The harness is a scoped reasoning component inside the HaxJobs product, not a chatbot controller. Key decisions:

- The Python app (FastAPI) owns the **database, files, profile, packs, decisions, and safety rules**.
- The agent is a **callable library**: `Agent().run(prompt)` returns text, `Agent(tool_mode="evaluation").run_with_tools(prompt)` returns text after optional tool calls.
- The agent can **dispatch registered tools** when the LLM requests them.
- **No outreach, no application submission, no file editing, and no arbitrary local file access** through tools.
- CLI admin access exists through the playground and `haxjobs agent` subcommands.

## Architecture

```
Agent.run()               → single-turn LLM call (used by evaluation)
Agent.run_with_tools()    → multi-turn tool loop (used by discovery, onboarding)

Registry
  ├─ TOOLS: dict[str, ToolDef]
  ├─ register(name, schema, handler, check_fn)
  ├─ get_schemas(names, exclude)
  └─ dispatch(name, args)

Tool modes (tool_modes.py)
  ├─ profile       → profile_read, profile_write, profile_schema, profile_gaps
  ├─ discovery     → discover_jobs, profile_read, web_search, fetch_page
  ├─ evaluation    → evaluate_fit, profile_read
  ├─ application   → generate_pack, profile_read
  ├─ decision      → record_decision
  ├─ admin         → db_query, profile_read, profile_schema
  ├─ outreach_future → find_contacts, draft_message (stubs)
  └─ learning_future → analyze_patterns (stub)
```

## Tool inventory

### Support tools (DONE)

| Tool | File | Description |
|---|---|---|
| `web_search` | tools_web.py | DuckDuckGo HTML search, 5 results max |
| `fetch_page` | tools_web.py | Fetch public HTTP(S) pages, SSRF-hardened, 12K char max |
| `db_query` | tools_db.py | Read-only SELECT/WITH queries, 50 row max. **Admin only.** |

### Profile tools (DONE)

| Tool | File | Description |
|---|---|---|
| `profile_read` | tools_profile.py | Dot-path or full profile read |
| `profile_write` | tools_profile.py | Scoped dot-path write, 0600 permissions, JSON auto-parse |
| `profile_schema` | tools_profile.py | Full profile JSON Schema |
| `profile_gaps` | tools_profile.py | Required fields, skill evidence, role achievements, employment gaps |

### Product tools (BUILD — implemented in plan 102)

| Tool | File | Description |
|---|---|---|
| `discover_jobs` | tools_product.py | Run ATS scrapers, promote jobs, auto-evaluate matches |
| `evaluate_fit` | tools_product.py | Score job against profile, write to evaluations table |
| `generate_pack` | tools_product.py | Create application pack for L1/L2 jobs |
| `record_decision` | tools_product.py | Record apply/maybe/save/skip/reject decision |

### Future tools (FUTURE — stubs only)

| Tool | File | Description |
|---|---|---|
| `find_contacts` | tools_product.py | Hiring manager/team lead search |
| `draft_message` | tools_product.py | Template-fill outreach message |
| `analyze_patterns` | tools_product.py | Decision-pattern analysis for learning engine |

Product tools currently return `{"ok": false, "code": "not_implemented"}`. Future tools return `{"ok": false, "code": "future_tool"}`. See `docs/TOOL_REGISTRY_SPEC.md` for the full contract.

## Modes

`Agent(tool_mode="evaluation")` auto-sets `tools` to the evaluation mode list. This keeps the LLM from seeing irrelevant tools. Explicit `tools=` overrides `tool_mode`.

## Safety model

- `db_query` is admin mode only — never available in product workflows.
- `profile_write` is profile mode only — never available during evaluation or discovery.
- `fetch_page` validates URLs before fetching and on every redirect (SSRF-hardened).
- Outreach tools require explicit user approval — the harness cannot send messages.
- `generate_pack` never creates per-job CVs — only references reusable CV variants.
- No tool writes to the DB or profile without logging to `activity_log`.
