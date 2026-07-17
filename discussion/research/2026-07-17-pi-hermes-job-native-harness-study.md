---
title: Pi and Hermes study for a job-native HaxJobs architecture
status: working reference
created: 2026-07-17
updated: 2026-07-17
scope: Converged source study, architectural findings, HaxJobs mapping, and planning guardrails
source_commits:
  pi: 3da591ab74ab9ab407e72ed882600b2c851fae21
  hermes: 9e1b1d7536270b4e2bf56662903acfbfc54ac937
related:
  - ../004-minimal-job-native-harness.md
  - ../005-implementation-stack-observability-and-verification.md
  - ../006-pi-inspired-haxjobs-architecture.md
---

# Pi and Hermes study for a job-native HaxJobs architecture

This is the durable technical reference for the Pi and Hermes architecture study.

It brings the disposable `/tmp` research into one place, removes reviewer noise, separates shipped behaviour from design documents, and maps the useful parts to the greenfield HaxJobs design.

This file should be read before planning or implementing the new agent runtime.

# Ground rules

## HaxJobs is greenfield

The current HaxJobs routes, tables, prompts, tools, service names, UI, and storage layout do not constrain this design.

Existing code may be reused later if it independently fits the agreed design. The old database is only development data that may be translated one way into a new model.

So references in the source studies to existing HaxJobs modules or tool names are historical observations, not architectural decisions.

## HaxJobs and Hax are different things

- **HaxJobs:** the job-search-native agent system around the model.
- **Hax:** the agent the user experiences.

HaxJobs owns context delivery, tools, permissions, events, durable work, evidence, verification, retries, and interfaces.

Hax reasons and converses inside those boundaries.

## The immediate experiment remains small

The architecture may eventually support conversations, coding workspaces, sessions, compaction, skills, sub-agents, and long-running operations.

The first experiment still stays controlled:

```text
Stage 0
  Job 49, then Job 328
  frozen career fixture
  no tools
  one observed model call

Stage 1
  same fixtures
  one tool: inspect_job_source(job_ref)
  bounded model -> tool -> model loop
```

Nothing in this study authorizes building the future runtime all at once.

# Sources and confidence

## Pi

Studied repository commit:

[`3da591ab74ab9ab407e72ed882600b2c851fae21`](https://github.com/earendil-works/pi/tree/3da591ab74ab9ab407e72ed882600b2c851fae21)

Primary material:

- `packages/agent/src/agent-loop.ts`
- `packages/agent/src/agent.ts`
- `packages/agent/src/types.ts`
- `packages/agent/src/harness/`
- `packages/agent/docs/`
- `packages/agent/test/`
- `packages/coding-agent/src/core/`
- `packages/coding-agent/docs/`

The commit was checked directly from the local clone. Findings are source and test attested. The Pi test suite was not rerun as part of the read-only study.

## Hermes

Studied repository commit:

[`9e1b1d7536270b4e2bf56662903acfbfc54ac937`](https://github.com/NousResearch/hermes-agent/tree/9e1b1d7536270b4e2bf56662903acfbfc54ac937)

Primary material:

- `run_agent.py`
- `agent/conversation_loop.py`
- `agent/turn_context.py`
- `agent/turn_finalizer.py`
- `agent/prompt_builder.py`
- `agent/context_engine.py`
- `agent/context_compressor.py`
- `agent/memory_manager.py`
- `tools/registry.py`
- `tools/approval.py`
- `tools/delegate_tool.py`
- focused tests and developer guides

The Hermes test suite was not rerun as part of the source study.

## How to read claims in this file

- **Verified runtime pattern:** present in checked source and usually covered by tests.
- **Documented design:** described by the project but missing or incomplete in runtime code.
- **HaxJobs recommendation:** our current judgement. It still needs acceptance during discussion.
- **Deferred:** useful later, not part of Stage 0 or Stage 1.

# The smallest useful agent system

Strip away every UI, plugin, memory provider, scheduler, and provider integration. The useful core looks like this:

```text
user or host sends input
        |
        v
host prepares one turn snapshot
        |
        v
model receives messages and active tools
        |
        v
model returns text or tool calls
        |
        +---- text ----> final response
        |
        +---- tool call
                |
                v
        validate and authorize
                |
                v
          execute normal code
                |
                v
        append tool result
                |
                v
          call model again
```

That loop is the agent runtime.

Everything else decides:

- what the model sees
- what tools it can call
- what survives after the call
- what actions require approval
- how failures are recorded
- how a later interface receives progress

Pi gives the cleaner small-loop shape. Hermes gives useful Python boundaries around turn setup, completion, tool registration, and approvals.

# Part 1: Pi's architecture

## Pi has a real domain split

The current Pi repository separates three concerns:

```text
pi-ai
  models, providers, streams, usage, provider message formats

pi-agent-core
  app messages, model/tool loop, tool validation, events, cancellation

pi-coding-agent
  coding identity, filesystem and shell tools, resources, sessions,
  extensions, project trust, compaction, CLI, TUI, RPC, SDK
```

This matters because the generic agent loop does not know what `read`, `bash`, or `edit` mean.

The coding layer supplies those capabilities.

That is the right broad shape for HaxJobs:

```text
model boundary
agent core
employment layer
interfaces
```

We can keep this inside one Python package until a physical split solves a real problem.

## Pi actually exposes three runtime levels

Pi does not have one single `Agent` abstraction.

### Low-level loop

The functional loop accepts a context snapshot and configuration, streams model output, executes tools, emits events, and returns new messages.

It has no storage, UI, coding prompt, or resource loader.

### Agent

`Agent` adds mutable in-memory state:

- current model
- system prompt
- transcript
- tools
- steering queue
- follow-up queue
- abort controller
- event subscribers

It is useful for simple in-memory use.

### AgentHarness

`AgentHarness` calls the low-level loop directly. It adds:

- persisted session context
- model collection
- resource loading
- tool registration and activation
- system-prompt resolution
- turn snapshots
- save points
- compaction and branch operations

The checked Pi design has some overlap between `Agent` and `AgentHarness`. HaxJobs should avoid copying both wrappers.

**HaxJobs recommendation:** one `EmploymentAgent` or similarly named host around one small loop. Add a separate session service only when sessions become real.

## Pi's loop lifecycle

The checked low-level loop does this:

1. Start the agent run.
2. Inject queued steering messages before the next model request.
3. Emit a turn-start event.
4. Stream one assistant response.
5. Stop immediately on provider error or abort.
6. Collect tool calls from the assistant response.
7. Validate and execute the tool batch.
8. Append tool-result messages in assistant source order.
9. Emit turn end.
10. Optionally build a fresh next-turn snapshot.
11. Optionally stop after the completed turn.
12. Poll steering messages.
13. When the model would stop, poll follow-up messages.
14. End when there are no tool calls or queued messages.

Source: [Pi agent loop](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L155-L274).

### Why this matters for HaxJobs

The loop is not where career logic belongs.

The loop only decides whether to:

- call the model
- run a requested tool
- feed the result back
- stop

Job discovery, source inspection, fit reasoning, evidence work, project creation, and application handling live behind tools or deterministic host steps.

## Internal messages and provider messages are separate

Pi applies two transformations before a provider call:

1. Transform application-level messages.
2. Convert those messages to the provider-compatible representation.

Only then does it build the final provider context.

Source: [Pi model-call boundary](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L275-L318).

This is one of the strongest patterns to copy.

HaxJobs will eventually hold things that should not all enter the prompt:

- user messages
- assistant messages
- tool calls and results
- approval requests
- operation state changes
- source observations
- private evidence references
- delivery receipts
- model usage
- warnings and retries

The model receives a selected projection, not the full storage log.

## The turn snapshot is frozen

Pi's higher harness builds a turn snapshot containing:

- persisted messages
- resources
- stream options
- session ID
- system prompt
- model
- thinking level
- all tools
- active tools

Source: [Pi turn-state construction](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/harness/agent-harness.ts#L314-L372).

A model request sees one stable snapshot.

If the model, prompt, tools, profile, or approval state changes during a turn, the current request does not mutate underneath it. The next request receives the new snapshot at a save point.

### HaxJobs rule

```text
one model request = one immutable view of the world
```

Changes become visible at the next safe boundary.

## Save points define ordering

Pi persists completed assistant and tool messages, flushes pending session changes, emits a save point, and only then prepares another provider call.

Source: [Pi save-point handling](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/harness/agent-harness.ts#L438-L542).

This gives a clear ordering rule:

```text
completed model output
-> completed tool effects
-> durable writes
-> save point
-> next turn snapshot
-> next provider call
```

HaxJobs will need this when a turn records decisions, creates evidence, changes operation state, or waits for approval.

Stage 0 only has one call, so the implementation can be tiny while keeping this future boundary visible.

## Tool execution is a trust boundary

Pi's tool definition contains:

- name
- label and description
- input schema
- execute function
- streaming update callback
- optional sequential execution requirement

The loop:

1. Finds the named tool.
2. Optionally normalizes arguments.
3. Validates arguments against the schema.
4. Runs a pre-tool hook.
5. Stops if the hook blocks the call.
6. Executes the tool.
7. Catches exceptions.
8. Runs a result hook.
9. emits one tool-result message.

Source: [Pi tool preparation](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L519-L585) and [Pi tool execution](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L587-L675).

### Truncated tool calls are not executed

If the provider response stops because of output length, Pi fails every tool call in that response. Parsed arguments may look valid while still being incomplete.

That is a good safety rule.

### Parallel execution keeps result order

Pi can execute independent tools in parallel, but tool-result messages are appended in the original order from the assistant message.

That protects protocol ordering even when completion times differ.

### One sequential tool makes the batch sequential

A tool may mark itself sequential. If any call in the batch needs that mode, Pi executes the full batch sequentially.

For HaxJobs, application submission, outbound messaging, or mutation-heavy actions should never be part of speculative parallel execution.

### Explicit termination

Pi tools may return `terminate=true`. A parallel batch ends the loop only when every finalized call in that batch requests termination.

There is also a `shouldStopAfterTurn` boundary after the turn completes.

Source: [Pi tool-batch termination](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L499-L517).

HaxJobs should keep a clean stop contract available. Stage 1 may only need "model returned no tool calls" plus a step limit.

## Events and hooks do different jobs

Pi has two broad mechanisms.

### Lifecycle events

Examples:

- agent start and end
- turn start and end
- message start, update, and end
- tool execution start, update, and end
- tool-result message

These describe what happened.

### Hooks

Examples:

- transform context
- block a tool
- patch a tool result
- change provider request options
- intervene in compaction

These may affect execution.

### HaxJobs rule

```text
observers watch
policies decide
```

A JSONL writer or future telemetry subscriber must never change the result of a run because it failed.

A policy check may block a real action.

## Some Pi hook designs are not fully shipped

Pi's docs describe richer reducers, provenance, cleanup, facades, and generic hook composition than the checked implementation currently provides.

The runtime has useful concrete hooks, but parts of the generic hook system remain design work. Provider transformations chain in registration order, while most current `emitHook` calls keep the last non-empty result. The typed reducers described in the hook design are not generally implemented yet.

Source: [Pi harness hook dispatch](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/harness/agent-harness.ts#L231-L292) and [Pi hook design](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/docs/hooks.md#L1-L84).

**HaxJobs recommendation:** implement only named boundaries that real runs need:

- before model call
- before tool execution
- after tool execution
- save point
- run completion
- later, compaction preparation

Do not build a general extension hook language yet.

## Context is a projection over durable truth

Pi sessions may retain full branch history while the model sees only the latest compaction summary plus recent entries.

Configuration state may still be derived from the full branch even when older conversation messages are hidden from the model.

That gives an important distinction:

```text
stored truth != model-visible context
```

For HaxJobs:

- career facts remain career facts
- source observations retain provenance
- job records remain job records
- commitments retain their state
- the prompt receives only the useful slice for this turn

Compaction must never become the only copy of a career fact or user decision.

## Pi compaction

The checked Pi compactor:

- estimates current context pressure
- reserves output space
- selects a safe cut point
- never starts retained history at an orphaned tool result
- supports oversized split turns
- can include an earlier summary in the next summary
- stores a compaction entry rather than deleting history
- retains recent messages verbatim

The coding layer defaults include a structured summary covering goals, constraints, progress, decisions, next steps, critical context, and tracked files.

HaxJobs already chose a similar vacation-handoff summary shape:

- goal
- constraints and locked decisions
- progress
- key files and facts
- next step

### Important implementation truth

In the checked generic Pi harness, automatic compaction and retry decisions are still incomplete or manually triggered in places. The design is stronger than the shipped automation.

### HaxJobs activation trigger

Do not implement compaction for Stage 0 or Stage 1.

Add token tracking first. Add compaction when real sessions approach a defined fraction of the model context window and evaluation shows history pressure is hurting quality.

## Pi session storage

Pi uses append-only versioned JSONL entries with IDs and parent IDs. It can:

- replay a conversation
- branch from an earlier point
- label entries
- record model and thinking-level changes
- retain compaction entries
- reconstruct an active leaf

This is useful for coding conversations where branching is a first-class feature.

### What HaxJobs should borrow

- append-only audit thinking
- explicit IDs
- reconstructable state changes
- no silent history rewriting

### What HaxJobs should not assume

- career truth belongs in a conversation tree
- branching is required from day one
- JSONL should be the final database
- a persisted transcript gives exactly-once effects

Career memory, operations, jobs, approvals, and outcomes need their own records. A transcript is not the product model.

## Pi is only semi-durable

Pi's durability design openly says full crash recovery is not currently guaranteed.

Current pending writes and queues can live in memory. Provider streams cannot resume from the middle. Unfinished non-idempotent tool calls cannot be retried safely without extra records and policy.

HaxJobs must never infer that append-only messages equal safe external effects.

Before an irreversible action, the system eventually needs:

- durable operation state
- exact approval correlation
- an idempotency key where the external service supports it
- a started or attempted effect record
- recovery rules
- no blind retry for non-idempotent calls

## Pi observability is partly design work

Pi's observability document proposes:

- trace IDs
- span IDs
- parent span IDs
- safe metadata by default
- runtime-neutral event consumers
- separation of passive telemetry from control hooks

At the checked commit, the full generic observability package described by the document is not present as finished runtime code.

HaxJobs should copy the principles, not wait for Pi's implementation.

Stage 0 already chose:

- local redacted JSONL
- Python logging
- one run manifest
- no telemetry server

## Pi prompts, resources, and skills

Pi resolves its system prompt outside the loop. The coding layer builds the final prompt from:

- coding identity
- active tool guidance
- project context files
- system additions
- skills metadata
- current working directory

The shape is useful. The text is coding-specific.

### Skills use progressive loading

Pi puts skill names and descriptions in the initial prompt. Full skill instructions are loaded only when selected, often through the `read` tool or an explicit skill command.

HaxJobs may later use the same progressive-loading idea for reviewed employment procedures.

Do not require general filesystem access just to load a skill. A narrow resource loader can return approved skill content.

## Pi testing patterns

Pi's tests use scripted fake providers. They verify:

- event order
- context transform before provider conversion
- unknown and invalid tool calls
- tool blocking
- parallel result ordering
- awaited subscribers
- save-point refresh
- provider option snapshots
- storage parity
- malformed storage rejection
- compaction cut boundaries

This is exactly the right test shape for HaxJobs.

A useful first verification floor:

```text
one fake-model no-tool run
one fake-model tool run
one invalid-arguments run
one blocked-tool run
one provider-error run
one event-order assertion
one redaction assertion
```

# Part 2: Pi's coding layer

## Tool catalogue

Pi's coding layer registers seven tools:

- `read`
- `bash`
- `edit`
- `write`
- `grep`
- `find`
- `ls`

It defines:

- default coding tools: `read`, `bash`, `edit`, `write`
- read-only tools: `read`, `grep`, `find`, `ls`
- all tools: all seven

Source: [Pi coding tool registry](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/index.ts#L50-L155).

The separation between the complete registry and active subset is reusable.

The permissive default is specific to an attended local coding session.

## `read`

Pi's `read` tool:

- resolves local paths
- reads text and images
- attaches supported images to model messages
- truncates text around 2,000 lines or 50 KB
- tells the model to use it instead of shelling out to `cat` or `sed`

Useful HaxJobs places:

- CV and certificate intake
- transcript inspection
- exported profile data
- application-answer documents
- employability project repositories

Required changes:

- selected roots only
- resolved path containment
- symlink checks
- privacy classification
- content limits
- no access to provider credentials or canonical internal state

Source: [Pi read tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/read.ts#L213-L330).

## `grep`

Pi uses ripgrep, respects ignore rules, returns path and line matches, and truncates results.

Useful HaxJobs places:

- finding evidence inside a project
- searching several user-selected documents
- locating a technology or claim in a repository

It should remain read-only and bounded.

Source: [Pi grep tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/grep.ts#L124-L319).

## `find`

Pi uses `fd` or injected glob operations, respects ignore rules, and returns paths relative to the workspace.

Useful HaxJobs places:

- discovering project files
- finding uploaded evidence documents
- locating tests, READMEs, or certificates

Again, selected roots only.

Source: [Pi find tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/find.ts#L107-L323).

## `ls`

Pi reads one directory, includes dotfiles, sorts entries, and marks directories.

Useful for workspace orientation.

It should not become general home-directory enumeration.

Source: [Pi ls tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/ls.ts#L95-L191).

## `write`

Pi creates parent directories and overwrites the target under a per-file mutation queue.

Useful HaxJobs places:

- creating employability project files
- writing controlled application artifacts
- writing user-approved notes to an output workspace

It must not directly mutate career records or operation state.

Source: [Pi write tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/write.ts#L203-L256).

## `edit`

Pi's edit tool:

- requires exact unique replacements
- rejects overlapping edits
- preserves BOM and line endings
- records a patch
- serializes mutations per file

This is a good model for project editing. Exact replacements are inspectable and reduce accidental rewrites.

Useful HaxJobs places:

- coding projects
- controlled CV or cover-letter source artifacts
- portfolio content

It still needs workspace boundaries and mutation history.

Source: [Pi edit tool](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/edit.ts#L270-L356).

## `bash`

Pi launches the user's shell in the current working directory, streams stdout and stderr, supports cancellation and timeout, kills process trees, and retains tail output with a temp-file fallback.

This is powerful because it is basically host-user authority.

A shell can bypass most application restrictions:

- read any accessible file
- alter career storage
- read credentials
- call external APIs
- send data
- install packages
- start background processes
- execute generated code

A path check inside the shell wrapper does not contain shell commands.

### HaxJobs boundary

For attended local project work:

- explicit project-workspace activation
- clear disclosure
- selected working directory
- time and output limits
- no automatic external-action permission

For unattended or cloud work:

- real container, VM, or similar OS boundary
- selected project mount only
- minimum credentials
- controlled network access
- process, time, disk, and output limits
- clean termination and artifact capture

Pi's own security documentation says project trust is not a sandbox.

Sources: [Pi bash execution](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/bash.ts#L289-L413) and [Pi security model](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/docs/security.md#L1-L70).

## Tool selection

Pi's SDK supports:

- explicit tool allowlists
- no-tools modes
- exclusions
- active tool changes
- custom and extension tools

Source: [Pi session creation](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/sdk.ts#L215-L225).

HaxJobs should copy the registry-versus-active-set distinction.

Capability selection should happen at the operation boundary, not through a single global all-tools switch.

## Resource loading

Pi's coding layer loads:

- extensions
- skills
- prompt templates
- themes
- context files
- system prompts
- package resources

The useful pattern is one loader with provenance and diagnostics.

Sources: [Pi resource-loader contract](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/resource-loader.ts#L27-L47) and [Pi resource reload](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/resource-loader.ts#L317-L466).

The parts to avoid for now:

- npm or git package installation
- executable third-party extensions
- theme loading in the agent runtime
- project-directory conventions copied from coding agents
- recursive resource discovery without a product need

## Extensions

Pi extensions may register tools, commands, shortcuts, providers, UI rendering, and event handlers. They run with full user permissions.

Sources: [Pi extension loader](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/extensions/loader.ts#L174-L365) and [Pi extension security note](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/docs/extensions.md#L31-L43).

This is good for a developer-controlled terminal tool. It is too broad for the first HaxJobs runtime.

HaxJobs may later need connector plugins for Gmail, WhatsApp, Telegram, browsers, or job sources. That does not justify a general plugin API yet.

Start with normal Python registration. Extract a plugin boundary when a second independently installed connector proves the need.

## Project trust

Pi's project trust decides whether local project resources may load.

It does not restrict tool behaviour after startup.

HaxJobs needs separate ideas:

- resource trust
- data privacy
- tool capability
- external-action approval
- execution isolation

One trust toggle must not stand in for all five.

## Session composition root

Pi's `createAgentSession()` wires:

- current directory
- model runtime
- settings
- session manager
- resource loader
- model restore
- active tools
- image policy
- provider hooks
- context hooks
- final session wrapper

This is the coding-layer composition root.

Source: [Pi session composition](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/sdk.ts#L135-L390).

HaxJobs will eventually need a smaller equivalent that assembles one employment-agent session or operation from injected services.

Do not start by building the final composition root. Stage 0 only needs enough wiring for one fixture, one prompt, one provider adapter, one trace sink, and one result.

# Part 3: Hermes architecture

## Hermes' useful spine

Ignore the 70-plus tools, gateway support, provider breadth, terminal systems, memory providers, and plugin surface.

The useful runtime shape is:

```text
host-neutral agent object
canonical message list
prepare one turn
bounded model/tool loop
strict tool registry
turn finalizer
structured result
```

Hermes is useful because it implements this in Python, the language HaxJobs chose.

## Thin host object

Hermes' public `AIAgent` forwards setup and conversation work into named modules. The actual loop accepts the prepared agent state plus input/history and produces one structured result.

Sources:

- [Hermes agent host](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/run_agent.py#L346-L449)
- [Hermes run boundary](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/run_agent.py#L6185-L6247)
- [Hermes conversation loop](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/conversation_loop.py#L607-L667)

HaxJobs should expose one host-neutral turn API used by CLI, web, and worker adapters.

## Turn preparation

Hermes has a `TurnContext` that names data crossing from setup into execution.

Turn preparation handles things such as:

- turn IDs
- counters
- early user-message persistence
- prompt assembly
- context-pressure checks
- plugin context
- memory prefetch

Sources:

- [Hermes TurnContext](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/turn_context.py#L92-L120)
- [Hermes turn builder](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/turn_context.py#L121-L169)

This is a good future seam for HaxJobs once a turn genuinely needs several inputs.

Do not create a giant context object for Stage 0.

## Canonical history with temporary overlays

Hermes copies canonical history for the provider call, injects temporary memory or plugin context into the copy, and leaves stored history unchanged.

Source: [Hermes provider-context copy](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/conversation_loop.py#L849-L928).

This maps directly to HaxJobs:

- selected career evidence may be relevant this turn
- current job facts may be relevant this turn
- a fetched company page may be relevant this turn
- none of that automatically becomes permanent conversation history

The model desk is temporary. Durable truth lives elsewhere.

## Strict tool registry

Hermes centralizes:

- name
- schema
- handler
- availability
- toolset membership
- result normalization
- dispatch failure handling

Source: [Hermes registry contract](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/tools/registry.py#L84-L113).

The narrow contract is useful.

The current Hermes registry also contains machinery HaxJobs does not need yet:

- AST auto-discovery
- availability TTL caches
- transient failure grace
- dynamic schema overrides
- plugin shadowing
- many toolsets
- MCP refresh generations

Use explicit Python registration first.

## Prompt layers and trust

Hermes keeps prompt-builder functions stateless and separates cached system material from request-only overlays.

That supports the three-tier HaxJobs prompt direction:

```text
stable
  Hax identity, safety, evidence rules

flow
  job review, research, project work, application preparation

volatile
  current request, selected career evidence, current job/company data
```

Fetched pages are untrusted data. They do not become system instructions.

The stable prefix should remain byte-for-byte stable where possible for provider caching.

## Context compression

Hermes defines a context-engine contract around:

- token accounting
- deciding when to compress
- compression
- session lifecycle

Its default compressor adds a lot:

- LLM summaries
- stale-task defences
- media stripping
- deterministic fallbacks
- cooldown persistence
- session rebinding

The contract is useful later. The default implementation is far beyond Stage 0 and Stage 1.

HaxJobs should first measure token use and failure patterns. Then build one compaction function when needed.

## Memory, session history, and skills are different

Hermes distinguishes:

- durable user facts and preferences
- past session outcomes
- reusable procedures

That maps well to HaxJobs:

```text
career memory
  facts, evidence, preferences, constraints, goals

interaction and operation history
  what happened, what was tried, decisions, outcomes

skills
  reviewed procedures for repeated work
```

Do not turn all three into one vector store or one transcript.

## Delegation

Hermes sub-agents start with fresh context, restricted tools, separate budgets, and return summaries rather than full internal transcripts.

By default, children cannot freely write shared memory, contact users, schedule work, or recursively delegate.

Source: [Hermes delegation boundaries](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/tools/delegate_tool.py#L1-L106).

Useful future rules:

- fresh child context
- explicit task input
- reduced tools
- reduced data access
- bounded turns and budget
- structured result
- no external effects
- parent decides what becomes durable

Delegation is not needed for the first job review experiment.

## Approval at the action boundary

Hermes correlates approvals with concurrent execution context and keeps a hard safety floor beneath override modes.

Source: [Hermes approval context](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/tools/approval.py#L1-L85).

HaxJobs needs a simpler employment-specific rule:

```text
read, search, inspect, reason, draft
  no per-call approval

submit, send, connect, publish, represent the user externally
  exact approval tied to the exact action
```

Approval belongs below the prompt, immediately before the side effect.

A system instruction saying "ask the user first" is not enforcement.

## Turn finalization

Hermes converges post-loop work in one finalizer:

- save state
- collect usage
- record exit reason
- run cleanup
- emit diagnostics
- return one structured result
- schedule optional post-response work

Sources:

- [Hermes finalizer setup](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/turn_finalizer.py#L29-L49)
- [Hermes result assembly](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/turn_finalizer.py#L424-L493)

HaxJobs should return a structured run result, even if Stage 0 starts small.

Possible fields:

- run ID
- final text
- exit reason
- model
- tool calls
- usage if available
- errors
- trace path
- verification status

## Observability

Hermes records per-iteration state and a final diagnostic containing:

- exit reason
- provider and model
- call count
- budget
- tool turns
- final role
- response length
- session ID

HaxJobs can do less:

```text
run_id
turn_id
operation_id if one exists
model
phase
event kind
tool name
start/end/error
duration
approval state
safe size/count metadata
```

Private prompts, CV text, tool arguments, tool results, credentials, and provider bodies stay out by default.

## Hermes drift warning

The checked Hermes source contains naming and documentation drift.

One `on_session_end` boundary means a real session ending. Another hook with the same name runs after a single conversation call. Compression thresholds also differ between docs and generic defaults.

HaxJobs should use names that match the real boundary:

- `turn_finished`
- `conversation_closed`
- `operation_paused`
- `operation_completed`
- `session_closed`

Where practical, runtime constants and docs should be tested together.

# Part 4: HaxJobs architecture mapped from the study

## Proposed layers

```text
interfaces
  CLI now, web later, worker later
        |
        v
employment host
  prepares work, context, capabilities, policy, result
        |
        v
agent core
  messages, bounded loop, tools, events, cancellation, save points
        |
        +---- model boundary
        |
        +---- tool registry
                    |
                    v
            employment actions and scoped workspaces
```

## Layer 1: model boundary

Responsibilities:

- one small model protocol
- provider adapter
- scripted fake provider
- normalized text and tool calls
- stop reason
- usage when available
- provider metadata
- provider-specific options kept local

No career logic.

### Stage 0 need

- one configured-provider adapter, initially tested against the current DeepSeek-compatible endpoint
- scripted fake
- text response
- provider error
- usage if returned

### Stage 1 addition

- normalized tool calls
- assistant tool-call message representation
- tool-result messages

## Layer 2: agent core

Responsibilities:

- internal message types
- provider-message projection
- bounded model/tool loop
- tool validation
- active tool selection
- cancellation
- lifecycle events
- step limit
- final result
- later save points, steering, follow-up, and compaction seams

No company logic. No CV logic. No fit-scoring rules.

## Layer 3: employment layer

Responsibilities:

- Hax identity
- employment instructions
- career-context selection
- evidence provenance
- operation or work-type context
- capability selection
- approvals
- durable state coordination
- later skills and commands

This is the main job-native layer. It owns two kinds of capability.

### Employment actions

Actions express product meaning:

- inspect a job source
- research a company
- retrieve relevant evidence
- assess fit
- identify missing evidence
- propose an evidence project
- record a decision
- prepare application material
- track an application
- prepare interview practice
- maintain a company watch

These names are examples. Real runs should decide the final catalogue.

### Generic workspace tools

Tools manipulate files and processes:

- read
- grep
- find
- ls
- write
- edit
- bash

They become useful when Hax is working with documents or helping build evidence projects.

## Layer 4: interfaces

The CLI, web app, and future worker call the same employment host.

They may differ in:

- input and output rendering
- streaming transport
- approval interaction
- background delivery

They must not each implement their own agent loop or career rules.

# Capability sets

These are permission bundles. They are not intent categories and should not narrow model reasoning.

One interaction may create several operations with different capability sets.

| Capability set | Likely tools | Main use |
|---|---|---|
| Conversation | None or selected read-only career context | Discuss, clarify, explain |
| Career records | Typed career, evidence, decision, and outcome actions | Read or change canonical career state |
| Job research | Search, fetch, inspect source, company and job actions | Verify employment information |
| Document intake | Read-only selected-file tools and document parsers | Understand user material |
| Application preparation | Typed pack and artifact actions | Create controlled application material |
| Project workspace | Pi-like filesystem tools plus controlled bash | Build and verify employability evidence |
| External effects | Submit, send, connect, publish | Exact approval every time |

## Registered tools and active tools

```text
registered catalogue
  everything the runtime knows how to execute

active set
  only what this operation may call now
```

A model should never receive a tool merely because it exists.

The host chooses the active set using:

- current operation
- user-selected workspace
- safety policy
- approval state
- execution environment
- budget

# Coding tools are part of the employment product

The initial coding-layer review recommended excluding generic coding tools from HaxJobs product work. Arinze corrected that boundary. The current working direction is scoped document and employability-project workspaces, while canonical career state remains behind typed employment actions. That earlier narrow recommendation is superseded.

HaxJobs is not a coding agent. That does not make coding tools irrelevant.

If a user lacks evidence for a role, Hax may help them complete a real project. That project can produce:

- code
- tests
- architecture notes
- a deployed demo
- a repository history
- a verified skill claim
- interview material

The employment goal gives the coding work meaning.

## Document workspace

Purpose:

- inspect CVs and application documents
- read certificates and transcripts
- inspect portfolio exports
- compare user evidence with a job

Recommended initial tools:

- `read`
- `ls`
- `find`
- `grep`
- domain parsers such as PDF or document extraction

Boundary:

- explicit uploads or selected roots
- read-only by default
- no provider credentials
- no hidden application state
- resolved path containment
- symlink-safe checks
- content limits

## Employability project workspace

Purpose:

- create or improve a real evidence project
- run code and tests
- verify the project before recording a claim

Recommended tools:

- `read`
- `grep`
- `find`
- `ls`
- `write`
- `edit`
- `bash`

Boundary:

- explicitly selected project root
- project-specific objective
- tracked mutations
- bounded output
- verification after changes
- no direct career-state mutation
- no external sending or submission rights

## Career state stays typed

Generic file tools should not rewrite:

- profile facts
- evidence claims
- constraints
- decisions
- applications
- standing commitments
- approvals
- outcomes

Those changes need typed employment actions so the system can enforce provenance, validation, history, and approval rules.

## Shell activation rule

A future attended local mode may activate `bash` for a selected project.

An unattended or cloud mode must use real isolation first.

No prompt rule can replace an OS boundary.

# Message and result contracts

Exact Pydantic models belong in an implementation plan. The architecture needs the shape first.

## Internal message

Needs enough information to represent:

- role or kind
- content parts
- tool-call IDs
- tool-result linkage
- timestamps
- safe metadata
- provider projection rules

It should not be identical to one provider's request format.

## Tool definition

Needs:

- name
- description
- Pydantic input model
- output model or result contract
- handler
- side-effect class
- capability requirement
- execution mode
- retry safety
- result-size limit
- availability check only when a real dependency requires one

## Tool result

Needs one stable success and failure shape.

Example direction:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "metadata": {}
}
```

or:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "source_unavailable",
    "message": "The trusted job source could not be reached."
  },
  "metadata": {}
}
```

The exact envelope remains open. The invariant is not open: every tool returns a predictable result.

## Run result

Likely needs:

- run ID
- conversation or interaction ID when those exist
- final assistant content
- exit reason
- model
- turns used
- tool calls
- usage
- errors
- trace reference
- verification status
- pending approval or later-work reference when relevant

Stage 0 can implement a small subset without inventing every future identifier.

# Stop, retry, and cancellation

## Normal stop

The model returns a response with no tool calls.

## Step limit

The host stops after the configured maximum number of model turns.

The result must say the limit was reached rather than pretending the task completed.

## Tool-requested stop

Keep room for a tool result to say that the operation has reached a terminal boundary.

Do not add it until a real tool needs it.

## Provider retry

Retry only failures known to be safe and transient.

A model request has no employment-side effect, but a retry can still charge twice, produce a different answer, duplicate streamed output, or repeat after the provider completed while the client lost the response. Provider retries must be bounded, budget-aware, and limited to known transient failure classes.

## Tool retry

Each tool should declare whether retry is safe.

Read-only source inspection may be retryable.

Application submission is not blindly retryable.

## Cancellation

Cancellation should stop new work and signal active model or tool execution.

It cannot pretend an already completed external action did not happen.

# Context assembly

Context assembly is where HaxJobs becomes job-native.

The loop remains generic. The employment host decides what reaches the model.

## Stable tier

Examples:

- who Hax is
- employment goal
- evidence and truth rules
- approval rules
- source-trust rules
- tool-use rules

Keep this stable for provider caching.

## Flow tier

Examples:

- reviewing a job
- researching a company
- building a project
- preparing an application
- practising an interview

## Volatile tier

Examples:

- current user request
- selected career track
- relevant constraints
- selected evidence
- current job data
- recent decisions
- current operation state

## Temporary tool context

Fetched pages and tool results enter as untrusted observations.

They may influence reasoning. They do not override system rules or automatically become durable truth.

## Context manifest

For repeatable experiments, record versions or hashes for:

- app commit
- prompt version
- model and provider
- active tools
- policy version
- fixture or dataset version
- career fixture version
- relevant context item IDs or hashes

Do not write raw private content into the trace by default.

# Observability floor

Stage 0 and Stage 1 stay local.

## JSONL events

Useful event kinds:

- run started
- context prepared
- provider request started
- provider response completed
- tool requested
- tool blocked
- tool started
- tool completed
- tool failed
- run completed
- run failed
- run cancelled

Safe default fields:

- event version
- timestamp
- run ID
- turn number
- event kind
- provider and model
- tool name
- duration
- safe counts and sizes
- error category
- approval state

Excluded by default:

- credentials
- headers
- provider bodies
- full prompts
- full model outputs
- CV text
- profile contents
- tool arguments
- tool results
- fetched pages

## Python logging

Logs explain local failures to the operator.

JSONL records the stable event contract.

They are related but not the same thing.

## Future telemetry trigger

Add OpenTelemetry or a local trace viewer when runs cross processes or JSONL inspection becomes painful.

Do not install a telemetry platform for Stage 0.

# Verification floor

## Deterministic checks first

Verify:

- schema validation
- active tool selection
- event ordering
- redaction
- approval blocking
- step limits
- context manifest generation
- fake-provider trajectories

## Fixture outcome checks

For Job 49 and Job 328, verify facts such as:

- no invented evidence
- uncertainty remains visible
- source inspection changes the answer only when useful
- the model does not claim it inspected a source in Stage 0
- missing evidence is not silently converted into experience

## Human review

Use a Markdown checklist for:

- usefulness
- honesty
- specificity
- career awareness
- source handling
- tone
- whether the output would help a real person decide what to do next

## Model judges later

A model judge may become one signal. It is never the sole release gate.

# What to borrow now, later, and never by default

## Borrow now

- one provider boundary
- one internal message representation
- one bounded async loop
- explicit tool schemas
- tool validation before execution
- active tools separate from registered tools
- structured lifecycle events
- fake-provider tests
- structured run result
- context manifest
- stable prompt plus turn context

## Borrow when a real run demands it

- turn snapshots and save points
- persisted conversations
- steering and follow-up queues
- token tracking
- compaction
- skills
- flat read-only sub-agents
- connector plugins
- isolated coding workspaces
- durable operations
- worker wakeups

## Do not copy by default

- Pi's permissive four-tool default
- Pi's whole JSONL branch tree as career storage
- Pi's third-party extension breadth
- coding-specific prompt text
- Hermes' provider matrix
- Hermes' 70-plus tools
- AST tool discovery
- dynamic schema mutation
- external memory providers
- autonomous self-editing skills
- recursive delegation
- regex-heavy shell security as a substitute for isolation
- a lowest-common-denominator model abstraction

# Risks found in the reference systems

## Pi

- Project trust is not a sandbox.
- The generic hook design is partly ahead of runtime code.
- Automatic compaction and retry behaviour are incomplete in the checked generic harness.
- The observability package is largely a design document at the checked commit.
- Pending writes and queues do not provide full crash recovery.
- `Agent` and `AgentHarness` overlap enough that copying both would add confusion.

## Hermes

- The runtime is large and fast-moving.
- Lifecycle names can mean different boundaries.
- Documentation and default thresholds can drift.
- Registry and plugin machinery solve a much broader product.
- Delegation carries substantial coordination code.
- Shell approval policy is large because the shell surface is inherently dangerous.

## HaxJobs-specific risks

- Treating conversation history as career truth.
- Giving the model all tools because they exist.
- Letting generic file writes bypass typed career actions.
- Treating source content as instructions.
- Logging private career data in traces.
- Retrying an external action without knowing whether it already happened.
- Adding compaction before measuring token pressure.
- building a plugin or sub-agent system before one real workflow needs it.
- copying coding-agent permissions into an unattended career agent.

# Decision status for planning

Research does not turn a working recommendation into an accepted decision. Planning must keep these groups separate.

## Accepted constraints

These are already decided in the discussion notes:

1. HaxJobs is greenfield.
2. Python owns the runtime and employment logic.
3. TypeScript is reserved for the later interface.
4. Real job fixtures and human review drive iteration.
5. Stage 0 has no tools.
6. Stage 1 has only `inspect_job_source(job_ref)`.
7. Stage 0 and Stage 1 use plain Python plus Pydantic rather than an agent framework.
8. PydanticAI is the first framework to reconsider if provider, streaming, retry, approval, and instrumentation code grows materially.
9. Initial observation uses local redacted JSONL, Python logging, pytest, fixture checks, and Markdown human review.

## Working architectural recommendations

These are strongly supported by the source study but still need acceptance where `discussion/006` marks them open:

1. The loop contains no job-search business logic.
2. Internal messages are separate from provider messages.
3. One model request sees one frozen context snapshot.
4. Registered tools are separate from active tools.
5. Tool arguments are validated before execution.
6. Tool and provider failures become explicit structured results.
7. Passive observers cannot alter execution.
8. External-effect approval is enforced below prompts.
9. Career truth is not stored only in conversation history or compaction summaries.
10. Generic file tools cannot mutate canonical career state.
11. Bash requires real isolation before unattended use.
12. CLI, web, and worker share one runtime.

# Proposed implementation sequence after approval

This is not an execution plan. It is the smallest likely order implied by the study.

## Slice A: Stage 0

- model protocol
- one configured-provider adapter, initially tested against the current DeepSeek-compatible endpoint
- fake adapter
- frozen fixtures
- one prompt assembly function
- one model call
- run result
- JSONL event sink
- context manifest
- pytest and human review template

## Slice B: Stage 1

- internal assistant tool-call message
- tool definition
- Pydantic argument validation
- active tool list
- `inspect_job_source(job_ref)`
- bounded tool loop
- invalid-call and tool-error handling
- ordered events

## Slice C: only after traces

Choose the next failure from evidence:

- context selection
- source normalization
- evidence retrieval
- session continuity
- document intake
- project workspace
- approval flow
- durable operation

Do not preselect the answer before seeing the traces.

# Open decisions

These need user judgement before implementation planning hardens them.

1. Accept the four-layer conceptual split inside one Python package?
2. Accept employability project work as a first-class scoped coding capability?
3. Accept read-only user-selected document workspaces?
4. Accept typed actions as the only route for canonical career-state mutation?
5. Accept explicit local activation for bash and mandatory isolation before unattended use?
6. Decide the exact internal message and tool-result envelope during the Stage 1 plan, not before?

# Current recommendation

Use Pi as the architectural shape:

- small generic loop
- domain capabilities outside the loop
- explicit active tools
- events
- cancellation
- save points later
- fake-provider tests

Use Hermes as the Python implementation lens:

- thin host object
- prepare-turn seam
- canonical messages
- strict registry
- final result
- approvals at side-effect boundaries

Then make the product job-native through employment context, evidence, actions, permissions, and workspaces.

The short version:

```text
Pi-like restraint
+ Hermes-like Python boundaries
+ employment-native context and tools
+ scoped coding capability
= the HaxJobs direction worth testing
```
