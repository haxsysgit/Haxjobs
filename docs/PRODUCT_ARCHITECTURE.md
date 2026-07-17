# HaxJobs Product Direction

## One sentence

HaxJobs is a career agent that uses the user's evidence, goals, job history, and progress to help them get interviews and become qualified for better roles.

## Product boundary

The product is the set of career actions, memory, rules, and approvals around the model.

The model reasons. HaxJobs decides:

- what context the model sees
- which career action it may call
- what gets saved
- what needs user approval
- what evidence supports a claim
- what happens after a failure

## Interface order

### 1. CLI

The CLI is the first complete interface. Every real action should be usable without a browser.

Examples of the intended shape:

```text
haxjobs profile build
haxjobs jobs discover
haxjobs jobs evaluate 42
haxjobs jobs decide 42 apply
haxjobs packs generate 42
haxjobs watch run
```

These commands are a target, not the current CLI surface.

### 2. Web app

The web app calls the same actions through FastAPI. It adds visual review and approval, but owns no separate business logic.

### 3. Cloud worker

A future always-on worker runs scheduled discovery, company watches, job-site watches, and notifications. It uses the same actions and durable state as the CLI.

The cloud worker is not built. Current automation is a host cron script plus an in-process discovery thread.

## Shared action model

```text
CLI -------------+
FastAPI ----------+--> shared product action --> storage and external services
Cloud worker -----+
Agent tool -------+
```

One capability means one implementation. An agent tool is a typed adapter over a product action, not another copy of the workflow.

Implemented actions:

- discover jobs
- evaluate job fit
- generate an application pack
- record a decision

Planned career actions include profile building, career-memory updates, missing-skill detection, roadmaps, resource curation, application tracking, interview tracking, and next-move recommendations. They should be added only when their data contract and verification rules are clear.

## Career memory

The current system has SQLite plus `state/profile.json`. That is enough for the present job pipeline, but not for a long-running career agent.

The target memory model needs independent career tracks and evidence-linked records for:

- skills
- projects
- work experience
- education
- jobs and companies
- applications and interviews
- goals and constraints
- learning plans and resources
- contacts and outcomes

Every important claim should carry its source, confidence, verification date, privacy level, related career tracks, and evidence links.

This career graph is a target. It does not exist in the current database.

## Context strategy

The model should receive the smallest useful context for the current action.

1. Select the relevant career track, job, evidence, and recent decisions.
2. Rank evidence by relevance and trust.
3. Keep the stable identity and safety prefix unchanged for prompt caching.
4. Put current profile and task material in the volatile context.
5. Compact long sessions before they crowd out important facts.
6. Write durable facts back to storage instead of relying on chat history.
7. Isolate heavy research or simulation work in child runs.

Durable sessions, retrieval, compaction, and child-agent runs are not implemented yet.

## Employability loop

A fit score is not the final product.

For a strong fit, HaxJobs should help the user make a truthful application using the best reusable CV variant and verified evidence.

For a weak fit, HaxJobs should explain the missing evidence or skills, build a realistic roadmap, find useful resources, suggest proof-building projects, track progress, and reevaluate later.

That loop is the main difference between a career agent and a job-matching script.

## Skills and tools

A tool performs one typed action, such as evaluating a stored job or recording a decision.

A skill is a reusable procedure that tells the agent when and how to combine tools. For example, an `assess-target-role` skill might select a career track, inspect evidence, evaluate several jobs, compare recurring gaps, and produce a roadmap.

Do not turn static profile text or fixed labels into tools. Put static rules in instructions and load relevant profile data as context.

## Approval rules

Explicit user approval is required before:

- submitting an application
- sending a message
- connecting with a person
- publishing profile changes inferred by the model
- claiming unsupported experience

Drafting, research, scoring, and recommendations may run without approval when they do not create an external side effect.

## What HaxJobs is not

- a generic chat wrapper
- a coding-agent clone
- an automatic application spammer
- a per-job CV rewriting service
- a collection of separate CLI, API, and cron implementations

The shortest description is still the right one: a career agent built around employability.
