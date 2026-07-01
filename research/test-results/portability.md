# Plan 028 portability notes — 5 shipping adapters

## Hermes
- Discovery: `shutil.which("hermes")` for CLI; optional native source at `Path.home() / ".hermes/hermes-agent"`.
- Auth: user-managed Hermes config/auth at `~/.hermes/config.yaml` + `~/.hermes/auth.json`.
- Cron/headless: `hermes -z` works. Native import resolves but live call fails on missing `openai` module dependency.
- Model: `hermes -z` uses config default; explicit `--model` flag available.
- Public note: users must have Hermes installed and configured with a working provider.

## Codex
- Discovery: `shutil.which("codex")`.
- Auth: user must have Codex OAuth at `~/.codex/auth.json` or `CODEX_API_KEY` env var. API key recommended for cron.
- Cron/headless: `codex exec --skip-git-repo-check --ephemeral --sandbox read-only --output-schema <schema> --output-last-message <file>` is the strongest headless mode of all tested agents.
- Schema enforcement: `--output-schema` guarantees valid JSON matching the provided schema. No parsing fragility.
- Public note: `codex exec --output-schema` is the recommended primary evaluation path.

## Pi
- Discovery: `shutil.which("pi")`.
- Auth: user-managed Pi providers at `~/.pi/agent/auth.json`.
- Cron/headless: `pi -p <prompt> --mode json --no-tools --model <model>` works but output is JSONL event stream.
- Output format: JSONL with `type`, `message`, `assistantMessageEvent` fields. Final assistant text is in `message_end` or `message_update` events with `content[].type == "text"`. Output may duplicate the final response.
- Model: explicit `--model` flag tested with `deepseek/deepseek-v4-pro`.
- Public note: adapter must parse JSONL event stream to extract final assistant text.

## Claude Code
- Discovery: `shutil.which("claude")`.
- Auth: Anthropic API key at `~/.claude/config.json` or OAuth at `~/.claude/.credentials.json`. Credit balance required.
- Cron/headless: `claude -p --output-format json --permission-mode bypassPermissions` is the correct invocation.
- BLOCKED locally: credit balance too low. When funded, this is one of the strongest adapters — native Python SDK, structured output, model fallback.
- Public note: requires active Anthropic account with credit. Native Python SDK is `claude_agent_sdk`.

## Gemini CLI
- Discovery: `shutil.which("gemini")`.
- Auth: Google OAuth. Free tier deprecated — requires migration to Antigravity suite.
- Cron/headless: `gemini -p <prompt> -o json -y` is the correct invocation.
- BLOCKED locally: `IneligibleTierError` — free tier no longer supported.
- Public note: users must have an eligible Gemini plan. The `-o json` flag provides structured JSON output.
