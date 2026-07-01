# Plan 046: Direct LLM evaluation — delete agent subprocess adapters

> **Depends on**: 041, 043 | **Priority**: P1 | **Effort**: M | **Risk**: MED (deletes code)
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The `evaluate/agents/` directory (hermes.py, codex.py, pi.py, claude_code.py, gemini.py) spawns agent CLIs as subprocess via `subprocess.run()`. Each CLI calls the same LLM APIs. This is an unnecessary middleman — slower, fragile, and requires agent CLI installation. Replace with direct `openai.chat.completions.create()` using structured output mode for guaranteed valid JSON.

## Steps

1. Create `src/haxjobs/evaluate/api.py`:
   ```python
   def evaluate_job(job: dict, profile: dict) -> dict:
       response = openai.chat.completions.create(
           model="gpt-4o",
           response_format={"type": "json_schema", "schema": EVAL_SCHEMA},
           messages=[{"role": "system", "content": build_prompt(job, profile)}],
       )
       return json.loads(response.choices[0].message.content)
   ```
2. Delete `evaluate/agents/` directory, `evaluate/chain.py`, `evaluate/agents/__init__.py`
3. Keep `evaluate/common.py` (build_prompt, validate_result, EXPECTED_SCHEMA) — good code
4. Keep `evaluate/run.py` — thin wrapper that calls `evaluate.api.evaluate_job()`
5. Update `evaluate/run.py` to import from `evaluate.api` instead of `evaluate.agents`
6. Delete agent adapter tests from `tests/test_evaluator_agent_selection.py` (keep common tests)
7. Write 3 new tests: direct API evaluation (mocked), structured output parsing, rate limit handling

**Ponytail**: `EVAL_SCHEMA` in `evaluate/api.py` is the same JSON schema used by codex `--output-schema`. Copy it from `evaluate/agents/codex.py` before deleting.

## Done criteria

- [ ] `evaluate/agents/` directory deleted
- [ ] `evaluate/api.py` uses direct `openai.chat.completions.create()`
- [ ] `evaluate/run.py` still works with new import path
- [ ] All tests pass (existing + 3 new)
- [ ] No subprocess.run() in evaluate/ code
