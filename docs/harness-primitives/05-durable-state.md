---
tags: [harness-primitives, memory, state]
aliases: [Durable State, Agent Memory, Memory Architecture]
cssclass: primitive
created: 2026-07-15
updated: 2026-07-15
---

# Primitive 6: Durable State

## If software did not save it, the agent did not remember it

The message list from [[00-How-An-Agent-Actually-Runs]] lets one running process replay earlier turns.

Close the process and that list disappears unless ordinary software writes it somewhere.

**Durable state** means data that survives this run, process, or machine restart.

```mermaid
flowchart LR
    T["Current turn"] --> S["Save useful state"]
    S --> D["Durable store"]
    D --> R["Retrieve relevant slice later"]
    R --> C["Build a future turn's context"]
```

Storage is only half the job. Retrieval makes stored material useful.

## Four useful kinds of memory

### Working memory

The messages and tool results open for the current run.

```python
messages = [
    {"role": "user", "content": "Compare these suppliers."},
    {"role": "tool", "content": "Three supplier records loaded."},
]
```

It is immediate and temporary. Context limits apply.

### Episodic memory

What happened, when, and why.

```python
save_event(
    kind="refund_decision",
    happened_at="2026-07-15T10:30:00Z",
    details={"order_id": 183, "decision": "approved"},
)
```

Sessions, tool runs, decisions, and outcomes are episodes.

### Semantic memory

Facts currently believed to be true.

```json
{
  "customer_id": 42,
  "preferred_language": "English",
  "shipping_region": "UK"
}
```

Facts need source, confidence, version, and verification date when mistakes matter.

### Procedural memory

How a repeated task should be done.

That may live in code, a workflow, or a [[07-sub-agents-and-skills|skill]]. It is a procedure, not an event from last Tuesday.

## Resuming a session is not the same as memory search

These solve different problems.

**Resume** reloads one conversation so work can continue.

**Recall** searches many saved events or facts and selects the few relevant to a new request.

A support agent may resume ticket 183 after a restart. Later, while handling ticket 302, it may search earlier duplicate-charge cases. That second action is retrieval, not session resume.

## From Gemma: a small durable session

Gemma stores one message per JSONL line.

Simplified from `~/gemma/harness/memory.py`

```python
def save_session(session_id: str, messages: list[dict], base: Path) -> None:
    path = base / f"{Path(session_id).name}.jsonl"
    write_jsonl_atomic(path, messages)


def load_session(session_id: str, base: Path) -> list[dict]:
    path = base / f"{Path(session_id).name}.jsonl"
    return read_jsonl(path) if path.is_file() else []
```

The format is not the main lesson. The important decisions are:

- one explicit session ID
- load at session construction
- save after a completed turn
- sanitize IDs before turning them into paths
- make writes crash-safe

Gemma writes to a temporary file and replaces the old file atomically.

```python
with os.fdopen(file_descriptor, "w") as session_file:
    for message in messages:
        session_file.write(json.dumps(message) + "\n")

os.replace(temporary_path, session_path)
```

If the process dies during the write, the previous good session stays intact.

JSONL is a nice teaching baseline and works for one local user. A multi-user or high-concurrency product will probably need database transactions, access control, migrations, and retention rules.

## Retrieval can start boring

The video groups keyword search with durable sessions in Chapter 9. In the current `~/gemma` source, `harness/memory.py` labels episodic retrieval as a later Chapter 16 addition. That difference is useful: persistence and retrieval are separate capabilities even when one lesson explains them together.

Gemma's later memory search uses keyword overlap across saved sessions.

```python
terms = query.lower().split()
score = sum(term in message_text for term in terms)
```

That is not semantically clever, but it is transparent and easy to debug. Start there if it meets the recall need.

Move to embeddings, reranking, graph traversal, or hybrid search when evaluation shows keyword search missing useful material. Do not start with an expensive retrieval stack because memory sounds advanced.

## Stored text is not automatically truth

A transcript can contain:

- a user correction
- an old fact
- a model guess
- a failed tool result
- untrusted web content
- a verified database response

Those should not become equal facts just because they share one JSONL file.

Useful memory records carry:

- source
- kind
- timestamp
- confidence
- current or superseded status
- tenant or user scope
- privacy level

## Forgetting is part of the design

Keep raw history when audit needs it, but do not keep loading old material into every prompt.

| Memory | Sensible treatment |
|---|---|
| Current messages | Compact or trim |
| Session history | Retain by policy, retrieve selectively |
| Current facts | Supersede old values, keep provenance |
| Procedures | Version and review after rule changes |
| Sensitive traces | Redact and expire |

Deletion also matters. A user should be able to remove their saved sessions and personal facts.

## HaxJobs case study

Current HaxJobs state is SQLite plus `state/profile.json`. That is the present implementation.

The planned career graph would provide stronger semantic memory for career tracks, skills, evidence, applications, interviews, and learning progress. It is not built yet.

The model should never receive the whole future graph. The harness should retrieve the small track and evidence slice needed for the current action.

## In plain English

- Working history is replayed messages. Durable state survives a restart.
- Resuming one session and searching older memory are different operations.
- Saving everything does not make it trustworthy or relevant.
- Start with simple storage and retrieval, then measure where it fails.
- Preserve source and history so old guesses do not quietly become current facts.
