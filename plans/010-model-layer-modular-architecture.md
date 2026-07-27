# Plan 010 — DeepSeek thinking mode and streaming fix

> **Baseline:** `7a0f608` (current main)
> **Drift stamp:** 2026-07-26
> **Status:** ACCEPTED (codex-reviewed)
> **Depends on:** Plan 009 DONE

## Goal

Fix the broken DeepSeek streaming that produces incomplete sentences and can't handle multi-turn tool calls. The root cause is that DeepSeek thinking mode sends `reasoning_content` chunks before `content` chunks, the current stream handler only reads `content`, and `reasoning_content` from tool-call turns is never passed back to the model in subsequent requests.

This is NOT a modular refactor. This is a targeted bug fix in existing files. One atomic change.

---

## Root cause (verified against live code)

1. **`model/client.py:213`** — only handles `delta.content`. DeepSeek thinking mode sends `delta.reasoning_content` first, then `delta.content` second. Reasoning chunks are silently dropped. The stream appears to stall, then content arrives in disconnected fragments.

2. **`model/types.py:77-82`** — `ModelStreamEventType` has `TEXT_DELTA` but no `THINKING_DELTA`. Reasoning chunks have nowhere to go even if captured.

3. **`model/types.py:26-31`** — `ModelMessage` has no `reasoning_content` field. Even if the adapter captured it, there's nowhere to put it in provider-bound messages.

4. **`agent_core/messages.py:34-45`** — `AssistantMessage` has no `reasoning_content` field and `extra: forbid` blocks any attempt to store it. The canonical message history can't carry reasoning across turns.

5. **`agent_core/messages.py:93-107`** — `MessageProjector._flush()` builds a `ModelMessage(role="assistant", ...)` with `content` and `tool_calls` but no `reasoning_content`.

6. **DeepSeek requirement** (docs): When the model makes a tool call during thinking mode, `reasoning_content` from that turn MUST be passed back in all subsequent requests or the API returns 400. HaxJobs never preserves it, so multi-turn tool-call conversations break.

---

## Fix (one atomic change)

### Step 1 — Add `reasoning_content` to canonical types

**File: `model/types.py`**

- Add `THINKING_DELTA` to `ModelStreamEventType` enum
- Add `reasoning_content: str = ""` field to `ModelResponse`
- Add `reasoning_content: str | None = None` field to `ModelMessage` (the provider-bound message type)

**File: `agent_core/messages.py`**

- Add `reasoning_content: str = ""` field to `AssistantMessage` with default
- Keep `model_config = {"extra": "forbid"}` — the explicit field satisfies it

Both fields default to empty/None so existing serialized messages parse without migration.

### Step 2 — Capture reasoning_content in the adapter

**File: `model/client.py`**

In the `stream()` method, after the `async for chunk in stream:` line:

```python
# reasoning content delta
if getattr(delta, "reasoning_content", None):
    yield ModelStreamEvent(
        event_type=ModelStreamEventType.THINKING_DELTA,
        delta=delta.reasoning_content,
        model=self._model,
        provider=self._provider,
    )
```

In the `complete()` method, after `msg.content`:

```python
reasoning_content = getattr(msg, "reasoning_content", None) or ""
```

And include it in the returned `ModelResponse(reasoning_content=reasoning_content, ...)`.

Also add `extra_body` to both stream and non-stream methods, gated to DeepSeek:

```python
if self._provider == "deepseek":
    kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
```

### Step 3 — Accumulate reasoning in the turn loop

**File: `agent_core/turn.py`**

Initialize `accumulated_reasoning` inside the main loop alongside `accumulated_text` (line 198-202):

```python
model_steps += 1
accumulated_text = ""
accumulated_reasoning = ""
```

In the stream event handler, add a branch for `THINKING_DELTA`:

```python
elif stream_event.event_type == ModelStreamEventType.THINKING_DELTA:
    accumulated_reasoning += stream_event.delta
    # Do NOT emit as LiveEvent (thinking is internal to the model)
```

When persisting the canonical AssistantMessage after a tool call turn, include reasoning_content:

```python
assistant_msg = AssistantMessage(
    message_id=_mid(),
    turn_id=turn_id,
    content=accumulated_text,
    status="complete",
    reasoning_content=accumulated_reasoning,
)
```

**Critical: the in-loop provider message also needs reasoning.** After a tool-call response, turn.py directly builds a `ModelMessage(role="assistant", tool_calls=...)` at line ~551 and appends it to `provider_messages` — the in-memory list used for the very next model request within the same turn. This message never goes through the projector. Without reasoning_content on it, the immediate next request drops it and DeepSeek returns 400.

```python
provider_messages.append(
    ModelMessage(
        role="assistant",
        content=accumulated_text,
        tool_calls=[...],
        reasoning_content=accumulated_reasoning or None,
    )
)
```

### Step 4 — Carry reasoning_content through the projector

**File: `agent_core/messages.py`**

In `MessageProjector.__init__`, add:

```python
self._pending_reasoning_content: str = ""
```

In `MessageProjector._flush()`, when building the assistant ModelMessage, include it:

```python
if self._pending_reasoning_content:
    msg.reasoning_content = self._pending_reasoning_content
self._pending_reasoning_content = ""
```

In `MessageProjector.project()`, when processing an `assistant` message:

```python
elif msg.kind == "assistant":
    self._flush()
    self._pending_text = msg.content
    self._pending_reasoning_content = getattr(msg, "reasoning_content", "")
```

In the `project()` reset block, clear it:

```python
self._pending_reasoning_content = ""
```

### Step 5 — Projection emits reasoning_content on the provider message

The `ModelMessage` now has a `reasoning_content` field. When `_flush()` sets it and `client.py:68-71` dumps messages with `model_dump(exclude_none=True)`, a `None` default won't appear in non-tool-call messages. Only messages that had tool calls (where reasoning_content was set) will include the field.

---

## Files in scope

| File | Change |
|---|---|
| `model/types.py` | `THINKING_DELTA` enum, `reasoning_content` field on ModelResponse + ModelMessage |
| `model/client.py` | Capture `reasoning_content` in stream + complete, add `extra_body` with thinking mode |
| `agent_core/turn.py` | Accumulate reasoning, persist on AssistantMessage with tool calls, THINKING_DELTA branch |
| `agent_core/messages.py` | `reasoning_content` field on AssistantMessage, `_pending_reasoning_content` in projector |
| `tests/` | New test file for thinking mode streaming |

## Files NOT touched

- `employment/*` — zero employment-layer changes
- `interfaces/*` — TUI only renders LiveEvent, THINKING_DELTA is intentionally not forwarded
- `agent_core/session.py` — no session logic changes
- `agent_core/live_events.py` — no new LiveEventType added
- `agent_core/tools.py` — no tool contract changes
- `model/fake.py` — unchanged

## Tests (must pass)

1. **Mocked DeepSeek stream with reasoning** — adapter yields THINKING_DELTA chunks before TEXT_DELTA chunks, accumulated reasoning preserved on assistant message
2. **Multi-turn tool call with reasoning preservation** — first turn has tool calls with reasoning, second turn's projected messages include reasoning_content on the assistant message
3. **In-loop provider message carries reasoning** — fake-stream test with tool call asserting `fake.requests[1]` contains `reasoning_content` on the assistant message with tool calls; this is the critical path that bypasses the projector (turn.py line 551).
4. **Canonical JSON round trip** — AssistantMessage with reasoning_content serializes and deserializes correctly
5. **Backward compat** — AssistantMessage without reasoning_content field (old JSON) parses correctly
6. **Thinking not leaked** — LiveEvent stream never contains THINKING_DELTA content
7. **Existing test suite** — all 290 existing tests pass unchanged

## Live validation

```bash
haxjobs chat --new
# Send one message that requires multiple steps (tool calls)
# Verify sentences arrive complete, no broken fragments
# Verify multi-turn conversation works without 400 errors
```

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')
uv lock --check
git diff --check
```

## Out of scope

- Modular file split (no protocol.py, no adapters/, no streaming.py, no schemas.py, no provider.py)
- StreamAccumulator class
- user_id context caching / session isolation
- Context cache hit tracking (`prompt_cache_hit_tokens`)
- Anthropic API format adapter
- Token usage tracking improvements
- TUI thinking indicator
- Tool dispatch extraction from turn.py
- Reasoning effort control (`reasoning_effort` parameter — default "high" is fine for initial fix)

---

> **Warning for executor:** This plan targets the exact bug in live code. Before implementing, check that `model/client.py:213` still only handles `delta.content` and that `agent_core/messages.py:34-45` still forbids extras on `AssistantMessage`. If either has changed since this plan was written, adjust accordingly. Do not create new modules — this is an in-place bug fix.
