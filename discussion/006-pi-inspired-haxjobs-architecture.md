---
status: discussing
created: 2026-07-17
scope: Decide how HaxJobs should mirror Pi's architecture while adding employment-native tools and controlled coding capabilities
builds_on:
  - discussion/004-minimal-job-native-harness.md
  - discussion/005-implementation-stack-observability-and-verification.md
studied_systems:
  - Pi commit 3da591ab74ab9ab407e72ed882600b2c851fae21
  - Hermes commit 9e1b1d7536270b4e2bf56662903acfbfc54ac937
---

# Pi-inspired HaxJobs architecture

## The user's correction

HaxJobs should not study coding-agent systems only to learn a generic model and tool loop.

A serious employment agent will need many capabilities that coding agents already solved:

- reading user-selected files
- searching folders and project repositories
- writing and editing artifacts
- running code and tests when helping the user build evidence projects
- streaming progress
- cancelling work
- maintaining conversations
- selecting tools per operation
- keeping tool results together with model history
- compacting long conversations
- observing runs
- loading procedures only when relevant
- isolating specialist work later

HaxJobs is not a coding agent, but helping someone become employable can include real coding work. If Hax designs a missing portfolio project with the user, then cannot inspect, edit, run, and verify that project, the employability promise stops halfway.

So the right answer is not "career tools instead of coding tools."

It is:

> Employment-native tools are the main product surface. Coding tools become a first-class scoped capability when the employment work genuinely enters a project or document workspace.

# What Pi actually separates

The current Pi repository has a cleaner split than the older coding-agent-only picture.

```text
pi-ai
  provider and model boundary

pi-agent-core
  messages, model/tool loop, events, cancellation, tool validation

pi-coding-agent
  coding prompt, filesystem and shell tools, resources, sessions, extensions, CLI and TUI
```

The important lesson is that `read`, `bash`, `edit`, and `write` are not baked into the generic model loop. They belong to Pi's coding-specific product layer.

Pi's low-level loop only understands:

- messages
- a system prompt
- active tool definitions
- a model stream
- tool calls and results
- lifecycle events
- stop, cancellation, steering, and follow-up conditions

Source: [Pi agent loop](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L155-L318).

Pi's coding layer then registers seven concrete tools and chooses an active subset:

- `read`
- `bash`
- `edit`
- `write`
- `grep`
- `find`
- `ls`

Source: [Pi coding tool registry](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/tools/index.ts#L50-L155).

Pi currently enables `read`, `bash`, `edit`, and `write` by default for an attended coding session. Explicit tool lists, no-tools modes, and exclusions alter the active set.

Source: [Pi session creation](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/src/core/sdk.ts#L215-L225).

That separation is exactly what HaxJobs needs.

# Proposed HaxJobs mapping

Keep one Python package initially. Mirror Pi's conceptual boundaries without creating a package monorepo before we need one.

```text
Hax model boundary
  provider adapters and normalized model responses

Hax agent core
  internal messages, bounded loop, tools, events, cancellation, save points

Hax employment layer
  career context, evidence rules, employment tools, capability selection, approvals

Interfaces
  CLI first, web later, worker later
```

## 1. Model boundary

Equivalent to Pi's `pi-ai`, but much smaller at first.

Responsibilities:

- one `ModelClient` protocol
- one DeepSeek-compatible adapter
- one scripted fake
- normalized text, tool calls, stop reason, usage, and provider metadata
- provider-specific options kept inside the adapter

No product logic.

## 2. Agent core

Equivalent to Pi's `pi-agent-core`.

Responsibilities:

- internal message types
- model message projection
- bounded model to tool to model loop
- tool argument validation
- tool-result ordering
- cancellation
- lifecycle events
- step limits
- future steering and follow-up
- save points between turns

No CV rules. No fit scoring. No company logic. No application logic.

## 3. Employment layer

Equivalent to Pi's `pi-coding-agent`, but centred on getting the user hired.

Responsibilities:

- Hax identity and employment instructions
- career-context assembly
- evidence provenance
- job and company context
- employment-native tools
- workspace selection
- tool-capability selection
- external-action approvals
- later sessions, skills, commands, and operation types

This is where HaxJobs differs from Pi.

## 4. Interfaces

The CLI, later web interface, and future worker call the same employment agent and product actions.

They do not implement separate tool loops or career logic.

# What to copy from Pi now

## Internal messages are not provider messages

Pi keeps application messages separate from the final provider-compatible messages. A projection step decides what the model sees.

Source: [Pi message flow](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/README.md#L16-L35).

HaxJobs needs this even more.

An internal record may contain:

- a user message
- an assistant response
- a tool request
- a tool result
- a source observation
- an approval state
- a saved user decision
- an operational event
- a private evidence reference

Not all of those should be copied into the next model prompt. The context assembler produces the model-visible view.

## Tool definitions are separate from active tools

Pi can know about all seven coding tools while exposing only the current active subset.

HaxJobs should know about its full tool catalogue while selecting capabilities for the current operation.

That means:

```text
registered tools != tools visible to this model turn
```

The model can reason freely. The runtime controls what effects are possible.

## Tool calls are validated before execution

Pi resolves the named tool, validates arguments, runs a pre-tool policy hook, executes, catches failure, then returns a tool-result message.

Source: [Pi tool preparation and execution](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/agent-loop.ts#L519-L675).

HaxJobs should mirror this ordering:

```text
model requests action
-> find registered tool
-> validate Pydantic arguments
-> check capability and approval policy
-> execute normal Python action
-> validate and redact result
-> append result
-> continue or stop
```

## Save points between model turns

Pi's higher harness persists completed messages and pending writes, emits a save point, rebuilds the next turn snapshot, then allows another provider request.

Source: [Pi save-point handling](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/src/harness/agent-harness.ts#L438-L542).

This prevents mid-turn changes from silently changing the request already in flight.

HaxJobs should eventually use the same rule:

- one model request sees one frozen turn snapshot
- profile, tool, approval, or context changes affect the next model call
- completed effects are saved before another call starts

Stage 0 has one call, so the save-point design stays small.

## Events are stable and passive

Pi distinguishes lifecycle observation from policy hooks. Its observability design says the core emits safe events and adapters decide whether they become JSON, OpenTelemetry, Sentry, or something else.

Source: [Pi observability design](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/agent/docs/observability.md#L1-L77).

That supports the JSONL decision already made for HaxJobs.

The rule should be:

- observers record what happened
- policy checks can block or change an action
- an observer failure must not change the agent's work

## Fake-provider tests

Pi tests the loop and harness using scripted provider responses rather than real model calls.

HaxJobs already decided on the same pattern. This is one of the clearest things to mirror.

# What to copy from Hermes

Pi is the better shape for the small core. Hermes has useful Python implementation lessons.

## Prepare the turn, then run the loop

Hermes separates once-per-turn setup from repeated model and tool execution through a turn-context boundary.

Useful later when Hax has:

- session loading
- career-context selection
- memory retrieval
- prompt assembly
- provider settings
- capability selection

Do not create a large `TurnContext` in Stage 0. Keep the seam in mind as these inputs appear.

## Canonical messages, temporary provider overlays

Hermes keeps one canonical history and injects temporary memory or plugin context only into the provider request copy.

Source: [Hermes conversation context copy](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/agent/conversation_loop.py#L849-L928).

HaxJobs should use this for selected profile evidence and current job context. Retrieved context belongs on the current model desk. It does not automatically become permanent conversation truth.

## Strict tool registry

Hermes' useful registry core is name, schema, handler, toolset, availability, dispatch, and one result contract.

Source: [Hermes tool registry](https://github.com/NousResearch/hermes-agent/blob/9e1b1d7536270b4e2bf56662903acfbfc54ac937/tools/registry.py#L84-L113).

Do not copy AST discovery, dynamic schema mutation, dozens of toolsets, or plugin shadowing yet.

## Side-effect approvals belong below prompts

Hermes places approval checks around actual execution. HaxJobs needs a stricter employment version.

A prompt saying "ask first" is not an approval system.

Application submission, outreach sending, connections, and external representation must stop at the action boundary until the exact action is approved.

# Coding tools in HaxJobs

The user's point stands: HaxJobs should have coding tools.

The key decision is where they operate.

## Career state is not a general filesystem

The canonical career profile, decisions, applications, evidence claims, and commitments should be changed through typed employment actions.

A generic `write` call must not rewrite the career database or profile files behind those actions.

Why:

- it bypasses validation
- it bypasses provenance
- it bypasses history
- it bypasses approval
- it can make durable state contradict itself

## User document workspace

Hax may need to inspect:

- CVs
- cover letters
- certificates
- transcripts
- job descriptions
- common application answers
- portfolio material
- exported LinkedIn data

Recommended capability:

- `read`
- `ls`
- `find`
- perhaps `grep`
- domain parsers such as `extract_document`

The workspace should be made from files the user selected or uploaded. It should not mean unrestricted access to the user's home directory.

Writing should happen through explicit artifact actions or a selected output directory.

## Employability project workspace

Hax may help the user design and complete a real project that creates missing evidence.

Recommended capability inside a selected project root:

- `read`
- `grep`
- `find`
- `ls`
- `write`
- `edit`
- `bash`

This is the Pi-like coding mode inside HaxJobs.

It is still employment work because the project's purpose, target skill, evidence goal, and completion proof come from the user's employability plan.

## Why `bash` is different

`bash` can bypass almost every tool restriction:

- read any accessible file
- change the career database
- access credentials
- call external services
- send data
- install software
- execute generated code

A path check inside the bash tool is not enough.

For attended local use, bash can initially require explicit project-workspace activation and clear disclosure.

For unattended, automated, or cloud use, bash must run inside an OS or container boundary with:

- only the selected project mounted
- minimum credentials
- controlled network access
- time, output, process, and disk limits

Pi itself says its project trust is not a sandbox and recommends real containers or VMs for untrusted or unattended work.

Source: [Pi security model](https://github.com/earendil-works/pi/blob/3da591ab74ab9ab407e72ed882600b2c851fae21/packages/coding-agent/docs/security.md#L1-L57).

## Proposed capability sets

These are permission bundles, not rigid intent labels. One user interaction may create several operations with different bundles.

| Capability set | Likely tools | Purpose |
|---|---|---|
| Conversation | None or selected read-only career context | Discuss, clarify, explain |
| Career records | Typed profile, evidence, track, decision, and outcome actions | Read or change canonical career state |
| Job research | Search, fetch, inspect source, company and job actions | Verify external employment information |
| Document intake | Read-only selected-file tools and document extraction | Understand user-provided material |
| Application preparation | Typed pack and artifact actions | Create controlled application material |
| Project workspace | Pi-like filesystem tools plus bash inside a selected root | Build and verify employability evidence |
| External effect | Submit, send, connect, publish | Exact approval required every time |

The model does not receive every tool because they exist. The operation receives the capabilities needed for its work.

# Initial recommendation per coding tool

| Tool | Long-term place in HaxJobs | Initial boundary |
|---|---|---|
| `read` | Document and project workspaces | User-selected roots only, canonical paths resolved |
| `grep` | Document collections and project repositories | Read-only, bounded results |
| `find` | Selected workspaces | Read-only, ignore rules, bounded results |
| `ls` | Selected workspaces | Read-only, no home-directory enumeration |
| `write` | Project workspace and explicit artifact output | Selected root, no career-state internals |
| `edit` | Project workspace and controlled text artifacts | Selected root, exact replacement, mutation history |
| `bash` | Employability project workspace | Explicit activation; sandbox required before unattended use |

None of these should be added to Stage 0 or the Job 49 review. The first experiment is still deliberately tool-free.

Stage 1 still adds only `inspect_job_source(job_ref)` because we are measuring one change.

The coding tools enter when we test document intake or project building.

# Native employment tools remain primary

Coding tools manipulate generic files and processes. They cannot replace job-native actions.

Examples of native actions Hax may eventually need:

- inspect a job source
- search jobs across approved sources
- research a company
- retrieve relevant career evidence
- assess fit
- explain missing evidence
- propose an evidence project
- record a user decision
- prepare application material
- track an application
- prepare interview practice
- update an outcome
- maintain a company watch

The exact catalogue should still come from real runs. This note only settles the relationship:

```text
employment actions express product meaning
coding tools provide controlled workspace capability
```

# Commands, skills, extensions, and workflows

Pi gives useful distinctions, but HaxJobs should keep them small.

## Command

An explicit interface entry point, such as reviewing a fixture or opening a project workspace.

Commands start work. They do not contain business logic.

## Tool

One bounded action callable by the model.

Tools have typed arguments, typed results, capability requirements, and side-effect metadata.

## Workflow

Controller-owned order that must be followed for correctness or safety.

If an application must be verified, approved, then submitted exactly once, that ordering belongs in code rather than a skill prompt.

## Skill

A progressively loaded procedure that helps the model perform a repeated kind of work.

Pi puts skill metadata in the prompt and loads full instructions only when selected. HaxJobs can mirror that when repeated employment procedures actually exist.

## Extension

A way to add tools, hooks, resources, or interfaces without changing the core.

Do not build a third-party extension system yet. Native Python registration is enough. Connectors such as Gmail or WhatsApp may later justify a plugin boundary.

# What not to mirror from Pi

## Do not copy the permissive default

Pi is an attended local coding agent. It runs with the user's permissions and explicitly says project trust is not a sandbox.

HaxJobs may later operate unattended and hold private career data. Its capability defaults must be narrower.

## Do not copy the JSONL conversation tree as career storage

Pi's JSONL session tree is good for conversation branching and replay.

Career evidence, jobs, decisions, commitments, applications, and outcomes need their own durable records. A conversation transcript is not the career model.

Stage 0 JSONL remains a run trace, not the final product database.

## Do not build a plugin marketplace

Pi's extension system supports custom tools, commands, providers, UI, resource loading, and event interception. HaxJobs has one developer and no proven third-party extension need.

## Do not copy coding prompt text

Keep Pi's assembly pattern, not its coding identity, file instructions, or project assumptions.

## Do not treat Pi's design documents as shipped behaviour

At the studied commit, parts of Pi's generic hooks, automatic compaction, crash recovery, and observability package remain planned or incomplete.

We should copy verified runtime patterns and use design notes as ideas, not dependencies.

# Proposed smallest architecture for Stage 0 and Stage 1

```text
experiment CLI
    |
    v
EmploymentAgent
    |-- context builder
    |-- Hax instructions
    |-- active capability selection
    |-- AgentLoop
    |      |-- ModelClient
    |      |-- tool validation and dispatch
    |      |-- lifecycle events
    |
    |-- JSONL event sink
    |-- run result
```

Stage 0 active tools:

```text
[]
```

Stage 1 active tools:

```text
[inspect_job_source]
```

The registry may know only what each stage needs. We do not have to register the future catalogue before building it.

# Recommended architectural decisions

1. Mirror Pi's provider core, agent core, domain layer, and interface separation conceptually inside the Python package.
2. Keep one HaxJobs loop rather than separate loops for CLI, web, and worker.
3. Keep internal messages separate from provider messages.
4. Separate registered tools from active tools.
5. Select tools through capability sets attached to work, not one global all-tools list.
6. Treat native employment actions as canonical product operations.
7. Add Pi-like coding tools for selected document and employability project workspaces.
8. Keep generic writes and bash away from canonical career storage.
9. Require a real sandbox before bash can run unattended or in the cloud.
10. Copy Pi's save points, event ordering, fake-provider test shape, and passive-observability rule in small form.
11. Copy Hermes' canonical-history, temporary-context, strict-registry, and side-effect-approval ideas.
12. Delay compaction, extensions, delegation, skills, and durable workflow machinery until real runs demand them.

# Questions for Arinze

1. **Architecture shape:** Should HaxJobs mirror Pi's provider core, agent core, employment layer, and interface split, while keeping them as modules inside one Python package for now? My recommendation is yes.
2. **Coding workspace:** Should building real employability projects be a first-class Hax capability with `read`, `grep`, `find`, `ls`, `write`, `edit`, and `bash` inside an explicitly selected project root? My recommendation is yes.
3. **Document workspace:** Should user-selected intake files receive read-only file tools, while profile and career-state changes continue through typed employment actions? My recommendation is yes.
4. **Shell boundary:** Should `bash` require explicit project-workspace activation now and a real container or VM boundary before unattended or cloud execution? My recommendation is yes.

# Decision ledger

| Item | Status | Current direction |
|---|---|---|
| Pi as architecture reference | Open | Recommend mirroring its layered separation and small loop philosophy. |
| Hermes as architecture reference | Working recommendation | Borrow selected Python boundaries, not the full runtime. |
| Physical package split | Open | Keep one Python package initially. |
| Coding tools in HaxJobs | Open | Include as a scoped project-workspace capability. |
| Document file tools | Open | Read-only access to user-selected roots. |
| Career-state mutation | Working recommendation | Typed employment actions only. |
| Tool activation | Working recommendation | Registered catalogue plus per-operation active capability set. |
| Bash | Open | Explicit project activation; OS isolation before unattended use. |
| Stage 0 tools | Decided | None. |
| Stage 1 tools | Decided | `inspect_job_source(job_ref)` only. |
| Generic plugin system | Deferred | Native Python registration first. |
| Session tree, compaction, sub-agents, skills | Deferred | Add from observed needs. |

# Converged technical reference

The three disposable source studies have been merged into one durable implementation reference:

- [Pi and Hermes study for a job-native HaxJobs architecture](research/2026-07-17-pi-hermes-job-native-harness-study.md)

It keeps the detailed runtime findings, exact source links, shipped-versus-planned warnings, coding-tool analysis, HaxJobs mapping, risks, planning invariants, and likely implementation sequence. Read it with this decision note before writing an execution plan.
