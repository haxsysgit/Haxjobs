# Plan 027: Research agent internals — model registry, provider dispatch, native APIs

> **Executor**: This plan is written for **GPT 5.5 via Hermes** (or any agent with web + code-reading ability). The executor must dig into source code and config files, not just CLI help text. The goal is to find the DEEPEST integration point — not "what flag do I pass" but "how do I call the model directly without spawning a subprocess."
>
> **Drift check**: `ls evaluate/agents/hermes.py` — confirms we have the existing (shallow) adapter. HEAD expected at `354429b` or later.

## Status

- **Priority**: P1
- **Effort**: L (research-heavy, 3-5 hours)
- **Risk**: LOW (read-only, no code changes)
- **Depends on**: None
- **Category**: research
- **Planned at**: commit `354429b`, 2026-06-29

## Why this matters (the real problem)

HaxJobs currently calls Hermes like this:

```python
subprocess.run(["hermes", "chat", "--yolo", "-Q", "-q", prompt])
```

This is wrong at three levels:

1. **Subprocess for the same agent**: If HaxJobs is running inside Hermes (the user's daily driver), spawning `hermes chat ...` as a subprocess means Hermes launches a SECOND Hermes process to call itself. That's wasteful, slow, and fragile.

2. **Model-blind**: The subprocess call has no idea what models Hermes has configured. When GPT 5.5 rate-limits, the pipeline dies — even though Hermes has DeepSeek configured and ready to use. A proper integration would read Hermes' config, see available models, and switch automatically.

3. **No provider intelligence**: Each agent manages its own model registry, provider routing, and rate-limit handling internally. By using subprocess, we bypass all of that and reimplement it badly in `evaluate/run.py`.

### The real integration architecture

```
HaxJobs evaluation — two modes per agent:

MODE 1: NATIVE (HaxJobs runs INSIDE the agent)
  ┌──────────────────────────────────┐
  │ Agent process (Hermes/Pi/etc.)   │
  │  ┌────────────────────────────┐  │
  │  │ HaxJobs Python package     │  │
  │  │  evaluate/agents/hermes.py │  │
  │  │    → import hermes_cli     │  │
  │  │    → call_model(prompt)    │  │  ← direct function call, no subprocess
  │  │    → read config.yaml      │  │  ← knows all available models
  │  │    → switch on rate limit  │  │  ← uses agent's own router
  │  └────────────────────────────┘  │
  └──────────────────────────────────┘

MODE 2: EXTERNAL (HaxJobs runs standalone, e.g. cron)
  ┌──────────────────────────────────┐
  │ cron/bash                        │
  │  python3 evaluate/run.py         │
  │    → read hermes config.yaml     │  ← still model-aware
  │    → pick available model        │
  │    → subprocess: hermes chat     │  ← subprocess only when necessary
  │      --model deepseek <prompt>   │
  └──────────────────────────────────┘
```

For Pi: native mode = Pi extension that registers HaxJobs tools using Pi's own LLM. External mode = Pi SDK's `createAgentSession()` (runs a Pi process, but at least it's the real API, not a CLI subprocess).

## What you will research — per agent

For EACH agent, answer these questions at TWO levels:

### Level 1 — Architecture (read source code, config files, docs)

| Question | Why it matters |
|----------|---------------|
| What language is the agent written in? | Determines if we can import it as a library (Python) or need IPC (TypeScript/Go/Rust) |
| Where is the source code (local path + GitHub URL)? | We need to read it |
| Does it have a Python API? (importable package) | Native integration = no subprocess |
| Does it have a TypeScript/JS API? | Pi case — extension integration |
| How does it manage models/providers internally? | To switch models on rate limit |
| Where is its config file? What format? | To read available models |
| Does the config list multiple models/providers? | Fallback chain |
| Is there a "send prompt, get text" function in its internal API? | The exact function we'd call |
| Does it have rate-limit detection built in? | Don't reinvent it |
| Can we detect which agent we're running inside? (env var, process check) | Auto-detect native vs external mode |

### Level 2 — Integration surface (the exact code path)

| Question | Why it matters |
|----------|---------------|
| **Native mode**: What's the exact import + function call? | `from hermes_cli.llm import complete; result = complete(prompt, model="deepseek")` |
| **Native mode**: How do we read the model list from config? | `from hermes_cli.config import load_config; models = load_config()["models"]` |
| **External mode**: What's the CLI invocation with explicit model? | `hermes chat --yolo -Q -q --model deepseek <prompt>` |
| Can we get JSON-only output? How? | `--json` flag? Prompt engineering? Structured output API? |
| What's the rate-limit error signature? | To detect and switch models |
| What env vars control auth/providers? | For .env.example and cron setup |

## Agent list — with research depth per agent

### Agent A: Hermes (PRIMARY — user's daily driver)

**Why deep research**: Hermes is the configured evaluation agent. The user has multiple models configured (GPT 5.5 + DeepSeek Pro). Rate limiting is the current blocker. We MUST find the internal API, not just the CLI.

**Local files to read thoroughly**:
```
/home/hax/.hermes/hermes-agent/hermes_cli/main.py       # Entry point, cmd_chat, arg parser
/home/hax/.hermes/hermes-agent/hermes_cli/config.py     # Config loading, model registry
/home/hax/.hermes/hermes-agent/config.yaml              # Live config — list ALL models/providers
/home/hax/.hermes/hermes-agent/hermes_cli/              # Browse ALL .py files for LLM call dispatch
/home/hax/.hermes/hermes-agent/setup.py or setup.cfg    # Package structure, entry points
```

**Search for these patterns in the codebase**:
```bash
# Find the actual LLM call function
grep -rn "def.*complete\|def.*chat\|def.*generate\|def.*call_model\|def.*run_prompt" /home/hax/.hermes/hermes-agent/hermes_cli/

# Find model/provider config loading
grep -rn "config\|provider\|model" /home/hax/.hermes/hermes-agent/hermes_cli/config.py | head -30

# Find rate limit handling
grep -rn "rate.limit\|429\|usage.limit\|retry\|backoff" /home/hax/.hermes/hermes-agent/hermes_cli/ | head -20

# Find environment detection
grep -rn "HERMES_\|env\|environ" /home/hax/.hermes/hermes-agent/hermes_cli/main.py | head -20
```

**Key questions for Hermes**:
1. Can we `from hermes_cli import ...` and call a model directly? What function?
2. Does Hermes have an internal "send one prompt, get text back" function separate from the interactive chat loop?
3. How does Hermes switch between GPT 5.5 and DeepSeek? Is it automatic on rate limit?
4. Can we read the config to know: provider priority order, rate limits, available models?
5. Is the config YAML parseable by HaxJobs (stdlib, no pip install)?
6. Is there a `HERMES_SESSION_ID` or similar env var that tells us we're inside Hermes?

**Web searches** (for GPT 5.5):
- `hermes agent github source code internal LLM API`
- `hermes agent programmatic API Python import model dispatch`
- `hermes agent config.yaml multiple providers model fallback`

### Agent B: Codex (OpenAI)

**Research depth**: Medium. Less urgent than Hermes but valuable as an alternative.

**Web searches**:
- `openai codex agent github source code`
- `codex exec Python API programmatic completion`
- `codex agent model switching provider config`

**Key questions**:
- Is Codex open-source? Where's the repo?
- Does it have an importable Python package?
- Can we call `codex.Complete.create(prompt)` or similar?
- How does it handle multiple models?

### Agent C: Gemini CLI (Google)

**Web searches**:
- `google-gemini-cli github source code npm package`
- `gemini CLI programmatic API JavaScript import`
- `gemini CLI config multiple models`

### Agent D: Claude Code (Anthropic)

**Web searches**:
- `claude code agent github source code anthropic`
- `claude code programmatic API MCP integration`
- `claude code internal API call model function`

### Agent E: Pi Coding Agent (user is INSIDE it right now)

**Local files to read thoroughly**:
```
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md
  → Sections: Custom Tools, Event Interception, ExtensionContext, ExtensionAPI
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/sdk.md
  → Sections: createAgentSession, AgentSession, session.prompt()
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/skills.md
  → Full document — skill structure, how agents load them
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/extensions/tools.ts
  → How custom tools are registered
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/01-minimal.ts
  → Minimal SDK usage
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/06-extensions.ts
  → SDK with extensions
/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/extensions/subagent/
  → Subagent spawning pattern
```

**Key questions for Pi**:
1. **Native mode (extension)**: Can a Pi extension call Pi's LLM directly? Check if `ctx` or `ExtensionAPI` exposes a `prompt()` or `callModel()` method. If not, can we use the Pi SDK's `createAgentSession()` from within an extension?
2. **Skill mode**: If we write a `haxjobs` Pi skill, when the user says "evaluate this job," Pi reads the skill instructions and does the evaluation using its own LLM — THAT is the integration. No code needed, just a well-written SKILL.md.
3. **External mode**: For cron, can we use `createAgentSession()` + `session.prompt()` as a proper API (not CLI subprocess)?
4. What env vars indicate we're running inside Pi? (`PI_SESSION_ID`?)

### Agent F: Open Claw

**Web searches**:
- `open claw agent github` 
- `open claw agent source code Python API`
- `open claw agent model registry provider`

### Agent G: Mimo Code

**Web searches**:
- `mimo code agent github`
- `mimo code agent programmatic API`

### Agent H: Open Code

**Web searches**:
- `open code agent github CLI`
- `open code agent internal API`

### Agent I: Claude API (direct Anthropic Messages API)

**No web search needed — well-documented REST API.**

**Research**: 
- Endpoint: `POST https://api.anthropic.com/v1/messages`
- Auth: `x-api-key` header
- JSON mode: Use `{"type": "json_object"}` in system prompt or structured output
- Models: `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`
- Cost: ~$3/MTok input, ~$15/MTok output (Sonnet), ~$0.25/$1.25 (Haiku)
- Rate limits: Vary by tier, typically 50-100 req/min
- **Integration**: `urllib.request` (stdlib) — no dependencies needed
- **Native vs external**: Always "external" — it's a REST API, not an agent. But it's the most reliable fallback because it doesn't depend on any agent binary being installed or functioning.

### Agent J: Gemini API (direct Google Generative Language API)

**No web search needed.**

**Research**:
- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Auth: `?key=` query parameter
- JSON mode: `response_mime_type: "application/json"` in generation config
- Models: `gemini-2.5-flash`, `gemini-2.5-pro`
- Cost: Free tier available (15 RPM, 1500 RPD for flash)
- **Integration**: `urllib.request` (stdlib)
- **Native vs external**: Always "external" — REST API

## Research methodology

### Phase 1: Local file analysis (do this first, needs no web search)

```bash
# Hermes: map the internal API surface
find /home/hax/.hermes/hermes-agent -name "*.py" | xargs grep -l "def.*chat\|def.*complete\|def.*generate\|class.*Provider\|class.*Model" | head -10

# Hermes: find the model registry
grep -rn "models\|providers\|config" /home/hax/.hermes/hermes-agent/hermes_cli/config.py | head -30

# Hermes: find the LLM call dispatch
grep -rn "openai\|anthropic\|google\|deepseek" /home/hax/.hermes/hermes-agent/hermes_cli/ | head -20

# Hermes: read the live config
cat /home/hax/.hermes/hermes-agent/config.yaml

# Pi: read extension API surface
grep -n "registerTool\|callModel\|prompt\|invoke\|custom.tool" /home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md | head -20

# Pi: read SDK prompt API
grep -n "session.prompt\|createAgentSession\|AgentSession" /home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/sdk.md | head -20

# What agents are on PATH?
for bin in codex gemini claude; do
  path=$(which $bin 2>/dev/null) && echo "$bin: $path" || echo "$bin: NOT INSTALLED"
done
```

### Phase 2: Deep code reading

For Hermes (highest priority), trace the full call path:
1. `cmd_chat` in main.py → what does it call?
2. Find the "agent loop" — where does it call the LLM?
3. Find the "provider dispatch" — where does it choose OpenAI vs Anthropic vs DeepSeek?
4. Find the "one-shot completion" path — is there a `--print` or `--no-tui` code path that returns text and exits?

### Phase 3: Web search (for agents without local installs)

For each of agents B-H, run the searches listed above. For each:
1. Find the GitHub repo
2. Find the README — look for "API", "programmatic", "headless", "library usage"
3. Look for example code showing direct function calls (not CLI)
4. Look for config/toml/yaml showing model/provider configuration
5. If no programmatic API exists, document what the CLI surface looks like

## Deliverables

Create `research/agent-integration-points.md` with this structure:

```markdown
# Agent Integration Points — Deep Research Report

Date: 2026-06-29
Generated by: Plan 027

## Summary: Native vs External integration per agent

| Agent | Native mode (inside agent) | External mode (standalone) | Model-aware? | Priority |
|-------|---------------------------|---------------------------|-------------|----------|
| Hermes | `from hermes_cli.xxx import yyy; yyy(prompt, model="deepseek")` | `hermes chat --yolo -Q -q --model deepseek <prompt>` | YES — read config.yaml | P0 |
| Codex | ? | ? | ? | P2 |
| ... | ... | ... | ... | ... |

## Per-agent deep analysis

### Hermes (P0 — primary agent)

#### Architecture
- Written in: Python
- Source: `/home/hax/.hermes/hermes-agent/`
- Config: `config.yaml` (YAML) — parseable with stdlib? (Python 3.11+ has no yaml in stdlib — need to check if PyYAML is in venv, or write a minimal YAML parser)
- Python API: Yes — `hermes_cli` package
- Available models (from config): [list from config.yaml]
- Provider priority: [from config]

#### Internal API surface
- Function to call: `hermes_cli.xxx.yyy(prompt, model=None)` — [exact import path]
- How it handles rate limits: [from code]
- How it switches providers: [from code]
- Environment detection: `HERMES_SESSION_ID` env var? [yes/no]

#### Native mode integration
```python
# Exact code for calling Hermes' model directly
from hermes_cli.xxx import yyy
result = yyy(prompt, model="deepseek", max_tokens=4096, json_mode=True)
```

#### External mode integration
```bash
hermes chat --yolo -Q -q --model deepseek --json <prompt>
```

#### Rate-limit handling
- Error signature: [string to grep for]
- Fallback model: [from config]
- Automatic or manual switch: [from code]

### Codex
...

### Pi Coding Agent

#### Architecture
- Written in: TypeScript
- Source: `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/`
- Extension API: Yes — `pi.registerTool()`
- Skill system: Yes — `SKILL.md` with progressive disclosure
- SDK: Yes — `createAgentSession()`

#### Native mode (Pi extension)
```typescript
// Can we do this?
export default function(pi: ExtensionAPI) {
  pi.registerTool({
    name: "haxjobs_evaluate",
    execute: async (input, ctx) => {
      // Option A: Pi's LLM evaluates directly via the agent's own reasoning
      // This would require Pi to expose a "call LLM" method on ctx
      const result = await ctx.prompt?.(buildEvaluationPrompt(input));
      // OR
      // Option B: We use the SDK to spawn a sub-agent session
      const { session } = await createAgentSession({...});
      await session.prompt(buildEvaluationPrompt(input));
    }
  });
}
```
**Does `ctx` have a `prompt()` or `callModel()` method?** [YES/NO — from reading extensions.md]

#### Skill mode (Pi skill)
- How it works: Pi loads SKILL.md, adds context to system prompt, agent evaluates inline
- Pro: Zero code, uses Pi's LLM naturally
- Con: Only works interactively (user says "evaluate this job"), not for cron

### Claude API (direct)
- Always external (REST API)
- Endpoint: ...
- Auth: ...
- JSON mode: ...
- Models/cost: ...
- Integration: stdlib urllib.request, ~40 lines

### Gemini API (direct)
- Always external (REST API)
- ...
```

## STOP conditions

- If Hermes has NO importable Python API (everything is in `__main__` block or CLI-only), document that. External mode (subprocess) is then our only option, but we should still read config for model awareness.
- If an agent's source is not open-source and not installed, mark "No-go — cannot read internals, CLI-only."
- If an agent requires a pip/npm install that conflicts with HaxJobs environment, note it.
- Do NOT install any software. Only analyze what's on disk or documented.

## Done criteria

- [ ] `research/agent-integration-points.md` exists with deep analysis of ALL 10 agents
- [ ] For Hermes specifically: exact internal Python API function found and documented (or confirmed CLI-only)
- [ ] Hermes config.yaml fully parsed — all models, providers, priorities listed
- [ ] For Pi: definitive answer on whether `ctx.prompt()` or equivalent exists in extension API
- [ ] Every agent has BOTH native and external mode documented (or "native: N/A" if only CLI)
- [ ] Clear separation: which agents support model-aware integration vs blind CLI calls
- [ ] Summary table with priority ordering for Plan 028 (testing) and Plan 029 (implementation)
- [ ] `plans/README.md` updated
