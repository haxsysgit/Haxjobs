# Plan 043: Onboarding backend — CV upload → LLM extraction → profile.json

> **Executor instructions**: Follow this plan step by step. Run every verification command. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- src/haxjobs/server/app.py src/haxjobs/profile/`
> Frontend shell (042) and FastAPI (041) must exist. Profile directory must exist.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (new module, doesn't touch existing code)
- **Depends on**: 041
- **Category**: direction
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Without onboarding, HaxJobs is a tool for one person who hand-writes their profile JSON. The onboarding wizard makes it a product: upload CV → LLM extracts structured data → guided questions fill gaps → profile.json saved to `~/.haxjobs/profile.json`. This plan builds the backend — CV upload endpoint, LLM extraction, and the wizard question API.

## Current state

- `profile/arinze_profile.local.json` — Arinze's personal profile, manually written
- No CV upload endpoint exists
- No LLM extraction exists
- `haxjobs_config.py` has no OPENAI_API_KEY config

## Commands

| Purpose | Command | Expected |
|---------|---------|----------|
| Run tests | `python3 -m pytest -q tests/` | all pass |
| Test upload | `curl -F "file=@test.pdf" http://localhost:8241/api/onboarding/upload` | JSON response |
| Test wizard | `curl -X POST -H "Content-Type: application/json" -d '{"answers":[{"question_id":"q1","answer":"Full-time"}]}' http://localhost:8241/api/onboarding/wizard` | next question or profile |

## Scope

**In scope**:
- Create `src/haxjobs/onboarding/` package
- `extract.py` — send CV to LLM API, parse structured profile
- `wizard.py` — question generation, answer processing, profile building
- FastAPI routes in `server/routes/onboarding.py`
- `OPENAI_API_KEY` config in `haxjobs_config.py`
- Profile saved to `~/.haxjobs/profile.json`

**Out of scope**:
- Frontend wizard UI — plan 044
- Profile editing after onboarding — plan 051
- Anthropic/Gemini as LLM backend — ponytail: OpenAI only for v1

## Steps

### Step 1: Add OPENAI_API_KEY to config

Add to `haxjobs.toml`:
```toml
[llm]
provider = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"
```

Add to `haxjobs_config.py`:
```python
LLM_CONFIG = _load_toml().get("llm", {})
OPENAI_API_KEY = os.getenv(LLM_CONFIG.get("api_key_env", "OPENAI_API_KEY"), "")
```

### Step 2: Create onboarding/extract.py

```python
"""CV extraction via LLM API."""
import json
import os
from openai import OpenAI

PROFILE_SCHEMA = { ... }  # JSON schema for structured output

def extract_profile_from_cv(cv_text: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_schema", "schema": PROFILE_SCHEMA},
        messages=[
            {"role": "system", "content": "Extract structured profile data from this CV..."},
            {"role": "user", "content": cv_text},
        ],
    )
    return json.loads(response.choices[0].message.content)
```

### Step 3: Create onboarding/wizard.py

API that generates targeted questions based on what's missing from the extracted profile. Each answer fills a gap. After 5-10 questions, the profile is complete enough to start.

```python
def get_next_question(profile: dict, answered_questions: list) -> dict | None:
    """Return the next question to ask, or None if profile is complete."""
    # Check which fields are missing or low-confidence
    # Generate a relevant question
```

### Step 4: Create FastAPI routes

`POST /api/onboarding/upload` — accepts PDF file, returns extracted profile + first question
`POST /api/onboarding/wizard` — accepts answer, returns updated profile + next question
`POST /api/onboarding/complete` — saves final profile to `~/.haxjobs/profile.json`

### Step 5: Add openai to pyproject.toml deps

### Step 6: Test

Write `tests/test_onboarding.py` — mock the OpenAI call, test extraction parsing, test wizard question flow, test profile save path.

### Step 7: Commit

## Done criteria

- [ ] CV upload endpoint returns structured profile
- [ ] Wizard returns relevant questions for missing fields
- [ ] Profile saved to `~/.haxjobs/profile.json`
- [ ] Tests pass with mocked LLM calls
- [ ] `openai` in pyproject.toml deps
