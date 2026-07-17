# HaxJobs design discussion

This folder is the running record for product and agent-design conversations.

- `NNN-*.md` captures one concept at a time.
- Each note separates **decided direction**, **working proposals**, and **open questions**.
- A decided direction records the current agreement. It is not permanently final and can change when later design or implementation teaches us something better.
- Nothing becomes an implementation requirement until the user explicitly decides it.
- Notes should describe the product behaviour first. Tables, classes, schemas, and code come later.
- `research/` holds supporting evidence. Research findings stay provisional until the main discussion accepts them as decisions.
- Each decided design stage should gain a clean visual under `diagram/` when a diagram would make the model easier to understand.

## Greenfield design rule

HaxJobs is being designed and built from scratch.

- The current routes, services, tables, tools, prompts, UI, names, and architecture do not constrain the new design.
- Nothing from the current product is kept merely because it already exists.
- Existing code can only be reused later if it independently fits the decided design.
- The old database is a source of development data only. Its schema, identifiers, statuses, and relationships must not shape the new data model.
- Any imported development data will pass through an explicit one-way translation into the new model.

## Current evidence

- [2026 job-search patterns](research/2026-job-search-patterns.md)
- [Pi and Hermes study for a job-native HaxJobs architecture](research/2026-07-17-pi-hermes-job-native-harness-study.md)

## Design method

The first two notes establish the foundation:

1. [Hax's goal and rudimentary run lifecycle](001-hax-goal-and-run-lifecycle.md)
2. [Durable work and continuity](002-durable-work-and-continuity.md)

The active method now follows the harness-primitives build:

```text
minimal Hax harness
-> real job fixture
-> saved run and evaluation
-> one explainable harness change
-> rerun the same fixture
```

We still design through real employment work, but the job scenario is an evaluation for Hax rather than a reason to model the whole product before Hax runs.

## Decided harness foundation

4. [Minimal job-native harness](004-minimal-job-native-harness.md) (decided)
5. [Implementation stack, observability, and verification](005-implementation-stack-observability-and-verification.md) (decided)

## Active discussion

(None — all active architecture decisions for Stage 0/1 are settled.)

## Decided architecture for greenfield build

6. [Pi-inspired HaxJobs architecture](006-pi-inspired-haxjobs-architecture.md) (four-layer split and one-package decided for Stage 0/1; coding/document/bash workspaces remain open for later)

## Paused discussion

3. [Company watch from request to outcome](003-company-watch-vertical-slice.md) (paused)

Its accepted user-facing behaviour remains useful input. Its proposed domain objects and future rounds do not define the architecture.

Accepted choices, observations, and unresolved questions stay in the Markdown notes so chat history is never the only record.
