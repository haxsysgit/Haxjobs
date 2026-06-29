# Plan 028: Test agent integration — native APIs, model switching, real evaluation

> **Executor**: This plan tests the integration points found in Plan 027. The key difference from the shallow approach: we test NATIVE integration (direct function calls) first, then external (subprocess/API) as fallback. We also test model switching and rate-limit recovery.
>
> **Drift check**: `test -f research/agent-integration-points.md && grep -c "### " research/agent-integration-points.md` — confirms Plan 027 research exists with per-agent sections.

## Status

- **Priority**: P1
- **Effort**: M (3-5 hours, mostly waiting for model responses)
- **Risk**: MED (rate limits may block live tests; native APIs may not exist)
- **Depends on**: Plan 027 (research report at `research/agent-integration-points.md`)
- **Category**: testing
- **Planned at**: commit `354429b`, 2026-06-29

## Why this matters

Plan 027 told us WHAT the deep integration points are. Plan 028 proves they work. The testing is ordered by priority:

1. **Hermes native API** (P0) — the user's daily driver, most important
2. **Model switching** (P0) — prove we can switch from GPT 5.5 to DeepSeek when rate-limited
3. **Direct APIs** (P1) — Claude API, Gemini API — reliable fallbacks that don't depend on any agent binary
4. **Other CLI agents** (P2) — Codex, Claude Code, Gemini CLI — if installed
5. **Pi native integration** (P2) — extension/skill approach

## Test tiers

### Tier 1: Import test (30 seconds per agent)

Can we import the agent's Python API at all?

```python
# Hermes native
from hermes_cli.xxx import yyy  # Exact import from Plan 027
print("NATIVE IMPORT: OK")

# Pi extension
# (TypeScript — verify pi can load the extension)
```

**Pass**: import succeeds. **Fail**: ModuleNotFoundError, dependency conflict.

### Tier 2: Config reading test (1 minute per agent)

Can we read the agent's config and enumerate available models?

```python
# Hermes: read config.yaml, list models
from hermes_cli.config import load_config
cfg = load_config()
print("MODELS:", [m["name"] for m in cfg.get("models", [])])
print("PROVIDERS:", [p["provider"] for p in cfg.get("providers", [])])
```

**Pass**: Returns non-empty model list. **Fail**: config unreadable, no models found.

### Tier 3: Smoke test — trivial prompt (2-5 minutes per agent per model)

Send the simplest possible prompt to each available model, verify response.

```python
prompt = 'Return EXACTLY: {"status":"ok","model":"<model_name>"}'

# Native mode (Hermes)
from hermes_cli.xxx import yyy
result = yyy(prompt)
print("RESULT:", result[:200])
assert "ok" in result

# External mode (Hermes CLI)
subprocess.run(["hermes", "chat", "--yolo", "-Q", "-q", "--model", "deepseek", prompt])

# Direct API (Claude)
import urllib.request, json
req = urllib.request.Request("https://api.anthropic.com/v1/messages", ...)
response = json.loads(urllib.request.urlopen(req).read())
```

**Pass**: Valid response within 60s. **Record**: latency, model used, clean JSON? Markdown wrapping?

### Tier 4: Model switching test (5 minutes)

Prove the KEY use case: when model A rate-limits, model B takes over.

```python
models = ["gpt-5.5", "deepseek"]  # from config
for model in models:
    result = call_model(prompt, model=model)
    if result and not is_rate_limited(result):
        print(f"USING: {model}")
        break
```

**Test scenario A** (preferred): Hermes is currently rate-limited on GPT 5.5. Verify DeepSeek works.
**Test scenario B** (if not rate-limited): Record that both models work. The fallback logic is still proven.

### Tier 5: Real evaluation test (5-15 minutes per agent)

Run the FULL HaxJobs evaluation prompt against a real job and verify:
- Response is valid JSON
- All 9 evaluation fields present (fit_score, fit_verdict, level, level_name, strongest_matches, major_gaps, sponsorship_risk, summary, decision)
- Score is in plausible range (0-100)
- Level is in [1,2,3,4]

```bash
# Generate the evaluation prompt
PYTHONPATH=. python3 -c "
from evaluate.common import build_prompt, build_profile_blurb
from db.schema import init, get_db
init()
conn = get_db()
job = conn.execute('SELECT * FROM jobs WHERE id=4').fetchone()  # job #4 has a real JD
conn.close()
prompt = build_prompt(dict(job))
with open('/tmp/eval_prompt.txt', 'w') as f:
    f.write(prompt)
print(f'Prompt: {len(prompt)} chars')
"

# Test with each agent/mode
```

### Tier 6: Pi integration feasibility (15 minutes, interactive)

If Plan 027 found that Pi's extension API supports custom tools:
1. Write a minimal Pi extension `~/.pi/agent/extensions/haxjobs-test.ts` that registers a test tool
2. Verify `/reload` loads it
3. Verify the tool can be called from within Pi

If Plan 027 found Pi skills as the better path:
1. Write a minimal skill `~/.pi/agent/skills/haxjobs/SKILL.md`
2. Verify it appears in available skills
3. Verify Pi can follow evaluation instructions from the skill

## Test matrix

Create this table and fill it in as you test:

```
research/test-results/test-matrix.md
```

| Agent | Mode | Import? | Config? | Smoke? | Model switch? | Real eval? | Latency | JSON clean? | Notes |
|-------|------|---------|---------|--------|--------------|-----------|---------|-------------|-------|
| Hermes | native | ✓ | ✓ (2 models) | ✓ deepseek | ✓ (gpt→deepseek) | ? | ? | ? | |
| Hermes | external | N/A | N/A | ✓ gpt-5.5 | ? | ? | ? | ? | |
| Claude | API | N/A | N/A | ✓ sonnet | N/A | ? | ? | ? | |
| Gemini | API | N/A | N/A | ✓ flash | N/A | ? | ? | ? | |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | |

Each ✓ must be backed by raw output saved in `research/test-results/<agent>/`.

## Test artifacts

```
research/test-results/
├── SUMMARY.md                  # Overall verdict table + recommendations
├── hermes/
│   ├── native_import.txt       # Import test output
│   ├── native_config.txt       # Model list from config
│   ├── native_smoke_gpt55.txt  # Smoke test with GPT 5.5
│   ├── native_smoke_deepseek.txt
│   ├── native_eval.txt         # Real evaluation output
│   └── external_eval.txt       # CLI subprocess evaluation (comparison)
├── claude_api/
│   ├── smoke.txt
│   └── eval.txt
├── gemini_api/
│   ├── smoke.txt
│   └── eval.txt
├── codex/  (if installed)
├── pi/     (if feasible)
└── test-matrix.md
```

## Priority order

Test in this order — stop when you have enough working options:

1. **Hermes native** — highest value. If we can import hermes_cli and call models directly, that's a massive win.
2. **Hermes model switching** — prove DeepSeek works when GPT 5.5 is rate-limited.
3. **Claude API** — most reliable external fallback. Always available, no agent binary needed.
4. **Gemini API** — free tier, good budget fallback.
5. **Other installed CLI agents** (Codex, Claude Code, Gemini CLI) — nice to have.
6. **Pi integration** — different category entirely, lower priority than getting evaluation working.

## Verification commands

```bash
# Hermes native import test
cd /home/hax/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
from hermes_cli.config import load_config
cfg = load_config()
print('Config keys:', list(cfg.keys())[:5])
" 2>&1

# Hermes model list
cd /home/hax/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
from hermes_cli.config import load_config
cfg = load_config()
for m in cfg.get('models', []):
    print(f\"  {m.get('name','?')} → {m.get('provider','?')}\")
" 2>&1

# Claude API smoke test (REQUIRES ANTHROPIC_API_KEY env var)
python3 -c "
import os, json, urllib.request
key = os.environ.get('ANTHROPIC_API_KEY', '')
print('Key present:', bool(key))
if key:
    data = json.dumps({'model':'claude-3-5-sonnet-20241022','max_tokens':100,'messages':[{'role':'user','content':'Return EXACTLY {\"ok\":true}'}]}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=data, headers={'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    print(resp['content'][0]['text'][:200])
" 2>&1

# Gemini API smoke test (REQUIRES GEMINI_API_KEY env var)
python3 -c "
import os, json, urllib.request
key = os.environ.get('GEMINI_API_KEY', '')
print('Key present:', bool(key))
if key:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}'
    data = json.dumps({'contents':[{'parts':[{'text':'Return EXACTLY {\"ok\":true}'}]}],'generationConfig':{'responseMimeType':'application/json'}}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    print(resp['candidates'][0]['content']['parts'][0]['text'][:200])
" 2>&1
```

## Deliverables

- `research/test-results/SUMMARY.md` — overall verdict with working options ordered by reliability
- `research/test-results/test-matrix.md` — completed matrix with all test results
- Per-agent directories with raw output
- Clear recommendation for Plan 029: which adapters to build, in what order, with what integration mode (native preferred, external fallback)
- `plans/README.md` updated

## STOP conditions

- If Hermes has NO importable Python API, move to external mode testing. Don't force native if it doesn't exist.
- If ALL Hermes models are rate-limited, skip live Hermes tests — test with direct APIs (Claude, Gemini) and note "Hermes tests blocked by rate limit, retry after reset."
- If an API key is not set, skip that test and mark "BLOCKED: needs API key env var."
- If an import causes dependency conflicts, skip and mark "BLOCKED: import conflict."
- Do NOT commit API keys, tokens, or secrets to the repo. Use env vars only.

## Done criteria

- [ ] Hermes config parsed — at least 2 models identified
- [ ] At least ONE model tested successfully with a real evaluation prompt (any agent, any mode)
- [ ] Model switching logic proven (or documented as "both models available, switch code ready")
- [ ] `research/test-results/SUMMARY.md` with clear go-forward list for Plan 029
- [ ] At least 2 integration paths confirmed working (e.g., Hermes external + Claude API)
- [ ] Raw output saved for every test
- [ ] `plans/README.md` updated
