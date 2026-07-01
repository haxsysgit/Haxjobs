# Plan 028 test matrix — focused on 5 shipping adapters

| Agent | Mode | Available? | Model used | Smoke JSON? | Real eval? | Score | Failure shape | Verdict |
|---|---|---|---|---|---|---|---|---|
| Hermes | CLI `hermes -z` | yes | config default | yes, clean | yes, valid | 62 L2 | none | ✅ READY |
| Hermes | native Python | yes import | blocked | import OK | no | — | `ModuleNotFoundError: No module named openai` during live call | defer native, use CLI |
| Codex | CLI `codex exec --output-schema` | yes | config default | yes, clean | yes, schema-valid | 62 L2 | none | ✅ READY primary |
| Pi | headless `pi -p --mode json --no-tools` | yes | deepseek-v4-pro | yes, clean | yes, valid | 60 L2 | JSONL event stream, output duplicated in stream | ✅ READY (needs event parser) |
| Claude Code | CLI `claude -p` | yes | — | no | no | — | `Credit balance is too low` (HTTP 400) | ❌ BLOCKED: credit |
| Gemini CLI | CLI `gemini -p -o json -y` | yes | — | no | no | — | `IneligibleTierError: migrate to Antigravity` | ❌ BLOCKED: tier migration |
