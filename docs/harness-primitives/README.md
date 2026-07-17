---
tags: [readme, meta]
aliases: [README, Harness Primitives Index]
created: 2026-07-15
updated: 2026-07-15
---

# Harness Primitives Vault

Start with [[00-Harness-Primitives]], then read [[00-How-An-Agent-Actually-Runs]].

The lessons follow the same progression as The Carbon Layer build:

```text
stateless model
-> message history
-> instructions and context
-> tools and safety
-> durable state and workflow control
-> sub-agents and skills
-> verification and traces
-> interface over the same core
```

The video uses a coding agent to make each idea concrete. This vault keeps the lessons general. Short callouts quote code from `~/gemma`, then translate the coding example into a pattern that also applies to career, support, finance, research, and operations agents.

## Notes

1. [[01-instructions]]: rules the model sees before work starts.
2. [[02-context-delivery-and-management]]: selecting useful material and protecting the model's attention.
3. [[03-tool-interface]]: named actions the model may request.
4. [[04-execution-environment]]: permission, approval, secrets, and containment.
5. [[05-durable-state]]: sessions, facts, events, and retrieval.
6. [[06-orchestration]]: planning, order, retries, checkpoints, and stopping.
7. [[07-sub-agents-and-skills]]: focused workers and saved procedures.
8. [[08-verification-and-observability]]: external proof and run traces.
9. [[09-evolution]]: turning repeated failures into tested improvements.

Some files explain two related primitives together, so nine numbered notes cover all twelve pieces.

## Practical source

- Video: [Building an AI Agent From Scratch in Python, One Primitive at a Time](https://youtu.be/oUBgqzcV1qw)
- Local repository: `~/gemma`

The code snippets quote the current `main` branch, which includes fixes added after the original chapter tags. Use `git show ch-05:harness/tools.py` inside `~/gemma` when you need the exact historical chapter version.
