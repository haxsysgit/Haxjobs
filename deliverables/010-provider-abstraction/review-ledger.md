# Plan 010 Review Ledger

## Reviewer 1: Architecture and Correctness (DeepSeek V4 Flash)

**Verdict: PASS**

### Verified
- All 310 tests pass
- Layer discipline: zero `model/` imports from `agent_core`, `employment`, or `interfaces`
- `client.py` fully deleted, zero remaining imports
- Adapter never branches on provider name (the only `"deepseek"` string is a flag check on `thinking_format`)
- `DEEPSEEK_PROFILE` has `thinking_format="deepseek"`, `requires_reasoning_preservation=True`, `extra_body` with thinking enabled
- `OPENAI_PROFILE` has `thinking_format="disabled"`, `requires_reasoning_preservation=False`
- `DEFAULT_PROFILE` is safe defaults
- Full reasoning_content data flow verified end to end:
  1. adapter captures `delta.reasoning_content` ✓
  2. `StreamAccumulator.feed_reasoning()` stores it ✓
  3. `turn.py` accumulates from `THINKING_DELTA` ✓
  4. Reset each loop iteration ✓
  5. Set on canonical `AssistantMessage` ✓
  6. Set on in-loop `ModelMessage` with `or None` ✓
  7. `MessageProjector` reads + carries it ✓
  8. `_flush()` attaches on projection ✓
  9. `model_dump(exclude_none=True)` omits `None` ✓

### Notes
- Protocol uses `def stream` rather than `async def stream` — structurally equivalent for `AsyncIterator` return
- `FakeModelClient.complete()` still returns `ModelResponse | ModelFailure` union instead of raising — low risk since only used in tests

## Reviewer 2: Safety, Tests, Edge Cases (DeepSeek V4 Flash)

**Verdict: PASS**

### Verified
- 310 tests pass, py_compile clean, uv lock check clean, git diff check clean
- `test_profiles.py`: 8 tests covering deepseek/openai/unknown detection and profile flags
- `test_stream_accumulator.py`: 11 tests covering text, reasoning (enabled + disabled), tool call assembly, unsafe marking, state clearing
- `test_model_streaming.py`: 2 `GenericAdapter` tests (fragmented tool calls, mid-stream cancellation) + 9 `FakeModelClient` tests
- Cancel event checked between stream chunks, upstream stream closed on cancellation
- Credentials loaded from `PROVIDER_CONFIG_PATH`, never hardcoded
- Usage-only chunks (no choices) handled correctly

### Notes (non-blocking)
- No unit test for `GenericAdapter.complete()` non-streaming path
- No edge-case tests for `ProviderConfig` with unusual/malformed URLs
