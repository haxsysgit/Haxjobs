# Plan 043: Onboarding backend — CV upload → LLM extraction → profile.json

> **Depends on**: 041 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Without onboarding, HaxJobs is a tool for one person who hand-writes their profile JSON. The onboarding wizard makes it a product: upload CV → LLM extracts structured data → guided questions fill gaps → profile.json saved. This plan fills in the `features/onboarding/` module created in plan 041.

## Steps

### Step 1: Add dependency

```bash
uv add openai
```

### Step 2: Create features/onboarding/schemas.py

Pydantic models:
- `CVUploadResponse` — extracted profile + next question
- `WizardAnswer` — question_id + answer
- `WizardResponse` — updated profile + next question (or null if done)
- `ProfileSchema` — the full profile shape (name, email, phone, skills, work_experience, education, projects, preferences)

### Step 3: Create features/onboarding/service.py

Business logic:
- `extract_profile_from_cv(cv_text: str) -> dict` — calls OpenAI with JSON schema response format, returns structured profile
- `get_next_question(profile: dict, answered: list) -> dict | None` — finds missing/low-confidence fields, generates targeted question
- `apply_answer(profile: dict, question_id: str, answer: str) -> dict` — merges answer into profile
- `save_profile(profile: dict)` — writes to `~/.haxjobs/profile.json`
- `load_profile() -> dict | None` — reads from `~/.haxjobs/profile.json`

Profile JSON schema has: personal_info, skills[], work_experience[], education[], projects[], preferences (roles[], locations[], work_modes[], excluded_companies[]).

### Step 4: Create features/onboarding/routes.py

FastAPI routes:
- `POST /api/onboarding/upload` — accepts PDF upload, extracts text, calls service.extract_profile_from_cv(), returns CVUploadResponse
- `POST /api/onboarding/wizard` — accepts WizardAnswer, calls service.apply_answer() then service.get_next_question(), returns WizardResponse
- `POST /api/onboarding/complete` — saves final profile, returns success

### Step 5: Write tests

`tests/test_onboarding.py` — mock OpenAI call, test extraction parsing, wizard question flow, profile save/load.

### Step 6: Commit

```bash
git commit -m "add onboarding backend: CV upload, LLM extraction, wizard API"
uv run pytest -q tests/  # verify all pass
```

## Done criteria

- [ ] `POST /api/onboarding/upload` returns structured profile from CV
- [ ] Wizard returns relevant questions for missing fields
- [ ] Profile persists to `~/.haxjobs/profile.json`
- [ ] Tests pass with mocked LLM
- [ ] `openai` in pyproject.toml deps
