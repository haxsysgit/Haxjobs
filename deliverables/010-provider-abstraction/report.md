# Plan 010 Implementation Report — Provider Abstraction Layer

**Commit:** `939f2dc`
**Tests:** 310 passed
**Review:** Two reviewers, both PASS

## What changed

Replaced the 300-line `model/client.py` monolith with a proper provider abstraction using Pi's `compat` flag pattern. The old file handled 6 concerns in one class: config loading, SDK construction, non-stream completion, stream handling, tool call accumulation, and error wrapping.

## New files

| File | Lines | Purpose |
|------|-------|---------|
| `model/protocol.py` | 25 | `ModelClient` protocol — `complete()` + `stream(cancel_event)` |
| `model/profiles.py` | 70 | `ProviderProfile` dataclass with 7 flags + 3 provider constants + `detect_profile()` |
| `model/adapter.py` | 206 | `GenericAdapter` — flag-driven, never branches on provider name |
| `model/provider.py` | 49 | `ProviderConfig` + `load_provider_config()` from `~/.haxjobs/haxjobs.toml` |
| `model/schemas.py` | 22 | `tool_to_openai_schema()` + `tools_to_openai_schemas()` |
| `model/streaming.py` | 139 | `StreamAccumulator` — pure sync, testable with plain strings |
| `tests/test_profiles.py` | 45 | 8 tests for profile detection + flags |
| `tests/test_stream_accumulator.py` | 101 | 11 tests for delta accumulation + reasoning handling |

## Deleted files

| File | Lines | Reason |
|------|-------|--------|
| `model/client.py` | 288 | Replaced by protocol + adapter + profiles + schemas + streaming + provider |

## Modified files

| File | Change |
|------|--------|
| `model/types.py` | +`THINKING_DELTA` event, +`reasoning_content` on `ModelMessage` + `ModelResponse` |
| `model/__init__.py` | Exports all new types |
| `agent_core/messages.py` | +`reasoning_content` on `AssistantMessage`, projector carries it |
| `agent_core/turn.py` | `THINKING_DELTA` branch, accumulate reasoning, set on both canonical + in-loop messages |
| `agent_core/session.py` | Import updated |
| `employment/composition.py` | Wires `config → profile → adapter` |
| `model/fake.py` | Import updated |
| `tests/test_model_streaming.py` | Updated for `GenericAdapter` |

## Architecture

The adapter reads `ProviderProfile` flags. It never branches on provider name (except one check: `thinking_format == "deepseek"` to decide which chunk attribute to read — `delta.reasoning_content` vs nothing).

Adding GPT 5.6 means one 6-line `OPENAI_PROFILE` constant. Zero adapter changes. Zero agent loop changes.

## reasoning_content data flow

1. `GenericAdapter.stream()` captures `delta.reasoning_content` when `thinking_format == "deepseek"`
2. `StreamAccumulator.feed_reasoning()` stores it
3. `turn.py` accumulates from `THINKING_DELTA` events (not forwarded to LiveEvent)
4. Set on canonical `AssistantMessage` for persistence
5. Set on in-loop `ModelMessage` for immediate next request (critical bypass — the projector only handles session resume)
6. `MessageProjector` carries it from persisted `AssistantMessage` → provider-bound `ModelMessage`
7. `model_dump(exclude_none=True)` omits when `None`

## Review findings

Two DeepSeek V4 Flash reviewers. Both PASS. No blockers.

Architecture reviewer confirmed: zero layer boundary violations, no `model.client` imports remaining, adapter never branches on provider name, profiles match plan exactly, full reasoning_content flow verified.

Safety/tests reviewer confirmed: 310 tests pass, py_compile clean, uv lock check clean, git diff --check clean. Two non-blocking notes: no unit test for `GenericAdapter.complete()` non-streaming path, no edge-case tests for `ProviderConfig` with unusual URLs.

## Verification

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/   # 310 passed
PYTHONPATH=src:. uv run python3 -m py_compile $(find src -name '*.py')  # clean
uv lock --check                                          # clean
git diff --check                                         # clean
```

## Out of scope (deferred)

- Anthropic messages API adapter (separate adapter needed for non-OpenAI-compatible APIs)
- Context cache hit tracking
- `user_id` session isolation
- TUI thinking indicator
- `reasoning_effort` parameter control
- Provider fallback cascade
