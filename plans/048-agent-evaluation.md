# Plan 048: Agent-based evaluation — delete subprocess adapters, use native agent

> **Depends on**: 041, 043 | **Priority**: P1 | **Effort**: M | **Risk**: MED (deletes code, changes evaluation path)
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`evaluate/agents/` spawns agent CLIs as subprocess. That's gone. Instead, evaluation uses the native agent (`haxjobs.agent.Agent.run_structured()`) with the existing `evaluate/common.py` prompt builder. One agent, all providers — DeepSeek today, any provider tomorrow.

This plan also fills `features/evaluation/` (the API layer for triggering evaluation from the UI).

## Steps

### Step 1: Delete agent subprocess adapters

```bash
git rm -r src/haxjobs/evaluate/agents/
git rm src/haxjobs/evaluate/chain.py
```

### Step 2: Update evaluate/common.py

Keep: `build_prompt()`, `validate_result()`, `EXPECTED_SCHEMA`. These are good.

Remove any references to agent CLI paths or subprocess calls. If `build_prompt()` loads the profile JSON, ensure it reads from `~/.haxjobs/profile.json` (what onboarding writes) with fallback to the repo profile.

### Step 3: Create evaluate/api.py

```python
"""Evaluation via native agent with structured output."""
from haxjobs.agent import Agent
from haxjobs.evaluate.common import build_prompt, EXPECTED_SCHEMA


def evaluate_job(job: dict, profile: dict) -> dict:
    """Evaluate a job against a profile. Returns validated result dict."""
    agent = Agent()
    prompt = build_prompt(job, profile)
    result = agent.run_structured(
        prompt=prompt,
        system=(
            "You are a job-candidate fit evaluator. "
            "Analyze the job description against the candidate's profile. "
            "Score from 0-100. Be honest — false hope wastes the candidate's time. "
            "Return valid JSON matching the schema exactly."
        ),
        json_schema={
            "type": "object",
            "properties": {
                "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "fit_level": {"type": "integer", "enum": [1, 2, 3, 4]},
                "fit_verdict": {"type": "string"},
                "strongest_matches": {"type": "array", "items": {"type": "string"}},
                "major_gaps": {"type": "array", "items": {"type": "string"}},
                "sponsorship_risk": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["fit_score", "fit_level", "fit_verdict", "strongest_matches", "major_gaps", "summary"],
            "additionalProperties": False,
        },
    )
    return result
```

### Step 4: Wire evaluate/run.py

```python
from haxjobs.evaluate.api import evaluate_job
# evaluate_from_db() loop stays — good code
# _auto_pack() stays — good code
```

### Step 5: Fill features/evaluation/

- **service.py**: wraps `evaluate.api.evaluate_job()` + `evaluate.run.evaluate_from_db()`
- **routes.py**: `POST /api/evaluation/run` (all pending), `GET /api/evaluation/status`
- **schemas.py**: request/response Pydantic models

### Step 6: Update tests

Delete: tests for agent subprocess adapters. Keep: tests for `evaluate/common.py`. Add: 3 tests for `evaluate/api.py` (mocked Agent, validates schema output, handles agent failure).

### Step 7: Verify

```bash
uv run pytest -q tests/
```

## Done criteria

- [ ] `evaluate/agents/` directory deleted
- [ ] `evaluate/chain.py` deleted
- [ ] `evaluate/api.py` uses `Agent.run_structured()`
- [ ] `features/evaluation/` has working routes
- [ ] No `subprocess.run()` in evaluate/ code
- [ ] No direct `openai.chat.completions.create()` — all through agent
- [ ] All tests pass

## STOP conditions

- Agent not configured → `POST /api/evaluation/run` returns 400 with "provider not configured" message
- Schema mismatch between `build_prompt()` and new api.py → check `EXPECTED_SCHEMA` matches the inline schema above
