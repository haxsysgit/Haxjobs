# Plan 028: Test agent integration points — practical validation

> **Executor**: This plan tests the integration points identified in Plan 027. It requires Plan 027's research report at `research/agent-integration-points.md`. Every test is concrete: run a command, check the output, record the result.
>
> **Drift check**: `test -f research/agent-integration-points.md && wc -l research/agent-integration-points.md` — confirms Plan 027 research exists.

## Status

- **Priority**: P1
- **Effort**: M (3-5 hours, mostly waiting for API/CLI responses)
- **Risk**: MED (some agents may be uninstalled or rate-limited)
- **Depends on**: Plan 027 (research report)
- **Category**: testing
- **Planned at**: commit `421789b`, 2026-06-29

## Why this matters

Plan 027 told us WHAT each agent can do. Plan 028 proves it works. A research report saying "Claude Code supports `claude -p`" is theory. Running `claude -p "Return {\"ok\":true}"` and getting `{"ok":true}` back is proof.

We test TWO things per agent:

1. **Connectivity**: Can we invoke it at all?
2. **Evaluation quality**: Using a real job from the DB, does it produce a valid evaluation JSON?

## What you will test

For each agent marked "Go" in Plan 027's research report, run these tests:

### Test 1: Smoke test (5 min per agent)

Send a trivial prompt and verify the agent responds with valid JSON.

```
Prompt: "Return exactly this JSON and nothing else, no markdown, no backticks: {\"status\":\"ok\",\"agent\":\"<agent_name>\",\"timestamp\":\"<current UTC ISO timestamp>\"}"
```

**Expected**: Response parses as valid JSON with status="ok".

**Record**: latency (seconds), whether JSON was clean or wrapped in markdown.

### Test 2: Real evaluation (5-15 min per agent)

Pick one job from the DB that has a decent JD (>500 chars) and has been evaluated before (so we can compare scores). Run the FULL evaluation prompt that HaxJobs generates (from `evaluate/common.py` `build_prompt()`).

```
# Generate the prompt
PYTHONPATH=. python3 -c "
from evaluate.common import build_prompt
from db.schema import init, get_db
init()
conn = get_db()
job = conn.execute('SELECT * FROM jobs WHERE id=20').fetchone()
conn.close()
if job:
    prompt = build_prompt(dict(job))
    print(prompt)
" > /tmp/test_eval_prompt.txt

# Send it to the agent
cat /tmp/test_eval_prompt.txt | <agent_invocation>
```

**Expected**: Response contains valid evaluation JSON with fields: `fit_score`, `fit_verdict`, `level`, `level_name`, `strongest_matches`, `major_gaps`, `sponsorship_risk`, `summary`, `decision`.

**Record**: All fields present? Score reasonable? JSON clean? Latency?

### Test 3: Retry behavior (for CLI agents only)

Send a prompt that asks for JSON, but deliberately. Verify the retry logic from `evaluate/run.py` works (extract JSON → validate → retry on issues).

### Agents to test (in priority order)

| Priority | Agent | Why this order |
|----------|-------|---------------|
| 1 | **Hermes** | Already works. Test with rate-limit awareness. Baseline for comparison. |
| 2 | **Codex** | If installed, highest-value alternative (OpenAI quality). |
| 3 | **Claude Code** | If installed. Claude quality + headless flag. |
| 4 | **Gemini CLI** | If installed. Free tier, good fallback. |
| 5 | **Claude API (direct)** | Doesn't need CLI install. HTTP request with curl. Reliable baseline. |
| 6 | **Gemini API (direct)** | Doesn't need CLI install. Free tier. |
| 7 | **Pi (skill approach)** | Different category — test by writing a minimal Pi skill and verifying the agent can follow evaluation instructions inline. |

Agents marked "No-go" in Plan 027 are skipped.

## Test artifacts

For each test, save the raw output to `research/test-results/<agent>/`:

```
research/test-results/
├── hermes/
│   ├── smoke_test.txt
│   ├── eval_test.txt
│   └── RESULTS.md
├── codex/
│   └── ...
└── SUMMARY.md
```

Each `RESULTS.md` contains:

```markdown
# <Agent> — Integration Test Results

## Connectivity
- [x] Smoke test passed (2.3s latency)
- [ ] Smoke test failed — reason

## Evaluation quality
- JSON valid: yes/no
- Fields present: fit_score, fit_verdict, level, level_name, strongest_matches, major_gaps, sponsorship_risk, summary, decision — yes/no each
- Score comparison: this agent scored <N> vs Hermes baseline of <M>
- Notes: ...

## Verdict
- [ ] READY — can build adapter
- [ ] NEEDS WORK — issue: ...
- [ ] BLOCKED — reason: ...
```

## Implementation notes for Plan 029

For each agent that passes testing, document the EXACT adapter pattern:

```
Agent: codex
Adapter file: evaluate/agents/codex.py
Invocation: ["codex", "exec", "--json", prompt]
Timeout: 180s
JSON extraction: Look for {...} in output, strip markdown fences
Auth: CODEX_API_KEY env var (automatic)
Retry: 2 retries, 5s backoff
Notes: --json flag returns clean JSON without markdown
```

For agents that partially work, document what's needed:
```
Agent: gemini
Issue: Returns JSON wrapped in ```json``` fences 50% of the time
Fix: Strip fences in extract_json() or add "no backticks" to prompt
```

## Verification commands

```bash
# Hermes (baseline)
hermes chat --yolo -Q -q 'Return exactly: {"status":"ok"}' 2>&1

# Codex (if installed)
codex exec --json 'Return exactly: {"status":"ok"}' 2>&1 | head -20

# Claude Code (if installed)
claude -p 'Return exactly: {"status":"ok"}' 2>&1

# Gemini CLI (if installed)
echo 'Return exactly: {"status":"ok"}' | gemini chat 2>&1

# Claude API (direct)
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":100,"messages":[{"role":"user","content":"Return exactly: {\"status\":\"ok\"}"}]}' | jq .

# Gemini API (direct)
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Return exactly: {\"status\":\"ok\"}"}]}]}' | jq .
```

## Deliverables

- `research/test-results/SUMMARY.md` — table of every agent tested, verdict, latency
- Per-agent `RESULTS.md` files with detailed notes
- Raw output saved for each test
- Updated `plans/README.md` with Plan 028 status
- A clear list of agents that are "READY for Plan 029 implementation" ordered by priority

## STOP conditions

- If an agent is not installed, try `which <agent>` and `pip install` / `npm install` as documented in Plan 027. If install fails, skip — mark "BLOCKED: not installed."
- If an agent requires an API key that's not configured, skip — mark "BLOCKED: needs API key."
- If an agent consistently returns non-JSON output even with explicit prompting, mark "NEEDS WORK: non-compliant JSON."
- If an agent takes >5 minutes, kill it and mark "BLOCKED: timeout."
- Do NOT commit API keys to the repo. Use env vars.

## Done criteria

- [ ] At least 3 agents tested (Hermes + 2 others, or Hermes + 1 CLI + 1 API)
- [ ] `research/test-results/SUMMARY.md` with verdict table
- [ ] Every agent tested has raw output saved
- [ ] For each READY agent: exact adapter pattern documented for Plan 029
- [ ] For each BLOCKED/NEEDS_WORK agent: specific reason and what would unblock it
- [ ] `plans/README.md` updated
