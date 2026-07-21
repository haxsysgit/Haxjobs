# Plan 003 (Corrected): Career Graph and Real Conversation Runtime

| Key | Value |
|-----|-------|
| **Plan ID** | 003 |
| **Title** | Career Graph and First Real Conversation |
| **Status** | IMPLEMENTED (corrected) |
| **Implementation commit** | (see report.md) |
| **Correction baseline** | `7bd9a55` |
| **Previous delivery** | Career graph at `9ee53be` |

## Scope

The corrected Plan 003 keeps the delivered career graph and adds the smallest real conversational path over it:

```
inline terminal → employment session → domain-free turn runtime → model and tool loop → employment context and actions → career graph
```

Running `haxjobs` opens an inline conversation with Hax. Responses come from the configured provider. The terminal streams text, shows real tool lifecycle events, can interrupt work, persists canonical history, and can resume a prior session.

## Phases delivered

1. Canonical conversation messages (User, Assistant, ToolCall, ToolResult)
2. Content-bearing live interaction events (separate from redacted telemetry)
3. Streaming and cancellation in the model boundary
4. Append-only session persistence (SQLite)
5. Bounded streaming model and tool turn runtime
6. Employment host and CareerStore context assembly
7. Employment session with busy-input policy, subscribers, resume
8. Inline prompt_toolkit terminal client
9. Documentation, diagrams, and manual proof

## Architecture rules enforced

- Terminal imports only session protocol and live event types
- Session owns canonical history, not career truth
- Turn runtime is domain-free
- CareerStore context selected per turn, never copied to session history
- Live events stay separate from telemetry RunEvent
- Provider adapter assembles stream chunks
- One pending message slot for busy-input policy
