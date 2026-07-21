# HaxJobs Product

## What HaxJobs is

HaxJobs is a career agent platform. Its job is to help one person get interviews and become more employable. It does this by finding opportunities, understanding companies, evaluating fit, preparing applications, tracking outcomes, and building the person up for roles they are not ready for yet.

HaxJobs is not a job board scraper, an automatic application spammer, a per-job CV rewriter, or a generic chatbot. It is built around the real job-search process: discover, access, qualify, convert, and learn.

The CLI comes first. The web app is a skin over the same actions. A future cloud worker will run discovery and monitoring continuously.

## Hax, the agent

Hax is the agent inside HaxJobs. The user talks to Hax like a smart friend who knows the job market.

Hax is conversational, not a command centre. The user can speak naturally:

- "what have you got for me?"
- "this Palantir role looks mad, am I even close?"
- "watch Notion, their career page is here"
- "I keep getting rejected. What am I doing wrong?"

Hax speaks like a sharp, grounded 23-year-old engineer talking to a smart friend. Simple verbs. No corporate buzzwords. No AI writing patterns. Natural rhythm. Concrete details.

Hax reasons freely. HaxJobs controls what Hax can do, what tools are available, what data it sees, what gets saved, what costs are incurred, and what external effects require approval.

## The product moats

HaxJobs has several things that are hard to copy:

1. **Deep career memory.** Long-lived understanding of the person across skills, projects, experience, education, evidence, goals, constraints, and outcomes. Not a flat JSON file.

2. **Multi-channel discovery.** Searches across job boards, company ATS pages, social posts, and community listings. No single source is treated as universally best.

3. **Company and recruiter intelligence.** Understands what a company is trying to achieve, what the hiring manager is selecting for, and how to position the person in the strongest truthful light.

4. **Employer-specific truthful positioning.** Selects the right evidence and tone for each employer instead of blasting the same CV everywhere.

5. **Evidence creation.** When important evidence is missing, Hax can design real job-relevant projects, help complete them, verify what was built, and add that new evidence to the profile. Unfinished work is never presented as completed.

6. **Interview preparation.** Prepares the person for the specific company's interview process using what it knows about both sides.

7. **Outcome-driven learning.** Tracks what worked and what did not, then adjusts strategy. Every rejection becomes a datapoint, not a dead end.

## How it works

### The conversation model

A conversation is the long-lived relationship with Hax. One message can create several pieces of work:

- an immediate answer during the same reply
- an investigation that runs for a few minutes
- a standing watch that checks a company's careers page for months

```
Conversation
  → user message
  → interaction (immediate handling)
  → zero or more operations (durable work)
  → Hax reply now, plus later updates where work continues
```

Hax talks like a person, not a workflow engine. When work continues after the reply, the user gets an update later that they can discuss naturally.

### Standing commitments

A standing commitment is Hax's promise to keep returning to work. Examples:

- "Watch Stripe for backend roles"
- "Let me know if anything backend comes up at Notion"
- "Keep an eye on that careers page"

Commitments have lifecycles:

| State | Meaning |
|---|---|
| Active | Work is happening now or in the background |
| Paused | User asked to hold the work |
| Waiting for approval | Work is ready but needs user approval for an external action |
| Suspended | Source keeps failing or dependency is unavailable |
| Complete | Work finished (terminal) |
| Cancelled | User or policy ended the work (terminal) |

Commitments survive chat sessions, model retries, and system restarts. A cron job or scheduler wakes HaxJobs to check standing watches, then sleeps again. Continuous means Hax remembers to return, not that one process runs forever.

### Work shapes

Hax chooses different work shapes depending on the request:

| Shape | What it means |
|---|---|
| Conversation | Explain, advise, react, or discuss |
| Inspect | Read a known job, company, decision, or profile and discuss it |
| Immediate task | A bounded action that finishes during the reply |
| Investigation | Multi-source work with evidence-bearing result |
| Watch / monitor | Register a durable target, check it again later |
| Career intervention | Work toward becoming more employable, not just judging a job |
| Approval-bound | Prepare an external action, pause for exact user approval |

These guide resources and safety. They do not restrict what Hax can understand. A single message can create more than one shape.

### What Hax can do

Read, research, evaluate, prepare, and recommend without approval.

Apply, send, contact, and publish with explicit user approval every time.

### What Hax protects

- The user's evidence and personal data
- Truth: supported facts vs. user claims vs. inference vs. unknowns
- Freshness: source dates and observation times are part of the evidence
- Privacy: external actions require approval; internal work is confidential

## The job search lifecycle

HaxJobs maps the real manual process:

```
person's tracks, constraints, and evidence
→ signals from several channels
→ verified lead
→ qualified opportunity
→ one or more access paths
→ evidence-bearing application or conversation
→ interview preparation
→ outcome
→ changed strategy
```

### How the pieces connect

1. **Profile.** Everything starts from the user's profile and evidence. Skills, projects, experience, education, work authorization, preferences, and constraints. Each claim carries its source, confidence, and verification date.

2. **Discovery.** Hax searches across job boards (Greenhouse, Ashby, Lever), company career pages, and other channels. Discovery is deterministic-first with LLM enrichment on top.

3. **Evaluation.** Hax compares each found job against the user's career direction and constraints. Hard constraints (role type, language, location, sponsorship) are checked first. Then fit is assessed honestly against real evidence.

4. **Application packs.** For strong fits, Hax prepares application materials using reusable role-specific CV variants and the user's verified evidence. No fresh CV for every job. Every claim is traceable to a source.

5. **Decisions.** Every job gets a recorded decision: apply, maybe, save, skip, or reject. These feed back into the learning loop.

6. **Employability.** For weak fits, Hax does not just say "score 47%." It explains what is missing, builds a roadmap, finds resources, suggests proof-building projects, and tracks progress. The goal is to make the person fit, not just measure the gap.

## What is built

Plan 004 conversational runtime with durable tool effects:

- Provider boundary with OpenAI-compatible adapter and fake client (DeepSeek v4 flash configured)
- Domain-free agent core with bounded tool-loop execution, durable tool execution boundaries (persist before handler, persist after handler), ToolExecutionContext, dangling call detection on resume
- Explicit tool registry with active-set enforcement, Pydantic argument validation, output-model validation, effect_kind/retry_safe metadata
- Employment layer with Hax identity, career graph (tracks, skills, evidence, gaps, constraints), normalized Jobs, typed JobAssessments (append-only, idempotent), job source fetcher
- Three employment tools: `get_job`, `inspect_job_source`, `record_job_assessment`
- Immutable session configuration (person/track scope pinned at creation)
- Content-free turn measurements (no prompt/response content in DB)
- Stable deterministic IDs for career graph migration (idempotent, repeatable)
- `haxjobs chat` CLI with `--new`/`--resume`/`--fake`/`--person-id`/`--track-id` modes
- Career profile management CLI: `haxjobs profile migrate/show/track/skill/evidence/gap/constraint`
- 248 tests, zero network in pytest

Everything from the legacy product (web app, discovery scrapers, evaluation pipeline, pack builder, decisions engine, cron scripts, FastAPI routes, React frontend) was deleted at the greenfield wipe. These rebuild from scratch on the new runtime.

## What is planned

In build order:

1. **User decisions.** Typed append-only user decisions linked to durable messages, retrievable across sessions (Plan 005).

2. **Context compaction.** Token tracking, compaction triggers, summaries, retrieval frameworks.

3. **Continuous operation.** Durable scheduled watches, worker leases, idempotent discovery, notifications with approval boundaries, and one cloud deployment path.

4. **Employability loop.** Detect recurring missing skills, build realistic roadmaps, find and rank resources, suggest proof-building projects, track progress, and recommend next moves.

5. **Outreach and communication.** Recruiter research, outreach drafts, approved connector queues (email, LinkedIn, WhatsApp, Telegram), with three-tier safety per connector: draft (safe), queue (safe), send (requires approval every time).

6. **Interview simulation.** Recruiter agent, applicant agent, and evaluator agent in a closed-loop simulation using the user's profile and the real job description.

## What HaxJobs is not

- A generic chat wrapper
- A coding-agent clone
- An automatic application spammer like LoopCV
- A per-job CV rewriting service
- A collection of separate CLI, API, and cron implementations
- A "score and forget" job matcher

The shortest description: a career agent built around employability.
