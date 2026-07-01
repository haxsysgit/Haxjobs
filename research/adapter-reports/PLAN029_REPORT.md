# Plan 029 implementation report — 2026-07-01

## Built

| File | What |
|---|---|
| `evaluate/agents/base.py` | BaseAdapter — shared `evaluate_job()` dispatch with normalization |
| `evaluate/agents/claude_code.py` | ClaudeCodeAdapter — session-native, headless blocked |
| `evaluate/agents/codex.py` | CodexAdapter — headless `--output-schema` (strongest) |
| `evaluate/agents/hermes.py` | HermesAdapter — rewritten as BaseAdapter subclass |
| `evaluate/agents/pi.py` | PiAdapter — rewritten with JSONL event parser |
| `evaluate/agents/gemini.py` | GeminiAdapter — stub (tier migration blocked) |
| `evaluate/agents/__init__.py` | AGENT_LIST + auto_discover() |
| `evaluate/chain.py` | Fallback chain — config-driven, auto-discovery fallback |
| `evaluate/run.py` | Updated to use chain dispatch |
| `haxjobs_config.py` | Added EVALUATION_FALLBACK_AGENTS |
| `tests/test_evaluator_agent_selection.py` | Rewritten for new chain API |

## Headless test results (faculty SWE Platform, job #633)

| Adapter | Score | Level | Time | Valid |
|---|---|---|---|---|
| codex | 62 | L2 | 17s | ✅ |
| hermes | 61 | L2 | 25s | ✅ |
| pi | 62 | L2 | 54s | ✅ |
| claude_code | — | — | — | ❌ credit |
| gemini | — | — | — | ❌ tier |

## Chain fallback verified

- Config `agent = "hermes"` → uses hermes
- Override `agent_order=["codex"]` → uses codex
- Override `agent_order=["codex", "hermes", "pi"]` → uses codex first, never falls through
- auto_discover() → `['codex', 'hermes', 'pi']`

## Raw outputs

Per-adapter evaluation JSONs saved to `research/adapter-reports/{agent}_eval.json`.

## Test suite

245 tests pass. py_compile clean.
