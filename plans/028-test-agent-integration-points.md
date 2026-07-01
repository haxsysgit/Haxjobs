# Plan 028: Test agent integration points for HaxJobs evaluator adapters

> **Executor**: This is a validation plan, not production adapter implementation. Your job is to prove which agent integration paths actually work on this machine, save raw evidence, and recommend the build order for Plan 029. Do not edit production source code.

## Status

- **Priority**: P1
- **Effort**: M (2-4 hours, mostly waiting for agent responses)
- **Risk**: MED (auth/rate limits may block live tests)
- **Depends on**: Plan 027 completed research in `adapter_research/`
- **Category**: testing / integration validation
- **Planned at**: commit `499d9ee`, 2026-07-01

## Drift check

Run before doing any work:

```bash
test -d adapter_research \
  && test -f adapter_research/00_summary.md \
  && test -f adapter_research/01_hermes_agent.md \
  && test -f adapter_research/02_codex.md \
  && test -f adapter_research/03_claude_code.md \
  && test -d adapter_research/hermes_sources \
  && find adapter_research/hermes_sources -type f | wc -l
```

Expected: command exits 0 and prints a non-zero source count. If `adapter_research/` is missing, STOP and report: Plan 027 artifacts are not available in this worktree.

## Why this matters

Plan 027 identified possible ways for HaxJobs to call coding agents. Plan 028 proves which ones are real enough for production/public release, not just working on Arinze's current machine:

1. Can HaxJobs discover the agent via PATH/config instead of hardcoded `/home/hax/...` paths?
2. Can HaxJobs call the agent headlessly without an interactive user?
3. Can it select a model explicitly?
4. Can it return clean JSON or schema-constrained output?
5. What does failure look like when auth, model, quota, or rate limits break?
6. What portable install/config/env requirements must Plan 029 document for public users?
7. Which adapters should Plan 029 build first?

The output of this plan is `research/test-results/`, not code under `evaluate/`. Treat local absolute paths as evidence only; production adapter recommendations must use `shutil.which()`, env vars, `Path.home()`, or documented config discovery.

## Current research facts to use

Use `adapter_research/` as the source of truth. Current known local tools from Plan 027 are examples, not production assumptions:

- Hermes: local binary may be `hermes`; native source may live under `Path.home() / ".hermes/hermes-agent"`; native Python entry point found in `agent/oneshot.py` as `run_oneshot()`.
- Claude Code: binary may be `claude`; has `claude -p` CLI and documented `claude_agent_sdk` Python SDK. SDK may or may not be installed locally.
- Codex: binary may be `codex`; version 0.139.0 locally; `codex exec` supports `--output-schema`, `--json`, `--model`, `--ephemeral`, `--skip-git-repo-check`, and `--output-last-message`.
- Pi: binary may be `pi`; supports headless one-shot `pi -p <prompt> --mode json --no-tools --model <model>`.
- Gemini CLI: binary may be `gemini`; supports `-p/--prompt`, `-m/--model`, and `-o/--output-format text|json|stream-json`.
- OpenCode: binary may be `opencode`; supports `opencode run --format json -m provider/model`.
- Cursor: binary may be `cursor`; use `cursor agent -p --output-format json --mode plan --trust`, not top-level `cursor --help`.
- GitHub Copilot CLI: binary may be `copilot`; supports `-p/--prompt`, `--model`, `--output-format json`, `--allow-all-tools`, and `--yolo`.
- Cline: not installed locally. Do not test it unless `command -v cline` succeeds.

For every agent, record both local evidence and the portable discovery rule Plan 029 should implement.

## In scope

You may create only:

```text
research/test-results/
  SUMMARY.md
  test-matrix.md
  portability.md         # public-release discovery/config notes per adapter
  _scripts/              # optional tiny helper scripts for repeatable smoke tests
  <agent>/               # raw stdout/stderr/metadata per test
```

You may read:

- `adapter_research/**`
- `evaluate/common.py`
- `db/schema.py`
- `haxjobs_config.py`
- local agent help/config files, but never print secrets

## Out of scope

Do not edit:

- `evaluate/**`
- `db/**`
- `discovery/**`
- `haxjobs.toml`
- `.env` or any auth/config file containing secrets
- `plans/README.md` (the reviewer maintains the index)

Do not install dependencies. If an SDK is missing, mark that test `BLOCKED: package not installed` and continue with that agent's CLI mode.

## Test prompt and schema

Use this tiny smoke prompt for every agent:

```text
Return only valid JSON matching this object: {"status":"ok","agent":"<agent>","model":"<model>"}. Do not include markdown.
```

Use this real-evaluation target for at least one working agent:

```bash
PYTHONPATH=. python3 - <<'PY'
from db.schema import init, get_db
from evaluate.common import build_prompt

init()
conn = get_db()
row = conn.execute("""
    SELECT * FROM jobs
    WHERE length(coalesce(description, '')) > 500
    ORDER BY id DESC
    LIMIT 1
""").fetchone()
conn.close()
if not row:
    raise SystemExit('STOP: no job with a real JD found')
prompt = build_prompt(dict(row))
open('research/test-results/eval_prompt.txt', 'w').write(prompt)
print(f"job_id={row['id']} prompt_chars={len(prompt)}")
PY
```

Expected: prints a job id and prompt length, and writes `research/test-results/eval_prompt.txt`.

The real evaluation response must contain parseable JSON with these fields:

```text
fit_score, fit_verdict, level, level_name, strongest_matches,
major_gaps, sponsorship_risk, summary, decision
```

## Required tests, in order

### 1. Inventory

Create `research/test-results/inventory.txt` with versions and availability. Use PATH discovery, not absolute paths:

```bash
set +e
for bin in hermes claude codex pi gemini opencode cursor copilot cline; do
  echo "===== $bin ====="
  if command -v "$bin" >/dev/null 2>&1; then
    echo "path=$(command -v "$bin")"
    timeout 10s "$bin" --version 2>&1 | head -20
  else
    echo "missing"
  fi
  echo
 done
```

Expected: record what is present on this machine, but do not fail the whole plan because an optional public adapter is missing.

### 2. Hermes native API

Try the native Python path first using `Path.home()`, not a hardcoded home directory:

```bash
mkdir -p research/test-results/hermes
python3 - <<'PY' > research/test-results/hermes/native_import.txt 2>&1
import sys
from pathlib import Path
repo = Path.cwd()
hermes_src = Path.home() / '.hermes' / 'hermes-agent'
print('hermes_src_exists', hermes_src.exists())
if not hermes_src.exists():
    raise SystemExit('IMPORT_BLOCKED: ~/.hermes/hermes-agent missing')
sys.path.insert(0, str(hermes_src))
from agent.oneshot import run_oneshot
print('IMPORT_OK run_oneshot', callable(run_oneshot))
PY
```

Then run one smoke call if import succeeds. Use a timeout. Save stdout/stderr to `research/test-results/hermes/native_smoke.txt`.

STOP for Hermes native only if import conflicts or hangs. Continue to Hermes CLI.

### 3. Hermes CLI fallback

Run a smoke prompt through headless Hermes (`hermes -z` if available; otherwise use the CLI mode documented in `adapter_research/01_hermes_agent.md`). Save raw output to `research/test-results/hermes/cli_smoke.txt`.

If Hermes reports rate limit / usage limit / HTTP 429 / payment required, save that output and mark Hermes live tests blocked. Continue to other agents.

### 4. Claude Code

First test SDK import only:

```bash
mkdir -p research/test-results/claude_code
python3 - <<'PY' > research/test-results/claude_code/sdk_import.txt 2>&1
try:
    import claude_agent_sdk
    print('IMPORT_OK', claude_agent_sdk.__file__)
except Exception as e:
    print('IMPORT_BLOCKED', type(e).__name__, str(e))
PY
```

Then test CLI mode with `claude -p` and JSON/schema flags if `claude --help` confirms the flags. Save raw output to `research/test-results/claude_code/cli_smoke.txt`.

If auth is missing, record the auth error. Do not print token/config contents.

### 5. Codex

Codex is high value because `--output-schema` can remove JSON parsing fragility.

Create a small schema file under `research/test-results/codex/eval_schema.json`, then run:

```bash
mkdir -p research/test-results/codex
codex exec \
  --skip-git-repo-check \
  --ephemeral \
  --sandbox read-only \
  --output-schema research/test-results/codex/eval_schema.json \
  --output-last-message research/test-results/codex/smoke_last_message.json \
  'Return {"status":"ok","agent":"codex","model":"default"}' \
  > research/test-results/codex/smoke_stdout.jsonl \
  2> research/test-results/codex/smoke_stderr.txt
```

If auth/rate limit blocks it, save the failure and continue.

### 6. Pi headless

Run Pi in no-tools JSON mode:

```bash
mkdir -p research/test-results/pi
pi -p 'Return only JSON: {"status":"ok","agent":"pi"}' --mode json --no-tools \
  > research/test-results/pi/smoke_stdout.txt \
  2> research/test-results/pi/smoke_stderr.txt
```

Also test explicit model selection with the configured primary model if known from `pi --help` or existing HaxJobs Pi adapter notes. Save output separately.

### 7. Gemini CLI

Run:

```bash
mkdir -p research/test-results/gemini_cli
gemini -p 'Return only JSON: {"status":"ok","agent":"gemini"}' -o json \
  > research/test-results/gemini_cli/smoke_stdout.json \
  2> research/test-results/gemini_cli/smoke_stderr.txt
```

### 8. OpenCode

Run:

```bash
mkdir -p research/test-results/opencode
opencode run --format json 'Return only JSON: {"status":"ok","agent":"opencode"}' \
  > research/test-results/opencode/smoke_stdout.jsonl \
  2> research/test-results/opencode/smoke_stderr.txt
```

### 9. Cursor Agent

Run only the agent subcommand:

```bash
mkdir -p research/test-results/cursor
cursor agent -p 'Return only JSON: {"status":"ok","agent":"cursor"}' \
  --output-format json \
  --mode plan \
  --trust \
  > research/test-results/cursor/smoke_stdout.json \
  2> research/test-results/cursor/smoke_stderr.txt
```

### 10. Copilot CLI

Run:

```bash
mkdir -p research/test-results/copilot
copilot -p 'Return only JSON: {"status":"ok","agent":"copilot"}' \
  --output-format json \
  > research/test-results/copilot/smoke_stdout.jsonl \
  2> research/test-results/copilot/smoke_stderr.txt
```

### 11. Real evaluation

Pick the two best working paths from the smoke tests. At least one must complete a real HaxJobs evaluation using `research/test-results/eval_prompt.txt`.

Save each raw output as:

```text
research/test-results/<agent>/real_eval_stdout.txt
research/test-results/<agent>/real_eval_stderr.txt
```

Then create a tiny parser check:

```bash
PYTHONPATH=. python3 - <<'PY'
from evaluate.common import extract_json, validate_result
from pathlib import Path

for path in Path('research/test-results').glob('*/real_eval_stdout.txt'):
    raw = path.read_text(errors='replace')
    data = extract_json(raw)
    ok = False
    err = ''
    try:
        validate_result(data)
        ok = True
    except Exception as exc:
        err = f'{type(exc).__name__}: {exc}'
    print(path, 'VALID' if ok else f'INVALID {err}')
PY
```

Save this output to `research/test-results/validation.txt`.

## Model switching proof

Do not fake rate limits. Prove model switching in one of these acceptable ways:

1. Real fallback: primary model fails with rate-limit/quota/auth and a secondary model succeeds. Save both outputs.
2. Availability fallback: two explicit models both work; document that fallback can switch between them, but no live rate limit occurred.
3. Blocked: only one model/auth path works. Document the exact blocker.

For each tested agent, record whether model selection is explicit and working.

## Deliverables

Write `research/test-results/test-matrix.md`:

```markdown
| Agent | Mode | Available? | Model selection? | Smoke JSON? | Real eval? | Failure shape | Verdict |
|---|---|---|---|---|---|---|---|
```

Write `research/test-results/portability.md` with one short section per adapter:

- portable binary discovery rule (`shutil.which("codex")`, SDK import, or `Path.home()` config lookup)
- required env vars or auth state, without values
- public install requirement if missing locally
- whether cron/headless use is realistic
- any local-only assumption that Plan 029 must avoid

Write `research/test-results/SUMMARY.md` with:

1. Working adapters ranked for Plan 029.
2. Which path should be primary.
3. Which path should be fallback.
4. Which agents to defer.
5. Exact blockers for skipped tests.
6. Recommended Plan 029 build order.
7. Public-release notes: what must be config-driven, optional, or documented for users installing HaxJobs outside this machine.

Keep it direct. This is for implementation, not a docs showcase.

## STOP conditions

- If `adapter_research/` is missing, STOP.
- If a command asks for interactive login, stop that agent test and record `BLOCKED: needs login`.
- If a command tries to edit files outside `research/test-results/`, stop that agent test.
- If any output includes secrets, do not save the secret. Replace it with `[REDACTED]` in the artifact and mention only the file/credential type.
- If all agents are blocked by auth/rate limits, still write `SUMMARY.md` and `test-matrix.md` with the blockers.

## Done criteria

- [ ] `research/test-results/inventory.txt` exists.
- [ ] `research/test-results/test-matrix.md` exists and covers Hermes, Claude Code, Codex, Pi, Gemini CLI, OpenCode, Cursor, Copilot, and Cline-if-installed.
- [ ] `research/test-results/SUMMARY.md` ranks the Plan 029 adapter build order.
- [ ] `research/test-results/portability.md` documents public-release discovery/config requirements and flags local-only assumptions to avoid.
- [ ] At least one real HaxJobs evaluation prompt was attempted and raw output saved.
- [ ] At least two integration paths have smoke-test artifacts, unless auth/rate limits block them all.
- [ ] `research/test-results/validation.txt` records whether real eval output passed `evaluate.common.validate_result()`.
- [ ] No production source files changed.

## Git workflow

Commit only the `research/test-results/` artifacts in the executor worktree if the reviewer requested commits. Do not update `plans/README.md`; the reviewer maintains it.
