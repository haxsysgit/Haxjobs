# Plan 045: Onboarding backend — CV upload → agent extraction → profile.json

> **Depends on**: 041, 043 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Without onboarding, HaxJobs is a tool for one person who hand-writes their profile JSON. The onboarding wizard makes it a product: upload CV → native agent extracts structured data → guided questions fill gaps → profile.json saved. This plan fills `features/onboarding/`.

Uses the native agent (plan 043) for all LLM calls — no direct API access. The agent reads provider config from `~/.haxjobs/config.toml` (plan 042), so it works with any configured provider (DeepSeek default, OpenAI, custom).

## Steps

### Step 1: No new deps needed

`openai` package is already added in plan 043 (native agent). The agent module handles the HTTP client internally.

### Step 2: Create features/onboarding/schemas.py

Pydantic models:
- `CVUploadResponse` — extracted profile + next question
- `WizardAnswer` — question_id + answer
- `WizardResponse` — updated profile + next question (or null if done)

Profile JSON schema has: personal_info, skills[], work_experience[], education[], projects[], preferences (roles[], locations[], work_modes[], excluded_companies[]).

### Step 3: Create features/onboarding/service.py

```python
"""Onboarding business logic — uses native agent for extraction and questions."""
import json
from pathlib import Path
from haxjobs.agent import Agent

PROFILE_PATH = Path.home() / ".haxjobs" / "profile.json"
PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "personal_info": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
                "work_authorization": {"type": "string"},
            },
        },
        "skills": {"type": "array", "items": {"type": "string"}},
        "work_experience": {"type": "array"},
        "education": {"type": "array"},
        "projects": {"type": "array"},
        "preferences": {
            "type": "object",
            "properties": {
                "roles": {"type": "array", "items": {"type": "string"}},
                "locations": {"type": "array", "items": {"type": "string"}},
                "work_modes": {"type": "array", "items": {"type": "string"}},
                "excluded_companies": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


def extract_profile_from_cv(cv_text: str) -> dict:
    """Extract structured profile from CV text using native agent."""
    agent = Agent()
    return agent.run_structured(
        prompt=f"Extract structured profile data from this CV:\n\n{cv_text}",
        system="You extract structured candidate profiles from CVs. "
                "Return valid JSON matching the schema. "
                "Infer skills from project descriptions. "
                "Leave unknown fields as empty strings or empty arrays.",
        json_schema=PROFILE_SCHEMA,
    )


def get_next_question(profile: dict, answered: list) -> dict | None:
    """Ask agent to identify the most important missing field."""
    agent = Agent()
    result = agent.run_structured(
        prompt=f"Profile so far:\n{json.dumps(profile, indent=2)}\n\n"
               f"Already asked: {json.dumps(answered)}\n\n"
               f"Identify the single most important missing or low-confidence field. "
               f"Return {{'field': '...', 'question': '...', 'type': 'text|select|multi'}}",
        system="You help fill gaps in job seeker profiles. Ask one targeted question at a time.",
        json_schema={
            "type": "object",
            "properties": {
                "field": {"type": "string"},
                "question": {"type": "string"},
                "type": {"type": "string", "enum": ["text", "select", "multi"]},
                "done": {"type": "boolean"},
            },
            "required": ["field", "question", "type", "done"],
        },
    )
    return result


def apply_answer(profile: dict, question_id: str, answer: str) -> dict:
    """Merge answer into profile at the right path."""
    # ponytail: simple dot-path setter. question_id = "personal_info.location"
    parts = question_id.split(".")
    target = profile
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = answer
    return profile


def save_profile(profile: dict):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def load_profile() -> dict | None:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            return json.load(f)
    return None
```

### Step 4: Create features/onboarding/routes.py

- `POST /api/onboarding/upload` — accepts PDF, extracts text, calls `extract_profile_from_cv()`, returns `CVUploadResponse`
- `POST /api/onboarding/wizard` — accepts `WizardAnswer`, calls `apply_answer()` then `get_next_question()`, returns `WizardResponse`
- `POST /api/onboarding/complete` — saves final profile, returns success

### Step 5: Write tests

`tests/test_onboarding.py` — mock `Agent.run_structured()`, test extraction parsing, wizard flow, profile save/load.

### Step 6: Commit

```bash
git commit -m "add onboarding backend: CV upload, agent extraction, wizard API"
uv run pytest -q tests/
```

## Done criteria

- [ ] `POST /api/onboarding/upload` returns structured profile via native agent
- [ ] Wizard questions generated by agent, fill profile gaps
- [ ] Profile persists to `~/.haxjobs/profile.json`
- [ ] Tests pass with mocked Agent
- [ ] No direct `openai.chat.completions.create()` calls — all through agent

## STOP conditions

- Agent not configured — user must complete `/setup` first (plan 042). Return clear error.
- PDF text extraction fails — show "paste text" fallback in onboarding UI
