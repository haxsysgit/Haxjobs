# Plan 005 manual proof

## Ownership and safety

This file records only safe local metadata. It contains no raw PTY transcript,
career text, model text, provider credential, private fixture output, or live-run
claim. The proof uses tracked job fixtures and an isolated in-memory SQLite
career store.

## Safe run

- Run ID: `local-005-isolated-20260721T221725Z`
- Environment: local worktree, Python 3.12, `CareerStore(':memory:')`
- Provider: none; direct typed action/tool calls only
- Network: none
- State mutation: none; no `state/` path opened

## Reproducible command

```bash
PYTHONPATH=src:. uv run -- python3 - <<'PY'
import asyncio, json
from haxjobs.agent_core.tools import ToolExecutionContext
from haxjobs.employment import job_actions
from haxjobs.employment.schema import CareerTrack, Person
from haxjobs.employment.store import CareerStore
from haxjobs.employment.tools import build_employment_tool_registry

store = CareerStore(":memory:")
job_actions.import_job_from_fixture(store, "discussion/fixtures/harness/job-49.json")
now = "2026-07-21T00:00:00+00:00"
store.upsert_person(Person(person_id="p", name="Test", location="L", created_at=now, updated_at=now))
store.upsert_track(CareerTrack(track_id="t", person_id="p", name="Backend", created_at=now, updated_at=now))

async def proof():
    registry, active = build_employment_tool_registry(store, "t")
    ctx = ToolExecutionContext("s", "turn", "call-1", "user-message-1", asyncio.Event())
    first = await registry.dispatch("record_job_decision", json.dumps({"job_id":"job-49", "label":"skip"}), active, ctx)
    replay = await registry.dispatch("record_job_decision", json.dumps({"job_id":"job-49", "label":"skip"}), active, ctx)
    correction = await registry.dispatch("record_job_decision", json.dumps({"job_id":"job-49", "label":"save"}), active, ToolExecutionContext("s", "turn-2", "call-2", "user-message-2", asyncio.Event()))
    recall = await registry.dispatch("get_job", json.dumps({"job_id":"job-49"}), active, ctx)
    assert first["ok"] and not first["data"]["replay"]
    assert replay["ok"] and replay["data"]["replay"]
    assert correction["ok"] and recall["data"]["latest_decision"]["label"] == "save"
    assert [row["label"] for row in store.list_decisions("job-49", "t")] == ["skip", "save"]
    assert store.list_decisions("job-49", "t")[0]["source_user_message_id"] == "user-message-1"
    assert store.list_decisions("job-49", "t")[0]["reason"] == ""

asyncio.run(proof())
store.close()
print("SAFE_LOCAL_PROOF_PASS")
PY
```

Observed: `SAFE_LOCAL_PROOF_PASS`.

## Not performed

- No configured-provider conversation.
- No live source inspection.
- No private career fixture or operator database.
- No human rubric verdict.
- No application, outreach, submission, queue, pack, or external effect.
