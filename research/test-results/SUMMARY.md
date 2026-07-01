# Plan 028 test results summary — 5 shipping adapters

## Verdict

Three of five target adapters are confirmed working headlessly with real HaxJobs evaluation. Plan 029 build order:

1. **Codex CLI** (`codex exec --output-schema`) — primary. Schema-enforced valid JSON eliminates all parsing fragility. Score 62, Level 2 on Faculty Platform Engineer role. Same score as Hermes.

2. **Hermes CLI** (`hermes -z`) — primary fallback. Clean JSON output, exit 0. Score 62, Level 2 on the same role. Already the default HaxJobs evaluator.

3. **Pi headless** (`pi -p --mode json --no-tools`) — secondary fallback. Works but output is JSONL event stream requiring parser. Score 60, Level 2. Different model (deepseek-v4-pro) produced slightly lower but consistent score.

4. **Claude Code** — deferred. API reports "Credit balance is too low." When funded, `claude -p --output-format json --permission-mode bypassPermissions` is the invocation. Native Python SDK (`claude_agent_sdk`) also available.

5. **Gemini CLI** — deferred. `IneligibleTierError`: free tier deprecated, requires Antigravity migration. `gemini -p -o json -y` is the correct headless invocation when auth is resolved.

## Real evaluation

- Job: `Software Engineer - Platform` at `faculty` (id=633)
- Prompt: 11,998 chars, saved in `eval_prompt.txt`
- All three working agents evaluated the same job:
  - Hermes: 62 L2 ("Quick Apply")
  - Codex: 62 L2 ("Quick Apply")
  - Pi: 60 L2 (via deepseek-v4-pro)

## Model switching proof

Availability fallback proven (no live rate limits occurred):
- Hermes CLI: config default model, exit 0
- Codex CLI: config default model, exit 0
- Pi headless: explicit `deepseek/deepseek-v4-pro`, exit 0

All three paths are independently operational. Rate-limit fallback logic is implementable in Plan 029.

## Working paths (verified)

| Agent | Smoke | Real eval | Validation |
|---|---|---|---|
| Hermes CLI | ✅ `{"status":"ok","agent":"hermes","model":"default"}` | ✅ exit 0 | VALID |
| Codex CLI | ✅ `{"status":"ok","agent":"codex","model":"default"}` | ✅ exit 0, schema-valid | VALID |
| Pi headless | ✅ `{"status":"ok","agent":"pi","model":"deepseek"}` in stream | ✅ exit 0 | VALID |

## Blocked paths

| Agent | Blocker | Resolution |
|---|---|---|
| Claude Code | Credit balance too low | Add Anthropic credit |
| Gemini CLI | Free tier deprecated | Migrate to Antigravity |

## Public-release notes

- Primary adapter: `codex exec --output-schema`. Users need Codex installed with auth.
- Fallback adapter: `hermes -z`. Users need Hermes installed with configured provider.
- Backup fallback: `pi -p --mode json --no-tools`. Users need Pi installed.
- All adapters use `shutil.which()` for binary discovery.
- Model selection must be configurable in `haxjobs.toml`.
- Claude Code and Gemini CLI are documented but optional — users provide their own auth.
