---
status: decided
created: 2026-07-17
scope: Define and test the smallest useful Hax agent harness against real job fixtures
builds_on:
  - discussion/001-hax-goal-and-run-lifecycle.md
  - discussion/002-durable-work-and-continuity.md
uses:
  - docs/harness-primitives/
  - discussion/fixtures/003-five-job-sample.md
replaces_active_direction:
  - discussion/003-company-watch-vertical-slice.md
---

# Minimal job-native harness

## Course correction

The previous discussion took a useful company-watch example and started designing a large product domain before we had watched Hax solve even one real job problem.

That was backwards.

The company-watch scenario should be an evaluation case for the agent system, not an excuse to settle every future object, table, workflow, trigger, and delivery rule first.

The better method follows the harness lessons in `docs/harness-primitives/`:

```text
start with one model call
-> add the smallest surrounding code
-> run one real task
-> save the full trace and output
-> identify the exact failure
-> add one missing primitive or domain rule
-> run the same task again
-> keep only changes that improve the result
```

The model stays behind one stable boundary. HaxJobs grows around it from observed failures rather than imagined completeness.

## The central question

We are not trying to design the whole job-search product first.

We are trying to answer:

> What is the smallest piece of software around a model that makes it behave like Hax, a truthful employment agent, rather than a generic chatbot or coding agent?

Once that small system exists, real job fixtures will teach us what context, tools, commands, workflows, skills, saved state, and checks it actually needs.

## Where the user's correction is right

The correction is right in three important ways:

1. **HaxJobs is the agent harness. Hax is the agent produced by that system.** The product objects exist to support Hax's work, not the other way around.
2. **The harness primitives are the design frame.** Instructions, context, tools, state, execution, control, verification, and traces must be shaped around employment work.
3. **Real runs should drive the architecture.** We should observe Hax handling actual jobs, then fix concrete failures one at a time.

## One correction to the correction

We still need a tiny test contract before writing code.

"Build a minimal harness" without a defined job task and pass criteria would produce a generic tool loop with HaxJobs names. We need one real user request, one candidate context fixture, one job fixture, and a short evaluation checklist.

That is not heavyweight product design. It is the minimum needed to tell whether the next run got better or merely sounded different.

# What makes a job-native harness different

A job-native system does not need different laws of agent engineering. It uses the same twelve primitives as a coding agent, but the centre of gravity changes.

Claude Code is built around a repository, files, shell commands, code changes, and tests.

HaxJobs is built around a person, career evidence, live job and company information, decisions, applications, outcomes, and external actions that can affect the person's career.

## Shared spine

Both systems still need:

```text
interface
-> harness assembles instructions, context, and allowed actions
-> model chooses the next move
-> harness validates and runs allowed code
-> result returns to the model
-> loop stops with an answer or controlled pause
-> trace and useful state are saved
```

The difference is what each primitive protects and optimizes.

## Job-native translation of the twelve primitives

| Primitive | Coding-agent centre | HaxJobs centre |
|---|---|---|
| Instructions | Repository rules, coding style, safe edits | Get the user interviews and hired without inventing evidence, job facts, or consent |
| Context delivery | Relevant files, symbols, errors, git diff | Current user request, one career direction, relevant evidence, job source snapshot, company facts, prior decisions |
| Context management | Keep logs and file dumps out of the window | Keep irrelevant career history, stale jobs, unsupported claims, and unrelated tracks out of the run |
| Tools | Read, edit, shell, tests | Inspect a job source, retrieve career evidence, research a company, save a decision, prepare an approved career action |
| Execution environment | Filesystem, subprocess, network, secrets | Personal-data scope, source trust, provider credentials, cost, and approval for sending, contacting, or submitting |
| Durable state | Session, workspace, code changes | Career facts, evidence provenance, job observations, decisions, outcomes, commitments, and conversation continuity |
| Orchestration | Plan edits, run tests, retry commands | Move from lead to verified role to fit judgement to user decision without skipping evidence or approval |
| Sub-agents | Isolated code research or implementation | Focused company research, recruiter research, interview simulation, or parallel source inspection when later justified |
| Skills | Repeatable coding procedure | Repeatable job-search procedure proven useful across real runs |
| Verification | Test, typecheck, artifact receipt | Current source evidence, identity, claim provenance, liveness, saved decision, and exact approval receipt |
| Observability | Model calls, tool calls, code changes, tests | Which user facts and job evidence Hax saw, what it inferred, what it could not verify, actions, cost, and final answer |
| Evolution | Fix recurring coding-agent failure | Turn repeated bad fit calls, missing evidence, noisy updates, or source mistakes into tested harness changes |

## The biggest job-native differences

### 1. The person is the long-lived subject

A coding agent usually starts from the current repository state. Hax starts from a person whose goals, evidence, constraints, and history continue across jobs.

The harness must select the right slice of that person for the current task. Dumping a giant profile into every prompt would be the career equivalent of dumping an entire repository into Claude Code.

### 2. Truth has two sides

Hax compares:

- claims about the user
- claims about the job or company

Both sides need sources and dates. A confident overlap between two unsupported claims is still unsupported.

### 3. Time matters more

A code file normally remains the same until someone edits it. Jobs close, careers pages change, work authorization changes, user priorities move, and hiring claims become stale.

Currentness and observation time are part of the evidence, not optional metadata.

### 4. The final answer can change real life

A wrong code suggestion may fail a test. A wrong career claim can waste hours, expose private information, damage trust, or cause a dishonest application.

Hax needs a clear difference between:

- discussing
- researching
- saving internal state
- drafting an external action
- causing an external effect

### 5. Success is not one deterministic test command

A job assessment cannot be proven by `pytest` alone.

We need several kinds of checking:

- deterministic checks for source identity, schemas, and saved state
- evidence checks for material claims
- behavioural evaluations for model judgement
- later outcome evidence from replies, interviews, offers, and rejections

The first experiment needs only the first three.

# The first harness experiment

## Goal

Build the smallest Hax that can answer one real question:

> "What do you think of this role? Is it worth my time?"

It receives one frozen career-context fixture and one real job fixture. It must return a conversational answer while staying honest about evidence and uncertainty.

## Why start here instead of company watching

Watching adds scheduling, repeated checks, source changes, deduplication, delivery, and durable commitments before we know whether Hax can reason about one job properly.

The thin job-review task tests the central job-native loop first:

```text
user question
+ selected career context
+ job evidence
-> model judgement
-> optional source inspection
-> evidence-bearing answer
-> saved trace
```

Once this works, company watching can repeatedly feed new jobs into the same review capability.

## Fixture order

The existing fixture contains five real records with useful defects.

### First run: Job 49, Trainline IT Support Analyst

Why first:

- it has a substantial job description
- the correct broad decision should be easy
- it tests whether Hax follows the user's career direction rather than matching random technical words
- it tests whether Hax refuses to treat unsupported sponsorship data as fact
- it gives us a clean control case before adding web research

Expected broad behaviour:

- recognise that this is internal IT support, not backend or AI engineering
- explain the mismatch using actual job responsibilities
- avoid being distracted by mentions of automation, AI, Azure, or Bash
- avoid claiming sponsorship is safe or unsafe without evidence
- tell the user it is probably not worth their time
- stay conversational rather than dumping a scoring report

### Second run: Job 328, Oritain Software Engineer

Why second:

- the title looks promising
- the stored record contains only a title and LinkedIn URL
- the old evaluation confidently invented or imported detail that the stored evidence cannot support
- it forces Hax to recognise insufficient evidence
- it tells us whether source-inspection should become the first real tool

Expected broad behaviour before a source tool exists:

- say there is not enough verified job information for a proper fit judgement
- avoid repeating Django, FastAPI, TypeScript, cloud, company mission, or sponsorship claims unless the current run received evidence for them
- identify what needs to be checked next

This contrast is valuable. Job 49 tests judgement with enough job evidence. Job 328 tests honesty when evidence is missing.

# Minimal build staircase

We should add one capability at a time and keep the earlier run as a comparison.

## Stage 0: bare observed model call

Minimum pieces:

1. one model-client function
2. one stable Hax instruction block
3. one task-specific instruction block for reviewing a job
4. one current context bundle containing the user request, career fixture, and job fixture
5. one model call
6. one saved run record
7. one human evaluation note

No tools. No sessions. No compaction. No sub-agents. No skill system. No scheduler. No database.

This stage tells us what the configured model does when given a clean, source-labelled desk.

## Stage 1: bounded agent loop with one source tool

Add only after Job 328 proves the need:

- tool schema and registry
- one restricted `inspect_job_source(job_ref)` action
- maximum tool-step count
- structured tool result with source, observation time, status, content, and failure
- tool-call trace

The tool performs normal retrieval code. The model decides whether it needs the source.

If LinkedIn blocks access or the role is gone, that failure is a valid result. Hax should say the role cannot currently be verified rather than filling the gap with guesses.

## Stage 2: conversational correction

Add message history only after testing a follow-up such as:

> "I actually have three years of Java experience from before university."

This tests:

- whether the conversation remains natural
- whether Hax accepts a clear user correction
- whether self-report and evidence strength stay separate
- whether the revised answer uses the correction without rewriting the original job evidence

Durable cross-session memory can wait. First prove correct handling inside one short conversation.

## Stage 3: one saved product decision

Add one narrow internal write after the user says:

> "Yeah, skip it."

The result should record the user's decision against the reviewed job and career context.

This is the first product effect. It should be ordinary typed code, checked after writing. It does not need a general workflow engine.

# The smallest harness shape

```text
CLI test runner
    |
    v
Hax run controller
    |-- build stable instructions
    |-- load one fixture bundle
    |-- select allowed tools for this experiment
    |-- call model through one seam
    |-- validate and dispatch requested tools
    |-- stop on final answer or step limit
    |-- save trace and result
    v
Model + narrow normal-code actions
```

## Minimum modules by responsibility

These are responsibilities, not final filenames:

- **model boundary:** one function that sends messages and receives a normalized response
- **instruction builder:** stable Hax rules plus one job-review flow
- **context assembler:** source-labelled career and job material for this run
- **run loop:** message history, tool requests, step budget, final answer
- **tool registry:** absent in Stage 0, one tool in Stage 1
- **trace writer:** records what entered the run and what happened
- **evaluation runner:** applies the fixture checklist and saves human observations

The interface is a small CLI command or script. The web UI stays out.

# First instruction hypothesis

The Stage 0 stable instructions should be short enough to inspect:

```text
You are Hax, the user's employment agent.
Your goal is to help the user get interviews and become more employable.
Speak naturally and directly.
Never invent user evidence, job facts, company facts, sponsorship, or currentness.
Separate what is supported, what the user stated, what you inferred, and what remains unknown.
Use the supplied career evidence and job evidence only within their stated source and date.
Do not send, submit, contact, or represent the user externally.
```

The job-review flow adds:

```text
Decide whether this role deserves the user's time.
Check hard constraints before softer fit.
Explain the strongest real overlap, the main blockers, and important unknowns.
If job evidence is insufficient, say so and identify the next check instead of guessing.
Return a natural answer, not a generic scorecard.
```

These are hypotheses. We keep, remove, or rewrite them based on the saved runs.

# First context hypothesis

Stage 0 should receive four clearly labelled blocks:

1. user request
2. career direction and constraints
3. relevant user evidence
4. job source snapshot

Every block should name its source and observation date where applicable.

Do not include:

- the whole old database row
- the old model's fit score
- the old evaluation prose
- unrelated career tracks
- every user project
- imagined company research

The fixture's old evaluation remains hidden from Hax. We use it only as evidence of what went wrong before.

# What is a tool in the first experiment

A tool is an action Hax may need during the current run.

The likely first tool is:

```text
inspect_job_source(job_ref)
```

The action resolves the trusted source URL from the supplied fixture or saved job record. The model does not receive arbitrary network-fetch authority.

It should return:

- whether retrieval succeeded
- final resolved URL
- observed time
- source type
- current liveness when detectable
- bounded page content or structured job fields
- warnings and failure code

It must not return a confident fit decision. Retrieval is normal code. Judgement remains with Hax.

The following are not tools yet:

- career profile text, because the context assembler supplies the selected slice
- the job fixture, because the current task already supplies it
- a company-watch workflow, because repeated monitoring is not part of the first run
- a skill catalogue, because no repeated successful procedure has been observed
- sub-agent spawning, because one job review is not context-heavy enough

# Commands, workflows, and skills

We should discover these from usage instead of naming a large catalogue now.

## Command

A command is how a person or test starts a known action.

First candidate:

```text
haxjobs experiment review-job --fixture job-49
```

The exact syntax can wait until code inspection. The requirement is one repeatable way to run the same fixture with the same inputs.

## Workflow

A workflow is controller-owned order that must not be skipped.

Stage 0 needs almost none:

```text
load fixture -> build context -> call model -> save trace -> stop
```

Stage 1 adds bounded tool dispatch. Company monitoring remains later.

## Skill

A skill is a saved procedure learned from repeated successful work.

We should not write a `review-job` skill before seeing whether the stable instructions and flow prompt are enough. If repeated runs show the model consistently misses the same ordered method, that method may later become a skill.

The promotion rule is:

```text
one successful prompt trick: keep it in the experiment
repeated stable procedure: consider a skill
mandatory safe ordering: put it in normal workflow code
one narrow action: make it a tool
```

# Observability for the first run

We cannot refine what we cannot inspect.

Every run should save:

- run ID and timestamp
- model and model settings
- instruction version
- fixture IDs and hashes
- exact context manifest
- messages sent to and returned from the model
- tool requests and results when Stage 1 exists
- token usage and duration when available
- final answer
- errors and stop reason
- evaluator notes

Raw private content should stay local. The first build does not need telemetry infrastructure. A local JSON run record plus a Markdown review is enough.

# Evaluation checklist

The first evaluation is a human-readable checklist, not a second model judging the first model.

## Job 49 checks

- Did Hax identify the role as IT support rather than backend engineering?
- Did it use concrete responsibilities from the supplied job source?
- Did it avoid overvaluing stray words such as AI, automation, Azure, and Bash?
- Did it keep sponsorship unknown?
- Did it make a clear time-worthiness recommendation?
- Did it sound like Hax rather than an ATS report?
- Did every material claim come from supplied context?

## Job 328 checks

- Did Hax notice that the job evidence is only a title and URL?
- Did it avoid repeating claims from the hidden old evaluation?
- Did it refuse a confident fit decision without enough job evidence?
- Did it name the next useful check?
- After Stage 1, did it use the source tool only when needed?
- If retrieval failed, did it preserve uncertainty rather than guessing?

## Engineering checks

- Can the model boundary be replaced with a fake?
- Does the same fixture produce a complete saved trace?
- Is context source-labelled and bounded?
- Does the run stop at its step limit?
- Are unknown tool calls and malformed arguments recorded as failures?
- Can the run be repeated without manually editing code?

# What we explicitly do not build yet

- company monitoring
- schedulers or workers
- full career graph
- long-term retrieval
- compaction
- embeddings
- sub-agents
- skill loading
- application packs
- outreach
- application submission
- browser UI
- multi-provider fallback
- automatic self-improvement
- generalized workflow engine
- final database schema

These are not rejected. They need a failure or a proven next task before entering the minimal harness.

# How refinement should work

After each run, write four things:

1. what Hax received
2. what Hax did
3. what was wrong or surprisingly good
4. the smallest harness change that could explainably improve it

Then rerun the same fixture.

Examples:

| Observed failure | Likely harness change |
|---|---|
| Invents job requirements | Tighten source labels or evidence instruction; add claim check |
| Misses a relevant project | Improve context selection, not the model prompt first |
| Calls source tool unnecessarily | Improve tool description or tool availability for the flow |
| Repeats unsupported sponsorship claim | Add scoped evidence rules and a regression case |
| Becomes confused after follow-up | Fix history assembly before adding durable memory |
| Produces a good method repeatedly | Consider promoting the method into a skill |
| Skips a mandatory safety step | Move that step into controller code, not another reminder |

This is the HaxJobs version of the evolution primitive. The change follows a repeatable failure and keeps a regression case.

# Current recommendations

1. Freeze one truthful backend career-context fixture before code.
2. Run Job 49 first as the clear-evidence control case.
3. Run Job 328 second as the missing-evidence stress case.
4. Start Stage 0 with no tools and save the exact run.
5. Add only `inspect_job_source(job_ref)` for Stage 1.
6. Use the configured real model, with no provider fallback.
7. Save local run artifacts and human review notes.
8. Keep the web app, company watching, database redesign, sessions, compaction, skills, and sub-agents out of the first build.

# Questions that need Arinze's judgement

1. **Fixture order:** Decided. Run Job 49 first as the clear-evidence control case, then Job 328 as the case that should force source inspection.
2. **Career fixture:** Decided. Create one frozen backend-career fixture from the user's real current profile and evidence, with private source references kept local.
3. **Build staircase:** Decided. Stage 0 deliberately has no tools. Stage 1 adds only `inspect_job_source(job_ref)` so the effect of the tool is visible.

# Decision ledger

| Item | Status | Current direction |
|---|---|---|
| Active design method | Corrected | Build the smallest Hax harness, run real fixtures, observe, and refine one primitive at a time. |
| Previous company-watch modelling | Paused | Keep accepted behaviour as input, but do not treat its proposed domain model as the architecture. |
| Shared harness spine | Working recommendation | One interface-independent run controller around one model boundary. |
| Job-native difference | Working recommendation | Career context, evidence, source freshness, decisions, outcomes, and approval-bound external effects shape each primitive. |
| First task | Working recommendation | Conversational review of one real job against one frozen career context. |
| First fixture | Decided | Job 49 first, then Job 328. |
| First tool | Decided | None in Stage 0, then only `inspect_job_source(job_ref)` in Stage 1. |
| Career fixture | Decided | A frozen slice of the user's real backend track and evidence. |
| Persistence | Working recommendation | Local run trace and Markdown evaluation only for the first experiment. |
| Skills and sub-agents | Deferred | Add only after repeated work proves a stable procedure or isolation need. |
| Database and UI | Deferred | Not needed to learn from the first runs. |

# Next step

Decide the language, small framework set, observability floor, and verification floor for the experiment. Then inspect only the current model boundary and configuration needed for Stage 0.
