---
status: paused
created: 2026-07-17
scope: Behavioural reference for a future company-watch capability
paused_reason: The discussion modelled too much product domain before testing a minimal job-native agent harness
continued_in: discussion/004-minimal-job-native-harness.md
builds_on:
  - discussion/001-hax-goal-and-run-lifecycle.md
  - discussion/002-durable-work-and-continuity.md
research:
  - discussion/research/2026-job-search-patterns.md
fixtures:
  - discussion/fixtures/003-five-job-sample.md
---

# Company watch vertical slice

> [!warning] Paused as the active design path
> This note moved too quickly from a useful job-search scenario into a large domain model. Keep the accepted user-facing behaviour as research input, but do not treat the proposed objects, relationships, or future rounds as the architecture. The active discussion continues in [004-minimal-job-native-harness.md](004-minimal-job-native-harness.md).

## Why the design method changed

We are no longer designing context, memory, tools, prompts, storage, workers, and interfaces as separate horizontal systems.

Those topics only become useful when they solve a real job-search journey. We will now design one complete slice from the user's words to a useful employment outcome. Each slice must connect behaviour, evidence, state, permissions, failure handling, and delivery.

The first slice is:

> A user has an active career direction and real constraints. They mention a company they care about and ask Hax to keep an eye on it.
>
> Hax understands the request, uses the relevant user profile and evidence, identifies trustworthy company hiring sources, creates and explains any standing work, checks the source later, detects a new role, decides whether it may be suitable, avoids duplicate reports, updates the user naturally, and records the user's later decision or outcome.

Development fixture: [five jobs sampled from the old HaxJobs database](fixtures/003-five-job-sample.md). The sample provides real source, identity, completeness, evaluation, and outcome-continuity problems for this slice to handle. It is evidence for the design, not a schema to preserve.

Example request:

> "I want UK backend work with sponsorship. Stripe looks interesting. Keep an eye on them and tell me when there is something worth pursuing."

## Decisions carried into this slice

These are already decided direction:

- Hax is conversational on the surface. HaxJobs owns durable state, evidence, permissions, retries, and truthful effects underneath.
- One user message may create several operations.
- Hax may reason freely. The system constrains consequences through permissions, budgets, evidence, verification, and approval gates.
- A standing commitment is Hax's durable promise to return to work.
- A cadence says when the work is next due.
- A scheduler only wakes the system. It is not the promise and it is not a permanently running process.
- Each check is one bounded attempt that starts, saves its result, and ends.
- Quiet checks should normally remain quiet.
- Useful changes and honest failures return to the conversation as updates.
- Suitability follows the linked career direction and current constraints, while preserving the wording and meaning of the original request.
- Hax must not invent company facts, vacancy facts, sponsorship support, or user evidence.
- This remains a greenfield design. Current source code, tables, routes, and names do not constrain the result.

## What the complete slice must settle

Before implementation planning, this note must agree the following as one connected design:

1. the user journey
2. the real manual job-search behaviour Hax is copying and improving
3. the user information needed for this watch
4. the company and hiring-source information needed
5. product objects and their relationships
6. every trigger that may create work
7. model reasoning versus deterministic work, research, saved actions, and scheduled work
8. initiative and approval boundaries
9. durable current state and useful history
10. evidence, company identity, job identity, and deduplication
11. failure and recovery behaviour
12. delivery timing and suppression of useless noise
13. the first thin-build boundary
14. the smallest concrete persistence model that supports the agreed behaviour

Nothing becomes an implementation requirement until it is recorded as decided direction.

# Discussion round 1: the user journey and the manual job

## 1. The small idea

A company watch is not just "check this URL every day."

A capable person doing this manually would need to remember what they want, identify the real company, find the employer's current hiring source, inspect the existing vacancies, return later, notice what changed, reject irrelevant roles, and decide whether the remaining role deserves effort.

Hax is taking over that repeated attention. The value is not the timer. The value is preserving the person's search criteria, checking trustworthy evidence, and only bringing back something useful.

## 2. What a capable person would do manually

For the Stripe example, a careful person would roughly do this:

1. Write down what counts as relevant: UK backend work, sponsorship required, suitable seniority, acceptable location and work mode, and any salary floor.
2. Confirm which Stripe is meant and find Stripe's official careers page.
3. Follow the careers page to the actual hiring system or job records.
4. Inspect the currently open roles so there is a baseline.
5. Save the job links or identifiers already seen.
6. Return later and compare the current list with the baseline.
7. Open genuinely new roles and check the hard constraints first.
8. Read promising roles more closely against the person's skills and evidence.
9. Check uncertain claims, especially location, work mode, closing date, and sponsorship.
10. Tell the person once, with the live source and the reasons it may be worth pursuing.
11. Remember whether they chose to apply, save, skip, or reject it.
12. Change the future search when their goals or constraints change.

People are bad at doing this consistently across many companies. Bookmarks go stale, the same role gets rediscovered under a new URL, and sponsorship assumptions become fake facts. Hax should improve the process by keeping identity, dates, evidence, and the person's current criteria together.

## 3. Recommended user journey

### Step A: the user asks naturally

The user should not configure a monitor form first. They say:

> "I want UK backend work with sponsorship. Stripe looks interesting. Keep an eye on them and tell me when there is something worth pursuing."

Hax should understand at least:

- company of interest: Stripe
- linked career direction: backend work
- geography: UK
- hard constraint: sponsorship required
- requested behaviour: inspect now and continue watching
- delivery condition: report something worth pursuing, not every change

Hax keeps the raw wording as evidence of what the user asked. A structured interpretation helps run the product, but it does not replace the original request.

### Step B: Hax checks whether it can start honestly

Hax should not ask a question merely because some profile field is blank.

It should ask only when the missing answer could materially change the work. For example:

- uncertain company identity can make Hax watch the wrong business
- no active career direction makes "worth pursuing" undefined
- conflicting sponsorship instructions can change whether most roles are excluded

A missing salary preference does not need to block the watch. Hax can continue, record salary as unknown, and ask later when a real role makes it relevant.

### Step C: Hax verifies the company and source

Hax identifies the company, finds the official careers page, and follows it to the employer's actual hiring source where possible.

The official company source outranks job boards, social posts, CSV lists, and search-engine results. Secondary sources can help Hax discover the official source, but they should not become the permanent authority when a current employer source exists.

The first check happens immediately. This matters for three reasons:

1. it proves that the source works
2. it records the jobs that already exist as the baseline
3. it may find an already-open role worth discussing now

Creating a watch without a successful or honestly failed baseline check would give the user false confidence.

### Step D: Hax explains what it started

Recommended reply:

> "Yep. I'm watching Stripe's official hiring source for UK backend roles. I'll treat sponsorship as required and check anything promising against your current backend track. I'm doing a first pass now so I know what is already open. After that I'll only nudge you for a new role worth looking at, or if the source keeps failing."

This reply is conversational, but it still makes the promise inspectable. It tells the user:

- which company Hax understood
- what role direction and hard constraint it is using
- which kind of source it will trust
- that an initial check is happening
- what will and will not create future noise

Hax does not need to dump internal IDs, operation names, or scheduler details.

### Step E: the initial check establishes a baseline

Existing jobs are not silently discarded. They are classified into three simple outcomes:

- **worth discussing now:** an already-open role may be suitable enough to show immediately
- **seen but not useful:** record its identity so it is not later announced as new
- **uncertain:** save what is missing and investigate only when the potential value justifies it

This is important. "New to Hax" and "newly posted by Stripe" are different claims. Hax must not pretend an old role is newly published merely because it saw it for the first time.

### Step F: later checks are bounded and quiet by default

When the standing commitment becomes due, one check attempt:

1. verifies the source is still the same source
2. fetches the current jobs
3. normalizes company and job identity
4. compares the result with previous observations
5. records new, changed, closed, duplicate, and unchanged jobs
6. runs cheap hard-constraint checks on genuinely relevant changes
7. uses deeper judgement only for promising or ambiguous roles
8. saves the attempt result and next due time
9. ends

If nothing useful changed, Hax says nothing.

### Step G: a promising new role appears

A new Stripe backend role should not go straight from URL detection to "perfect match."

Hax first separates:

- **hard blockers:** wrong country, impossible work authorization, clearly wrong seniority, closed role
- **known positives:** relevant function, acceptable location, evidence-backed skill overlap
- **unknowns:** sponsorship willingness, salary, team location, exact work mode
- **deeper fit:** whether the person's actual evidence answers what the role is selecting for

The first watch slice only needs a basic suitability decision: worth pursuing, maybe worth investigating, or not worth the user's attention. A full application campaign is a later slice.

### Step H: Hax reports the role once

Recommended update:

> "Stripe just posted a backend role that looks worth a look. It matches your backend track and UK preference. Your API and distributed-systems work gives us a real angle. I cannot verify sponsorship for this vacancy yet, so I would not call it application-ready. Want me to inspect the role properly?"

A useful update contains:

- what changed
- why Hax thinks it matters to this user
- what evidence supports that view
- what remains uncertain
- the live employer source
- a sensible next action

The same role must not be announced again because its title changed slightly, tracking parameters changed, or the ATS produced another URL.

### Step I: the user's response changes durable state

The user may say:

- "apply"
- "save this for Friday"
- "maybe, research the sponsorship first"
- "skip it, too senior"
- "reject anything requiring three office days"
- "pause Stripe for now"

Hax should preserve both the immediate job decision and any broader lesson. "Skip this job" is not automatically "never show me Stripe." "Reject anything requiring three office days" may be a new temporary or durable constraint, but Hax should confirm the intended scope when unclear.

### Step I.1: clear user statements are authoritative

The profile is not allowed to overrule the person it represents.

If a job requires TypeScript and the current profile says nothing about TypeScript, Hax must treat the skill as unknown, not absent. Hax may ask the user directly:

> "This role needs TypeScript, but I do not have any TypeScript experience recorded for you. Do you have it?"

If the user gives a direct and clear answer, Hax accepts it as authoritative within its stated scope. It records the answer as user-stated, uses it in future reasoning, and does not keep asking for clarification merely because older profile data was incomplete.

This rule also applies to clear goals, preferences, constraints, corrections, and decisions. For example:

- "I have used TypeScript professionally" is a user-stated experience fact.
- "Do not show me roles requiring three office days" is a direct search constraint.
- "Skip this job, but keep watching the company" is a job decision plus a clear standing instruction.
- "I am no longer targeting data-engineering roles" changes the active search direction.

Hax must preserve the original wording and scope. It must not weaken, reinterpret, or repeatedly question a clear instruction.

User authority and evidence status are separate.

A clear user statement is enough for Hax to accept that the user has the experience. It is not automatically verified evidence that Hax can present externally as proven work. Hax should first check whether evidence already exists but has not been linked, such as a work example, private project, repository, document, or prior role.

If no useful evidence exists and the skill matters to the user's target roles, Hax may suggest a meaningful project connected to the user's existing profile. The project only becomes evidence after the user completes it and Hax verifies what was actually built and understood. Until then, Hax records:

- the experience as user-stated
- the current evidence strength as unverified or not yet linked
- any proposed project as planned, not completed

Hax must not claim that the user lacks a skill merely because it was missing from the profile. It must not claim that the skill is externally proven merely because the user stated it.

The user's word is authoritative about the user. It does not turn an external claim into fact. A statement such as "I think this company sponsors" can be preserved as the user's belief, but Hax must still verify the company or vacancy claim before presenting it as true. Safety and approval rules also remain in force for external actions.

### Step J: later outcomes close the learning loop

If the user applies, gets rejected, interviews, receives an offer, or withdraws, Hax records the outcome against the same job and career direction.

That outcome can later change:

- which roles deserve alerts
- which evidence is working
- which gaps need employability work
- whether the company watch remains useful

This slice records the outcome. It does not yet build the whole application, interview, or employability workflow.

## 4. What success looks like

The slice succeeds when:

- the user can make one natural request
- Hax interprets the company, career direction, and real constraints correctly
- the employer and source are verified rather than guessed
- the initial check establishes an honest baseline
- one bounded later check detects a genuinely new or changed role
- the role is deduplicated and given a basic suitability judgement
- the user receives one useful, evidence-bearing update
- no routine "nothing changed" message is sent
- the user's decision is saved against the same role
- failures are visible rather than hidden behind a pretend-active watch

The product result is not "the cron ran." The result is that the user did not need to keep checking Stripe and still learned about a worthwhile role in time to act.

## 5. Decided recommendations from round 1

Arinze accepted all five recommendations and all three proposed answers on 17 July 2026.

### Decided A: every new watch gets an immediate baseline check

Why: a watch that has never verified its source is not trustworthy. The baseline also prevents existing jobs from being misreported as new later.

Edge case: the source may be unavailable when the user asks. Hax should create the commitment in a blocked or retrying state, say that the first check failed, and avoid claiming the watch is healthy.

### Decided B: the watch binds to a career direction and live constraints

Why: "watch Stripe" is only useful if Hax knows what matters to this user. The original wording remains preserved, but later checks use the current linked constraints unless the user explicitly fixed a rule for this watch.

Edge case: a user moves from UK backend work with sponsorship to remote AI work. Hax should review the watch rather than silently applying the old criteria forever.

### Decided C: sponsorship unknown is not the same as sponsorship impossible

Why: an employer's sponsor licence, a recruiter claim, and sponsorship for this exact vacancy prove different things. Suppressing every unknown role may hide good opportunities. Treating every licensed company as willing to sponsor would lie.

Recommended behaviour: if the role is otherwise strong, report it as promising but unresolved, clearly naming the sponsorship uncertainty.

Edge case: if the user says "do not show me anything unless sponsorship is confirmed for the vacancy," that fixed instruction should override the default.

### Decided D: current relevant roles can be reported during the baseline

Why: the user's actual goal is to find worthwhile work, not only roles posted after the watch began.

Edge case: Hax must say "already open when I started watching," not "Stripe just posted this."

### Decided E: the watch reports useful deltas, not scraped rows

Why: people do not want a careers-page change detector. They want help deciding what deserves attention.

Edge case: a role can change materially without being new. A location change, closing-date change, or rewritten sponsorship wording may deserve an update even when the job identity remains the same.

## 6. Round 1 answers

1. **Baseline matches:** report an already-open worthwhile role immediately, while clearly saying it was already open when monitoring began.
2. **Unknown sponsorship:** report an otherwise strong role as promising but unresolved, with the uncertainty stated plainly.
3. **Interruption threshold:** a useful result from a direct company watch gets an immediate update by default. Broader discovery may use different delivery rules later.

## 7. Decision ledger

| Item | Status | Current direction |
|---|---|---|
| Design method | Decided | Build complete job-search slices, not isolated horizontal subsystems. |
| First slice | Decided | Active career direction + company interest + standing watch + new job + suitability + update + decision/outcome. |
| Immediate baseline check | Decided | Run when the watch is created. |
| Source authority | Decided | Prefer the employer's current careers or ATS source; use secondary sources for discovery and corroboration. |
| Quiet checks | Decided from 002 | Save them without routine user messages. |
| Current constraints | Decided from 002 | Re-evaluate suitability using the linked career direction and current constraints, while preserving fixed instructions. |
| Clear user authority | Decided | A direct and unambiguous user statement is authoritative about the user's experience, goals, preferences, constraints, corrections, and decisions within its stated scope. Do not ask again without a real contradiction or material change. |
| Missing profile data | Decided | Absence from the profile means unknown, not false. Ask the user when the answer materially affects the work. |
| Self-report versus proof | Decided | Accept clear self-report as user-stated truth while tracking evidence strength separately. Do not present user-stated experience as externally verified without evidence. |
| Evidence creation | Decided | First look for existing proof. If none exists and the skill matters, suggest a relevant project. Only completed and checked work becomes new evidence. |
| Existing relevant jobs | Decided | Report worthwhile baseline matches immediately with honest wording about when Hax first observed them. |
| Unknown sponsorship | Decided | Report otherwise strong roles as promising but unresolved rather than treating unknown as impossible. |
| Delivery timing | Decided for direct watches | Immediately report useful results from a company watch the user directly requested. |

# Discussion round 2: user information, company information, and shared objects

## 1. The small idea

This watch connects three different kinds of truth:

1. **what the user is trying to achieve**
2. **what is currently true about the company and its jobs**
3. **what Hax promised to keep doing**

These truths change at different speeds. Mixing them into one giant profile or one watch record would create stale and contradictory behaviour.

For example:

- "I need sponsorship" is a user constraint.
- "Stripe appears on a sponsor register" is a dated external observation.
- "Stripe will sponsor this backend vacancy" is a separate vacancy-level claim that may still be unknown.
- "Keep checking Stripe" is an operational promise.

They are related, but they are not the same fact.

## 2. Recommended user information for this slice

The first slice does not need a complete career graph. It needs the smallest trustworthy view of the user that can answer: "Would this Stripe role deserve their attention?"

### A. User identity

For one user, Hax needs a stable internal identity and the user's preferred name. Contact details are not needed merely to monitor a company.

This information is stable in normal use, but still editable by the user.

### B. Active career track

A career track is a concrete search direction, not just a job title string.

For this slice it should carry:

- a human label, such as "UK backend engineering"
- target role families and accepted title variations
- target seniority or acceptable range
- target locations
- acceptable work modes
- work-authorization position
- sponsorship requirement
- salary floor or target, when known
- role or sector exclusions
- whether the track is active, paused, or no longer pursued

The watch links to this track so "worth pursuing" has an actual meaning.

A career track can change, but it should not be silently rewritten into a different career direction. Moving from backend engineering to AI engineering is better represented as another track or an explicit transition, not a title edit that destroys the old history.

### C. Constraints

Constraints answer: "What makes a role impossible or unacceptable?"

Examples:

- sponsorship required
- must be based in the UK
- cannot relocate
- minimum salary needed for legal or personal reasons
- cannot work more than two office days

Each constraint needs:

- its meaning
- its scope, such as this track or all tracks
- whether it is hard or negotiable
- where it came from
- when the user stated or changed it
- whether it has an end condition

Hax may help interpret natural language, but it must not quietly upgrade a preference into a hard blocker.

### D. Preferences

Preferences help rank roles without automatically excluding them.

Examples:

- remote preferred
- startup preferred
- interested in payments infrastructure
- would rather avoid consulting
- Stripe is especially interesting

Preferences can be weighted roughly, but the first build does not need a fake mathematical precision score. "Strong preference," "preference," and "nice to have" are enough if ranking is needed.

### E. Fixed instructions

A fixed instruction is a rule Hax must not override through its own judgement.

Examples:

- "Never show me unpaid roles."
- "Do not contact anyone without asking me."
- "For this watch, only alert me when vacancy-level sponsorship is confirmed."

"Fixed" should mean user-controlled, not permanent forever. The user can change it. The model cannot quietly relax it.

### F. Temporary preferences

Temporary preferences need a scope or an end condition where possible.

Examples:

- "For the next month, focus on London."
- "Until this interview is over, pause new applications."
- "This week, only show me roles I can apply to quickly."

A temporary preference with no recorded scope becomes stale context. Hax should either capture an end condition or revisit it when it starts affecting later work.

### G. Skills, projects, and work evidence

Suitability cannot rely on a flat keyword list.

For the watch slice, Hax needs relevant claims such as:

- skill or capability
- where it was used
- linked project, role, document, repository, or work example
- evidence strength
- source
- last checked date where relevant
- whether it is safe to present externally as verified, user-stated, or still unsupported

The watch does not need to load every career fact for every source check. Cheap constraints decide most jobs first. Detailed evidence becomes relevant only when a role survives the basic filter.

### H. Current job-search status

Hax needs to know whether the person is:

- actively searching
- casually open
- pausing applications
- interviewing heavily
- no longer searching

This affects urgency and whether a standing watch remains useful. It should not erase the career track or history.

## 3. Stability and evidence rules for user information

| Information | Typical behaviour | Evidence rule |
|---|---|---|
| Preferred name | Stable | User statement is enough. |
| Work authorization | Changes rarely, but expiry and legal rules matter | User statement plus document or legal checking when an external claim depends on it. |
| Sponsorship requirement | Can change with immigration status | User statement is authoritative about the need. |
| Career track | Durable but can be activated, paused, or replaced | User direction is authoritative. |
| Location and work mode | Can change quickly | Keep source, scope, and stated date. |
| Salary need | Can change and may be role-specific | User statement is enough; do not infer a hard floor from market data. |
| Skills and experience | Usually durable | User statement establishes self-report; supporting evidence controls external claim strength. |
| Projects and work examples | Durable once completed | Keep evidence links and verification status. |
| Company preference | Can strengthen, weaken, or expire | Keep source and date. |
| Temporary focus | Intentionally short-lived | Keep scope or end condition. |
| Fixed instruction | User-controlled | Only the user can change or remove it. |

## 4. Recommended company information for this slice

### A. Company identity

Hax needs to know which real organisation the user means.

Minimum identity information:

- stable internal identity
- official current name
- known aliases or former names
- official web domain
- country or operating regions where useful
- source and date for identity verification
- identity confidence

A name is not enough. "Stripe," a similarly named company, a subsidiary, and an employer-of-record listing can otherwise be mixed together.

Company identity can change through renaming, acquisition, or restructuring. The history should remain linked rather than creating accidental duplicates.

### B. Company interest

"Arinze is interested in Stripe" is useful career memory even if the watch is later cancelled.

The interest should preserve:

- the company
- the user's wording or reason
- linked career track or tracks
- strength of interest when stated
- source and date
- current state, such as interested, deprioritized, or no longer interested

This is not the standing commitment. Interest describes the relationship. The commitment describes promised recurring work.

### C. Careers source

A company may have more than one hiring source:

- official careers landing page
- ATS board
- country-specific careers page
- team-specific hiring page
- official jobs API or feed

Each source needs:

- source type
- current URL or endpoint
- company identity it belongs to
- how Hax verified the relationship
- first observed and last verified dates
- confidence
- health state
- source-specific identity information, such as an ATS board token
- whether it is primary, secondary, retired, or uncertain

The standing commitment should target the company and career goal, not become permanently tied to one URL. If Stripe moves from one ATS to another, the promise remains while Hax re-verifies and changes the source used to fulfil it.

### D. Sponsorship evidence

Sponsorship must not be one company boolean.

Possible evidence has different meaning:

- licensed sponsor register entry
- company careers wording
- vacancy wording
- recruiter statement
- previous sponsorship history
- user's first-hand knowledge

Each observation needs its source, date, scope, and what it can prove. A company-level licence may support "licensed sponsor at this date." It does not support "this vacancy will sponsor this user."

### E. Hiring signals

Signals can include:

- a careers page becoming active
- a new team or location appearing
- repeated openings in one function
- recruiter posts
- funding, expansion, or restructuring news

These are dated observations, not permanent company properties. They may help prioritize checks or research, but the first walking skeleton does not need general company-intelligence monitoring.

### F. Discovered jobs

A job belongs to the employer even if it appears through several sources.

Useful information includes:

- employer identity
- source identifiers and URLs
- title and normalized role family
- location and work mode
- description
- employment type
- posting and closing dates when actually known
- first observed and last observed dates
- current liveness
- sponsorship wording or absence of wording
- source evidence
- content fingerprint or other identity signals

Known contacts are intentionally later. This watch slice can detect and discuss a job without building recruiter or hiring-manager research.

## 5. Recommended shared product objects

These are domain concepts, not a demand for one database table per row.

| Object | What it means in this slice | Important relationships |
|---|---|---|
| User | The person Hax is helping | Has career tracks, evidence, interests, decisions, and outcomes. |
| Career track | One coherent employment direction | Belongs to user; carries constraints and preferences; guides suitability. |
| Constraint or preference | A scoped rule or ranking signal | Usually belongs to a career track; may apply globally or temporarily. |
| Evidence | Support for a user capability or claim | Belongs to user; can relate to projects, work, education, and career tracks. |
| Company | The real employer identity | Has sources, jobs, interests, and commitments. |
| Company interest | The user's durable interest in a company | Connects user, company, reason, and relevant career tracks. |
| Careers source | A verified place where the company publishes hiring information | Belongs to company; is checked by attempts; can be replaced or retired. |
| Standing commitment | Hax's promise to keep checking for a defined goal | Connects user, company, career track, criteria, state, and source set. |
| Cadence | When the commitment is next due | Can begin as fields on the commitment rather than a separate object. |
| Check attempt | One bounded execution of the watch | Belongs to commitment; reads sources; records observations, failures, and completion. |
| Job | One employer opportunity with stable identity across observations | Belongs to company; can be seen through several source records. |
| Finding | A useful interpretation of an observed change | Comes from an attempt; may refer to a job, source failure, or material change. |
| Update | What Hax actually delivered to the user | Can report one or more findings; records delivery state without claiming it was read. |
| Decision | The user's current judgement about a job | Connects user, job, and career track; includes apply, maybe, save, skip, or reject. |
| Application | A real application event | Created only when an application actually exists, not when the user says maybe. |
| Outcome | What later happened | Relates to the application or job journey and can change future strategy. |

## 6. The relationship map in plain language

```text
User
  -> pursues Career Track
  -> has Constraints, Preferences, Instructions, and Evidence
  -> is interested in Company

Company
  -> publishes through one or more Careers Sources
  -> has Jobs

Standing Commitment
  -> belongs to User
  -> watches Company for one Career Track
  -> uses current scoped Constraints plus fixed watch instructions
  -> has a cadence and many bounded Check Attempts

Check Attempt
  -> checks one or more verified Careers Sources
  -> observes Jobs and source failures
  -> produces zero or more Findings

Finding
  -> may be saved quietly
  -> may become an Update

Update
  -> returns to the User
  -> may lead to a Decision

Decision
  -> may later lead to an Application
  -> Application may later receive an Outcome
  -> Decision and Outcome can change future search strategy
```

## 7. Important separations

### Company interest is not a watch

The user can remain interested in Stripe after cancelling monitoring. Hax may later use that interest in research or conversation without pretending an active promise still exists.

### Commitment is not a source

The promise is to monitor Stripe for suitable work. A URL is only one current means of fulfilling it.

### Finding is not an update

Hax may find that nothing changed, a job closed, or a low-value role appeared. Those findings can be saved without notifying the user.

### Decision is not an application

"Maybe" and "save" are decisions. "Apply" expresses intent and may start application work. An application record should exist only when a real application process starts or is submitted.

### User truth is not external proof

The user is authoritative about their own goals, preferences, and self-reported experience. External claims still need evidence before Hax presents them as established facts.

## 8. Career memory versus operational state

This is not a storage choice yet, but the ownership boundary matters.

### Career memory

These facts should remain useful outside this watch:

- career track
- constraints and preferences
- fixed and temporary instructions
- skills and evidence
- company interest
- job decisions
- applications and outcomes

### Operational state

These facts exist because Hax is currently fulfilling the watch:

- commitment state
- cadence and next due time
- source selection and health
- check attempts
- retry and suspension state
- findings
- reported-job set
- update delivery state

A job and company sit between both sides. They are external career entities used by operations and later career decisions.

## 9. Edge cases from this round

### One role fits two career tracks

The same Stripe role may fit backend engineering and AI engineering. The job should remain one job. Suitability, decisions, and watch relevance need track context so one role is not duplicated into two fake jobs.

### The company changes hiring systems

The old source can be retired and a new verified source activated without cancelling the user's standing commitment. Source history remains so Hax can explain missed checks or identity changes.

### A preference conflicts with a fixed instruction

A preference such as "remote preferred" cannot override "never show me roles requiring relocation." Fixed instructions and hard constraints win. Hax should explain a real conflict rather than blending the two into a score.

### An alias points to the wrong company

If identity confidence is weak, Hax should ask before starting a permanent watch. Watching the wrong company is worse than asking one useful question.

### Company sponsorship evidence becomes stale

Hax keeps the old dated observation but stops treating it as current. Stale evidence is history, not present proof.

## 10. Round 2 working recommendations

### Recommendation A: one active track for the walking skeleton

The first build should support one active career track. The domain model should not make additional tracks impossible, but the first slice should not solve cross-track ranking and delivery.

### Recommendation B: separate watches by career track

A company interest may connect to several tracks. Each standing watch should have one primary track so suitability and changing constraints remain understandable.

If the user later wants Stripe watched for both backend and AI roles, Hax can create two related commitments under one company interest rather than one vague combined filter.

### Recommendation C: commitments follow the company goal, not a fixed URL

Hax may replace a failed or retired source after verifying the new official source. This does not require approval because it is the obvious next step needed to fulfil the original promise. Hax reports the change only when confidence drops, coverage may have been lost, or repeated failure affects trust.

### Recommendation D: represent hard constraints separately from preferences

A hard constraint can exclude a role. A preference ranks it. Hax can interpret direct wording such as "I need sponsorship" as hard. If wording is ambiguous, it should not silently suppress a role. It can preserve the uncertainty and ask when a real decision depends on it.

### Recommendation E: keep company-level and vacancy-level claims separate

This is mandatory for sponsorship, location, work mode, and hiring status. A fact about the company must not automatically become a fact about every job.

### Recommendation F: do not make every concept a separate table

Cadence can initially live with the commitment. Constraints and preferences can initially be typed entries under a track. Findings may be attempt-history records. The table boundary comes after we decide which records need independent identity, querying, and lifecycle.

## 11. Questions that need Arinze's judgement

1. **Multiple tracks at one company:** Should one Stripe interest support separate track-specific watches, such as backend and AI, rather than one combined watch? My recommendation is yes. The user sees one company relationship, while Hax keeps suitability coherent per track.
2. **Source replacement:** May Hax automatically replace a careers source when it verifies that the company moved to another official source? My recommendation is yes, with an update only when confidence or monitoring coverage was affected.
3. **Ambiguous constraints:** When Hax cannot tell whether something is a hard requirement or a preference, should it avoid excluding roles and ask only when the distinction affects a real finding? My recommendation is yes. Asking about every blank field up front would make Hax feel like a form.

## 12. Round 2 decision state

| Item | Status | Current direction |
|---|---|---|
| One active track in first build | Working recommendation | Prove one coherent watch before multi-track ranking. |
| Track-specific commitments | Open | Recommend separate watches per track under one company interest. |
| Company interest versus commitment | Working recommendation | Preserve interest independently from active monitoring. |
| Company versus source | Working recommendation | Commitment targets company goal; verified sources can change. |
| Source replacement | Open | Recommend automatic replacement after verification. |
| Hard constraints versus preferences | Working recommendation | Store and apply them differently. |
| Ambiguous constraint handling | Open | Recommend ask only when a real decision depends on the distinction. |
| User statement versus evidence | Decided earlier | User statement establishes user-stated truth; evidence strength remains separate. |
| Company-level versus vacancy-level claims | Working recommendation | Keep scope explicit and never inherit company facts blindly onto a job. |
| Object-to-table mapping | Intentionally unresolved | Decide after behaviour, history, identity, and query needs are agreed. |

## Next round after these answers

Round 3 will map every trigger through Hax's behaviour: what needs model judgement, what normal Python should do, what is saved, what is scheduled, and what appears to the user.
