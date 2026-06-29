# Plan 027: Research agent internals and pluggable points for evaluation

> **Executor**: This plan is written for **GPT 5.5 via Hermes** (or any agent with web search capability). The executor must follow every search instruction, analyze results, and produce the specified deliverables.
>
> **Drift check**: `git log --oneline -1 -- evaluate/agents/` — confirms current state. HEAD expected at or after commit `fa70a36` (compat shim cleanup).

## Status

- **Priority**: P1
- **Effort**: L (research-heavy, 2-4 hours with web access)
- **Risk**: LOW (no code changes, read-only research)
- **Depends on**: None
- **Category**: research
- **Planned at**: commit `421789b`, 2026-06-29

## Why this matters

HaxJobs currently has ONE evaluation agent adapter: `evaluate/agents/hermes.py`. It shells out to `hermes chat --yolo -Q -q <prompt>`. When Hermes is rate-limited, the entire evaluation pipeline is dead.

The goal is a pluggable multi-agent evaluation system where the user configures their preferred agent in `haxjobs.toml`:

```toml
[evaluation]
agent = "hermes"  # or "codex", "gemini", "claude", "pi", "open_claw"
```

But "agent" means different things for different tools. Some are CLI binaries, some are SDKs, some are skills/extensions running inside a host agent. Before implementing adapters, we need to KNOW what the pluggable point is for each.

## What you will research

For EACH agent in the list below, answer these questions:

1. **What is it?** One-line description. Where is its source/docs?
2. **How do you call its LLM programmatically?** Is there a CLI? An HTTP API? An SDK? An MCP server?
3. **What is the MINIMAL invocation?** Exact command/API call that sends a prompt and returns text output. No interactivity, no tool loop — just "here's a prompt, give me the response."
4. **Does it support JSON-only output mode?** Can we force it to return valid JSON with no markdown wrapper?
5. **Local files to inspect** (if already installed): what's on disk? What version?
6. **Integration difficulty**: Easy (subprocess, ~30 lines), Medium (HTTP API auth, ~60 lines), Hard (needs custom plugin/skill), Very Hard (no documented API).
7. **Go/No-go**: Should we build an adapter for this agent? Rationale.

### Agent list

| # | Agent | Why it matters |
|---|-------|---------------|
| A | **Hermes** | Already used. We know it works but need to document rate limits, retry behavior, and whether there's a better call pattern than `hermes chat --yolo -Q -q`. |
| B | **Codex (OpenAI)** | `codex exec` exists. Needs research: does it have a headless mode? Can it do one-shot completions? |
| C | **Gemini CLI (Google)** | Official Google CLI. Research: does `gemini chat` accept piped prompts? JSON mode? |
| D | **Claude Code (Anthropic)** | `claude -p <prompt>` for headless. Research: API key requirements, token limits, JSON mode. |
| E | **Pi Coding Agent** | We're inside it. Research: extension system (TypeScript), skill system (Markdown), SDK (`createAgentSession()`). Question: can we call Pi's LLM from a Pi extension without spawning a subprocess? |
| F | **Open Claw** | Described as an open-source agent harness. Research: what is it? CLI? SDK? MCP? |
| G | **Mimo Code** | Referenced by user. Research: what is it? How to call it? |
| H | **Open Code** | Referenced by user. Research: what is it? How to call it? |
| I | **Claude API (direct)** | Anthropic Messages API. Not an "agent" but a direct API call — useful as a reliable fallback. Research: API key requirements, token costs, JSON mode. |
| J | **Gemini API (direct)** | Google Gemini API. Same rationale as direct Claude API. |

## Search instructions

For each agent, run these searches and summarize findings. Use the exact queries below — they're designed to find programmatic integration points, not marketing pages.

### Hermes (agent A)
Local files already installed at `/home/hax/.hermes/hermes-agent/`. The executor should:
- Read `/home/hax/.hermes/hermes-agent/hermes_cli/main.py` function `cmd_chat` (line ~2205) and the argument parser for `--yolo`, `-Q`, `-q`, `--no-tui`, `--print`, `--json` flags
- Read `/home/hax/.hermes/hermes-agent/config.yaml` to understand provider/model config
- Search: `hermes agent headless mode one-shot prompt API` and `hermes agent --print flag documentation`

### Codex (agent B)
- Search: `openai codex CLI headless mode non-interactive prompt` and `codex exec --json documentation`
- Search: `codex CLI one-shot completion without TUI`

### Gemini CLI (agent C)
- Search: `google gemini CLI headless mode piped prompt` and `gemini chat --help flags json mode`
- Search: `google-gemini CLI npm package programmatic usage`

### Claude Code (agent D)
- Search: `claude code cli -p flag non-interactive headless` and `claude code --print --json mode documentation`
- Search: `claude code API key configuration environment variable`

### Pi Coding Agent (agent E)
- Local files: Read `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md` (especially "Custom Tools" and "Event Interception" sections)
- Read `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/sdk.md` (especially `createAgentSession` and `session.prompt()`)
- Read `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/docs/skills.md`
- Read `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/examples/sdk/` — especially `01-minimal.ts`, `05-tools.ts`, `06-extensions.ts`
- Search: `pi coding agent extension registerTool custom tool LLM invoke`
- Search: `pi coding agent SDK session.prompt programmatic`
- **Key question**: Can a Pi extension call the LLM directly (no subprocess)? Check if `ctx` or `pi` API exposes a `callModel()` or `prompt()` method. If not, can we use the Pi SDK's `createAgentSession()` from inside an extension?

### Open Claw (agent F)
- Search: `open claw agent github` and `open claw agent CLI API`
- Search: `open claw agent headless mode programmatic`

### Mimo Code (agent G)
- Search: `mimo code agent github` and `mimo code agent CLI`
- Search: `mimo code agent API programmatic usage`

### Open Code (agent H)
- Search: `open code agent github CLI` and `open code agent headless`
- Search: `open code agent programmatic API`

### Direct APIs (agents I, J)
These don't need web search — they're well-documented REST APIs:
- **Claude API**: `POST https://api.anthropic.com/v1/messages` with `x-api-key` header. JSON mode available via tool_use or structured output. ~$3/MTok input, ~$15/MTok output (Sonnet). Research: exact JSON-mode prompt format, token limits.
- **Gemini API**: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` with API key. JSON mode via `response_mime_type: "application/json"`. Research: free tier limits, exact API format.

## Local file analysis (do this FIRST, no web search needed)

Before searching the web, analyze what's already installed:

```bash
# Hermes internals
cat /home/hax/.hermes/hermes-agent/hermes_cli/main.py | grep -A30 "def cmd_chat"
cat /home/hax/.hermes/hermes-agent/config.yaml

# Pi internals
ls /home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/

# What CLI agents are on PATH?
which codex gemini claude 2>/dev/null
codex --help 2>&1 | head -40 || echo "(not installed)"
gemini --help 2>&1 | head -40 || echo "(not installed)"
claude --help 2>&1 | head -40 || echo "(not installed)"
```

## Deliverables

Create a file `research/agent-integration-points.md` with this structure:

```markdown
# Agent Integration Points — Research Report

Date: 2026-06-29
Generated by: Plan 027

## Summary table

| Agent | Type | Integration | Difficulty | JSON mode | Go? |
|-------|------|-------------|------------|-----------|-----|
| Hermes | CLI subprocess | `hermes chat --yolo -Q -q` | Easy | Prompt-only | YES |
| Codex | ... | ... | ... | ... | ... |

## Per-agent analysis

### Hermes
**What**: ...
**Minimal invocation**: `hermes chat --yolo -Q -q <prompt>`
**JSON mode**: Not native. Must prompt-engineer "return ONLY valid JSON."
**Rate limits**: ...
**Local state**: Installed at /home/hax/.hermes/hermes-agent/, config at config.yaml
**Go/No-go**: YES — already working. Issues: rate limiting, no native JSON mode.

### Codex
...

### Pi Coding Agent
**What**: TypeScript-based agent harness with extension/skill system
**Integration path A (Pi skill)**:
  - HaxJobs as a Pi skill in ~/.pi/agent/skills/haxjobs/SKILL.md
  - When user says "evaluate this job", Pi loads the skill and evaluates inline
  - Pro: No subprocess, uses Pi's own LLM
  - Con: Only works when user is actively using Pi
**Integration path B (Pi extension)**:
  - TypeScript extension registering haxjobs_discover, haxjobs_evaluate tools
  - Tools use pi.registerTool() with execute() calling Python subprocess
  - Pro: Can trigger pipeline from within Pi
  - Con: Still needs a CLI agent for the actual LLM call, or needs SDK session.prompt()
**Integration path C (Pi SDK)**:
  - External script uses createAgentSession() + session.prompt() to call Pi
  - Pro: Programmatic, could work from cron
  - Con: Spawns a new Pi process, not running inside existing session
**Recommendation**: Path A (skill) for interactive use. Path B+C for cron need more investigation.

...
```

## STOP conditions

- If an agent has NO documented programmatic API and NO CLI, mark it "No-go — no integration surface found" and move on.
- If search results are contradictory, note the contradiction and pick the most authoritative source (official docs > GitHub README > blog posts).
- If an agent's integration requires authentication that can't be automated (browser login, OAuth dance with redirect), mark it "No-go — authentication requires human interaction."
- Do NOT install any software. Only analyze what's already on disk or documented online.

## Done criteria

- [ ] `research/agent-integration-points.md` exists with analysis of all 10 agents (A through J)
- [ ] Every agent has a clear Go/No-go decision with rationale
- [ ] Local files (Hermes config, Pi docs) have been read and summarized
- [ ] CLI agents on PATH have been checked and their `--help` output documented
- [ ] Direct API agents (Claude, Gemini) have documented endpoint, auth, and cost
- [ ] The report clearly separates: "works today" (Hermes), "easy to add" (subprocess CLIs), "needs plugin/skill" (Pi), "unknown/risky" (Open Claw, Mimo, Open Code)
- [ ] `plans/README.md` updated with Plan 027 status

## Maintenance notes

- This is a living document. When a new agent version ships, update its entry.
- The "Go/No-go" column feeds directly into Plan 028 (testing) and Plan 029 (implementation).
- Agents marked "No-go" should still be documented with rationale — they may become viable later.
