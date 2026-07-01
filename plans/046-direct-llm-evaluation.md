# Plan 046: Direct LLM evaluation — delete agent subprocess adapters

> **Depends on**: 041 | **Priority**: P1 | **Effort**: M | **Risk**: MED (deletes code, changes evaluation path)
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`evaluate/agents/` (hermes.py, codex.py, pi.py, claude_code.py, gemini.py) spawns agent CLIs as subprocess. Replace with direct `openai.chat.completions.create()` using JSON schema response format — faster, simpler, no agent CLI dependency.

## Steps

### Step 1: Add dependency (if not already from plan 043)

```bash
uv add openai  # no-op if already added
```

### Step 2: Create evaluate/api.py

```python
"""Direct LLM evaluation via OpenAI API with structured output."""
import json
import os
from openai import OpenAI

EVAL_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "job_evaluation",
        "schema": {
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
    },
}

def evaluate_job(job: dict, profile: dict) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": build_prompt(job, profile)},
        ],
        response_format=EVAL_SCHEMA,
    )
    return json.loads(response.choices[0].message.content)
```

Copy `build_prompt()` from `evaluate/common.py` — keep the existing prompt logic.

### Step 3: Delete agent adapters

```bash
git rm -r src/haxjobs/evaluate/agents/
git rm src/haxjobs/evaluate/chain.py
```

### Step 4: Update evaluate/run.py

Replace `from evaluate.chain import evaluate_one_job` → `from evaluate.api import evaluate_job`. Keep the `evaluate_from_db()` loop and `_auto_pack()` logic — they're good.

### Step 5: Create features/evaluation/

Fill in the skeleton from plan 041:
- **service.py**: calls `evaluate.api.evaluate_job()` + `evaluate.run.evaluate_from_db()`
- **routes.py**: `POST /api/evaluation/run` (evaluate all pending), `GET /api/evaluation/status`
- **schemas.py**: request/response models

### Step 6: Update/delete tests

Delete tests for agent adapters. Keep tests for `evaluate/common.py` (validate_result, build_prompt). Add 3 tests for `evaluate/api.py` (mocked OpenAI call, structured output parsing, rate limit handling).

### Step 7: Verify

```bash
uv run pytest -q tests/
```

## Done criteria

- [ ] `evaluate/agents/` directory deleted
- [ ] `evaluate/chain.py` deleted
- [ ] `evaluate/api.py` uses direct OpenAI API
- [ ] `features/evaluation/` has routes + service
- [ ] All tests pass
- [ ] No subprocess.run() in evaluate/ code

## STOP conditions

- OpenAI API key not set — `OPENAI_API_KEY` env var must exist
- Schema validation fails on real evaluation — check EVAL_SCHEMA matches what the LLM actually returns
