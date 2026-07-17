---
status: decided
created: 2026-07-15
scope: Hax's full goal and the first rough lifecycle of a user message
---

# Hax's goal and run lifecycle

## The product promise

Hax is a natural, career-focused agent friend inside HaxJobs.

Its job is to do everything useful and safe to help a person get interviews and get hired. That includes finding roles, understanding companies, talking through opportunities, evaluating fit, preparing application materials, tracking outcomes, and helping the person become employable for roles they are not ready for yet. Employability work can include creating and completing real job-relevant projects that become new evidence in the person's profile.

HaxJobs is the system behind Hax. It owns records, tools, safety gates, long-running work, automation, and the interfaces through which the user talks to Hax.

At the surface, Hax is conversational. Underneath, HaxJobs is a capable employment-native agent system. The conversation is how the user talks to the whole job-search process, including discovery, research, applications, employability work, interviews, monitoring, and learning from outcomes.

Visual: [Hax goal and rudimentary run lifecycle](../diagram/001-hax-goal-and-run-lifecycle.drawio) ([PNG preview](../diagram/001-hax-goal-and-run-lifecycle.png))

Hax must not feel like a command centre, form wizard, or employee taking tickets. The user should be able to speak naturally:

- "what have you got for me?"
- "this Palantir role looks mad, am I even close?"
- "watch Notion, their career page is here"
- "I keep getting rejected. What am I doing wrong?"
- "cool, do the research while I sleep"

## Locked decisions

- Hax is a job-search and employability agent first, while still being a natural conversational companion to the user.
- A user message can contain more than one request. The system must not force it into one rigid intent bucket.
- HaxJobs can use work-shape policies to choose an appropriate amount of work, tools, cost, and persistence for a request. These policies guide resources and safety; they do not limit what Hax can understand or attempt.
- Work shapes are invisible product machinery. They must not make Hax speak like a command centre or force every request through a closed list of intents.
- Long-running work exists. A company career-page link may lead to registration, research, scraping, source discovery, and ongoing monitoring rather than one blocking reply.
- A strong search uses a portfolio of access paths. Hax must not treat job boards, company sites, recruiters, referrals, communities, direct contact, or agencies as the one universally correct channel.
- Understanding an employer and positioning the person strongly for that employer is a core HaxJobs capability.
- When important evidence is missing, Hax can prepare and help complete a relevant project so the person becomes more qualified rather than merely appearing more qualified.
- HaxJobs has several product moats. Employer-specific positioning and evidence creation are two of them, not one singular moat.
- Get out of the model's way when it is reasoning. Constrain consequences instead: available tools, permissions, external side effects, budgets, evidence requirements, and verification.
- Hax may combine known procedures, improvise a new route, ask for missing information, or create linked operations when the user's goal demands it.
- This note is only about behaviour and lifecycle. It does not choose the data model, context algorithm, prompt content, or UI.

## Locked principle: work shapes guide resources, not reasoning

The same friendly Hax should be able to choose different work shapes:

| Work shape | What it means | Example |
|---|---|---|
| Conversation | Explain, advise, react, or discuss. No product operation is needed. | "Do you think this role is actually good?" |
| Inspect | Read a known job, company, decision, pack, or profile evidence and discuss it. | "Why did you score Notion at 62?" |
| Immediate task | A bounded action that can finish during the current interaction. | "Evaluate job 123." |
| Investigation | Multi-source work with a larger budget and evidence-bearing result. | "Research this company and tell me whether it is worth chasing." |
| Watch / monitor | Register a durable target, then check it again later. | "Keep an eye on this careers page." |
| Career intervention | Work aimed at becoming more employable, not merely judging a job. | "What would get me ready for FDE roles?" |
| Approval-bound action | Prepare an external action, but pause for exact user approval before sending or submitting anything. | "Draft an outreach message to this recruiter." |

These examples are not a closed taxonomy. If a request does not fit them cleanly, Hax still handles the request and the system chooses suitable resources without rejecting it for classification reasons.

A single message may create more than one shape:

> "Check this company, tell me whether it is worth my time, and watch its jobs."

That is an investigation plus a monitoring request. Hax can answer naturally while the system creates two linked operations.

## Decided lifecycle shape: one message can create several runs

The word "run" can get overloaded. A clean mental model is:

```text
Conversation
  -> user message
  -> interaction
  -> zero or more operations
  -> Hax reply now, plus later updates where work continues
```

- **Conversation:** the ongoing relationship and message history.
- **Interaction:** one user message and Hax's immediate handling of it.
- **Operation:** a bounded piece of work created by that interaction. It can be instant or long-running.
- **Update:** a later result, progress report, question, or approval request attached back to the same conversation.

Example:

```text
User: "Watch Stripe's careers page and tell me if backend roles show up."

Interaction:
  - understands Stripe, careers page, backend track, monitoring request

Operations:
  - inspect and register Stripe as a company/source
  - run an initial careers-page scan
  - create a recurring watch

Immediate Hax reply:
  - confirms what he is checking and gives the first useful result if available

Later update:
  - reports new matching role, uncertainty, or a failed source check
```

The shape is decided. These labels are working names and may change when implementation exposes better terminology:

- a conversation is the long-lived relationship
- an interaction handles one user message and its immediate reply
- an operation is durable work with its own state
- a model run is one disposable internal attempt to advance an operation
- an update returns later progress or results to the conversation

A failed model run can be retried without losing the operation. An operation can outlive the interaction that created it. The conversation can continue for months.

## Locked rudimentary end-to-end lifecycle

1. **Receive the message**
   - Identify conversation and user.
   - Keep the raw user wording. Do not throw it away after classification.

2. **Interpret what the user means**
   - What is the user trying to achieve?
   - Which subjects are involved: a job, company, career track, application, interview, or general career concern?
   - Is the request conversational, immediate, investigative, ongoing, approval-bound, or mixed?
   - Does Hax have enough information, or should he ask one useful question first?

3. **Choose operations and budget**
   - A normal discussion may need no operation.
   - A simple saved-job question may need one read operation.
   - A career-page link may create an investigation plus a watch operation.
   - The chosen shape controls tool access, time budget, provider budget, whether work continues after the reply, and what must be saved.

4. **Do the work safely**
   - Short work can finish before Hax replies.
   - Long work should create a durable operation, report that it has started, and continue independently.
   - External side effects stop at an approval gate.

5. **Reply like Hax, not like a workflow engine**
   - The user gets a human answer first.
   - Hax can state what he found, what he started, what he needs, and what happens next without dumping internal categories.

6. **Save the meaningful result**
   - Save facts, sources, decisions, new watch targets, produced artifacts, operation status, and evidence needed later.
   - Do not save every model sentence as truth.

7. **Report later work back into the conversation**
   - A completed investigation or monitor result becomes a new Hax update the user can discuss naturally.
   - It is not a detached background log nobody sees.

## Important guardrail

Do not build a rigid intent classifier that forces every message into exactly one label before Hax can respond.

The classifier should be a small interpretation step that returns something like:

```text
main goal: watch this company
secondary goal: assess whether it is worth pursuing
subjects: company, career page, backend track
work needed: investigation + monitoring
needs approval: no
needs clarification: maybe, only if role preference is unknown
```

It should help choose resources. It should not replace the agent's ability to understand a mixed natural sentence.

## Discussion update: user answers

### Confirmed direction

- The conversation -> interaction -> operations -> updates order matches the intended meaning of session and run, though the model needs more detail later.
- Hax is conversational and should be transparent about work he starts, finds, cannot verify, or needs from the user.
- Monitoring is an intent, not a phrase match. "Watch this company," "I think they may hire soon," and "keep an eye on them" can all lead to the same underlying need after natural-language interpretation.
- Helping the user become fit for a role is normal Hax behaviour. It should not feel like a separate clinical product mode.
- How later results appear to the user remains open. It will likely be a mix, but that is an interface discussion for later.

### Correction to the discussion method

We should not choose lifecycle mechanics from abstract agent patterns first.

First map the real manual process of finding work, getting considered, applying, interviewing, and recovering from rejection. Then ask where Hax can make each part faster, more thorough, or more reliable without making the experience robotic.

The agent system is the machinery. The manual job-search process is what the machinery must serve.

## Research frame: how people actually get hired

"Where did you find the vacancy?" and "what got you hired?" are different questions.

A person can discover a role through LinkedIn, receive an employee referral, apply through the company ATS, and win the role after a strong interview. Calling LinkedIn or referrals alone "the way they got hired" loses the chain that Hax needs to understand.

The manual needs to map five linked parts:

| Part | Question |
|---|---|
| Opportunity discovery | Where do suitable vacancies and early hiring signals appear? |
| Access | How does a person get noticed: direct application, recruiter, referral, community, or direct contact? |
| Qualification | How do they decide whether the role, company, location, pay, and work authorization are worth pursuing? |
| Conversion | What turns a lead into an interview, offer, or rejection? |
| Learning | What should change after outcomes or repeated rejection patterns? |

There is no one universally best method. The right mix changes with career track, seniority, geography, work authorization, sector, company size, and how visible the vacancy is.

## Current evidence base

The full July 2026 research pass lives in [research/2026-job-search-patterns.md](research/2026-job-search-patterns.md).

It covers:

- current UK vacancy and tech-market data
- 2025 and 2026 Reddit success and failure reports
- current LinkedIn and X recruiter/candidate reports
- Greenhouse and Ashby application-source data
- the supplied ATS, sponsor, company, and internship materials
- the CareerOps manifesto
- contradictory tactics and what the evidence can actually support

## Provisional patterns, not locked decisions

The evidence currently points to these working ideas:

1. Search across a portfolio of channels instead of depending on one board.
2. Use boards, social posts, and lists for discovery, then verify against the employer's current source.
3. Qualify a lead before spending serious effort on it.
4. Optimize for attempts that produce interviews, not raw application count.
5. Combine formal applications with genuine human access where available.
6. Use truthful searchable language, then back it with evidence.
7. Value freshness and liveness without inventing an early-application multiplier.
8. Treat discovery, application, interview preparation, outcome, and learning as one process.
9. Change the strategy for the user's career track, seniority, geography, work authorization, and sponsorship needs.
10. Keep source, date, confidence, and entity identity for every external claim.
11. Explain uncertainty instead of pretending contradictory recruiter advice has one universal answer.
12. Re-measure tactics from the user's own replies, interviews, offers, and rejections.

These are candidates for HaxJobs principles. We still need to discuss and accept, reject, merge, or rewrite them one by one.

## Locked principle: the application is a positioning campaign

Finding a vacancy only answers "where is the opening?" The harder question is "why should this company choose this person?"

For a promising opportunity, Hax should understand:

1. what the company is trying to achieve or fix
2. what the recruiter, hiring manager, and job description are selecting for
3. which parts of the person's real evidence answer that need
4. which positioning angle makes the overlap easiest to see
5. which tone, materials, access path, and interview stories suit this company
6. which likely objections need honest answers

Marketing means selecting and presenting the strongest relevant evidence. Selling means giving the employer a concrete reason to take the next step.

If the evidence is not there, Hax should switch from positioning to creation. It can research what proof the role demands, prepare a relevant project, help the person complete it, verify what was actually built and understood, then add that new evidence to the profile. A planned or unfinished project cannot be presented as completed work, but Hax is allowed to create the experience rather than merely work around the gap.

This is one HaxJobs moat among several. Discovery sources are widely available. A durable understanding of the person, joined with role and company research, evidence creation, positioning, and outcome feedback is much harder to copy.

## What this means for Hax, before any automation

Hax needs to understand this full manual chain:

```text
person's tracks, constraints, and evidence
-> signals from several channels
-> verified lead
-> qualified opportunity
-> one or more access paths
-> evidence-bearing application or conversation
-> interview preparation
-> outcome
-> changed strategy
```

Only after the manual is settled should we decide how sessions, operations, tools, context, and automation represent it.

## Decision state

This note records the current decision on Hax's product goal and rudimentary run lifecycle. It is decided, not permanently final. Later implementation evidence can change the terminology or expose a better shape.

It deliberately does not decide the internal context system, model prompts, durable data model, tool catalogue, skill catalogue, scheduler, worker design, or interfaces. Those concepts build on this one.

The remaining provisional job-search patterns are research inputs for later product behaviour discussions.
