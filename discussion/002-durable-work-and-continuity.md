---
status: decided
created: 2026-07-17
scope: How Hax's work survives beyond one message or model run
builds_on: discussion/001-hax-goal-and-run-lifecycle.md
---

# Durable work and continuity

## Why this concept comes next

Hax can reply now, continue working later, monitor something repeatedly, pause for approval, fail halfway through, or return with a result tomorrow.

Before discussing context windows, career memory, tools, or workers, we need to decide what continuity means from the user's point of view. Otherwise we may build storage and context around the wrong unit of work.

This note describes behaviour first. Names such as conversation, interaction, operation, run, and update are working labels.

## Decisions carried forward

From [001-hax-goal-and-run-lifecycle.md](001-hax-goal-and-run-lifecycle.md):

- the conversation is the long-lived relationship with Hax
- one message may create several pieces of work
- some work finishes before the immediate reply
- some work continues after that reply
- a failed model attempt must not erase the underlying work
- later progress and results return to the conversation
- Hax can act from user requests, ongoing monitoring, and automated job-search processes
- the model gets room to reason while HaxJobs controls tools, effects, budgets, evidence, and verification
- this is a greenfield design; the current HaxJobs database and runtime do not constrain it

## The actual problem

Consider this request:

> "Research Stripe, watch their careers page, and tell me when a suitable backend role appears."

The conversation may be quiet for three weeks. During that time HaxJobs may need to remember:

- what the user asked for
- which company and career source were identified
- which career track and constraints define "suitable"
- whether the initial research finished
- when the careers page was last checked
- what changed between checks
- failures and retry state
- whether a matching role was already reported
- whether the user paused or cancelled the watch

The model cannot carry this by remembering an old chat window. HaxJobs must own it as durable product state.

## Decided: the promise is not the process that wakes up

A standing commitment is the promise. A schedule or cron is only one way HaxJobs decides when to make the next check.

```text
"Keep an eye on Stripe"
-> standing commitment stays active
-> cadence says when it is next due
-> scheduler wakes HaxJobs
-> one check attempt starts and ends
-> evidence and state are saved
-> useful change or failure becomes a curated update
-> HaxJobs sleeps until more work is due
```

Continuous means Hax remembers to return. It does not mean one process stays alive forever.

Visual: [Standing commitment lifecycle](../diagram/002-standing-commitment-lifecycle.drawio) ([PNG preview](../diagram/002-standing-commitment-lifecycle.png))

Working terms for now:

- **Commitment:** one promised piece of work, such as researching Stripe once.
- **Standing commitment:** work Hax keeps returning to until an end condition.
- **Cadence:** how often or under what condition Hax should return.
- **Scheduler:** the alarm clock that wakes the system.
- **Attempt:** one bounded execution of the due work. It ends even while the standing commitment remains active.

One scheduler can collect every due standing commitment, run bounded attempts, save the results, and stop. HaxJobs does not need one permanent process per promise.

## Decided: Hax remembers promises and their state

A durable commitment is a promise HaxJobs must remember after the current reply and model run are gone.

The labels may change later, but the normal human situations are decided:

| State | Meaning |
|---|---|
| Active | Hax is doing the work now or in the background. |
| Paused | The user asked Hax to hold the work for now. |
| Waiting for approval | The work is ready, but an external effect still needs the user's current approval. |
| Suspended | The source keeps failing, a dependency is unavailable, or the work is otherwise blocked. |
| Complete | The promised work finished. This is terminal. |
| Cancelled | The user or an agreed policy ended the work before completion. This is terminal. |

Waiting, pausing, and suspension are different:

- paused is a user choice
- waiting for approval is a safety gate
- suspended means HaxJobs cannot continue honestly

An old approval is not permanent permission. If a message, vacancy, recipient, or other material fact has become stale, Hax must ask again before causing the effect.

## Decided: different commitments end differently

- A one-off investigation completes when its result has been saved and reported.
- A watch continues until cancelled, but Hax can ask whether it is still useful after a major life or profile change.
- Approval-bound work waits without silently expiring, though stale work must be refreshed before approval.
- Repeated failure moves work to suspended and tells the user instead of pretending monitoring is still active.
- Cancellation must be explicit and recorded. Silence from the user is not cancellation.

## Decided: state and delivery are both durable

HaxJobs needs to preserve four things:

| Thing | What it answers |
|---|---|
| Commitment | What did Hax agree to do? |
| Progress | What has happened, what is running, and what remains? |
| Evidence and result | What was found, where did it come from, and how certain is it? |
| Delivery state | Was the result reported, approved, paused, or cancelled? |

Hax can know that it posted or sent an update. It cannot claim the user read it unless an interface later supplies a real read receipt.

A reported finding must carry enough identity to prevent Hax from announcing the same Stripe role every day.

## Decided: suitability can change while a commitment is alive

Hax must preserve the original request, but it must not blindly freeze an old meaning of "suitable."

A watch should remain linked to the relevant career track and current constraints. Explicit fixed instructions remain fixed. If the user's role preference, location, work mode, work authorization, or other material condition changes, Hax should review the commitment and explain any changed interpretation.

## Storage implication, not a schema decision

This is operational state, not merely a metric. Metrics can later count checks, matches, failures, and time spent. The promise itself needs a durable state store.

The storage technology is not decided. It may be SQLite, PostgreSQL, or something else after we decide the deployment, concurrency, portability, and recovery needs. YAML and TOML remain options for human-edited configuration, but live promises need atomic state changes and reliable querying.

The smallest conceptual storage shape would eventually need:

1. a current record for each commitment
2. a history of state changes, checks, findings, failures, and reports

That does not choose table names, schemas, database technology, or event architecture yet.

The current HaxJobs database does not constrain this design. It is only a source of development data. Any useful jobs, evaluations, companies, or other records will be translated one way into the new model rather than carrying the old tables and assumptions forward.

An interest such as "Arinze is interested in Stripe" may outlive the watch itself. That belongs to career memory with its source and confidence, while "keep checking Stripe" is the active commitment. They should be related without becoming the same fact.

## Decided: what can create a standing commitment

- **Direct request:** start it within normal safety and cost limits.
- **Existing automation:** run it because the user already agreed to that rule. Report useful changes or failures, not every quiet check.
- **Casual interest:** Hax may start a small, cheap follow-up if it tells the user. An offhand comment must not silently become permanent expensive work.
- **Follow-up during work:** do the next obvious thing that directly helps the original goal. Do not wander into a separate project.
- **Large cost, unrelated expansion, or external action:** ask first.

Hax can take initiative without being sneaky. For example:

> "You've mentioned Notion a few times, so I'm keeping it on my radar while I look for backend roles. Tell me if that's not what you meant."

## Continued in the first vertical slice

The commitment model is decided direction. Delivery timing depends on the job-search situation rather than a separate generic notification system.

That discussion continues in [003-company-watch-vertical-slice.md](003-company-watch-vertical-slice.md), where immediate updates, digests, quiet saves, failures, and approvals are decided against a real company-watch journey.
