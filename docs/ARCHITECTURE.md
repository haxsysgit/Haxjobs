# HaxJobs Architecture

## Architecture summary

HaxJobs is a stateful web application and workflow coordinator sitting above Hermes.

```text
Browser extension / manual input / Hermes search
        ↓
     HaxJobs API
        ↓
Database: jobs, applications, profile, packs, contacts, tasks
        ↓
HaxJobs UI: dashboard, pipeline, profile, inbox, outreach
        ↓
Hermes task queue integration
        ↓
Hermes performs analysis, generation, browser automation, and contact lookup
```

## Main boundaries

### UI layer

Shows the user what is happening:

- saved jobs
- application statuses
- generated documents
- next actions
- user profile
- saved answers
- contact/message drafts
- Hermes task state

### API layer

Owns CRUD and workflow transitions:

- create saved job
- normalize job snapshot
- update application status
- attach documents
- create Hermes task
- record Hermes result
- manage profile facts
- manage saved answers

### Data layer

Stores durable job-search memory.

Start simple with SQLite locally. Use Postgres later if deployment needs it.

### Hermes integration layer

Coordinates work that needs agent reasoning or browser automation.

HaxJobs should create tasks. Hermes should complete them and write back structured results.

## Recommended MVP stack

Current repo already has a web app direction. Keep that unless there is a strong reason to reset.

- Backend: Python / FastAPI
- Frontend: Vue 3 / Vite
- Local database: SQLite
- Future production database: PostgreSQL
- Browser extension: Manifest V3
- Document storage: local filesystem first
- Agent integration: Hermes task queue first, MCP/API later

## Core modules

### Jobs

Represents an opportunity, not an application attempt.

A job can come from:

- Hermes search
- browser extension save
- manual URL paste
- imported list

### Applications

Represents the user's attempt to pursue a job.

Tracks status, fit score, sponsorship risk, notes, and next actions.

### Profile

Stores the user's career truth and reusable application answers.

### Application Packs

Stores generated documents and their relationship to jobs/applications.

### Contacts and Outreach

Stores relevant people and approved/drafted/sent messages.

### Hermes Tasks

Stores work requests and results.

Examples:

- `analyze_job`
- `generate_pack`
- `apply_assist`
- `find_contacts`
- `draft_outreach`
- `refresh_status`

## Hermes task lifecycle

```text
pending → running → needs_user_input → completed
                  ↘ failed
                  ↘ cancelled
```

Tasks should include:

- type
- target entity
- prompt/instructions
- input payload
- result payload
- status
- created_at
- updated_at
- error if failed

## Design choice: task queue over direct control

For MVP, prefer HaxJobs storing pending tasks and Hermes polling/processing them.

This is simpler than trying to keep a live browser session or realtime agent connection inside the web app.

## Safety boundary

HaxJobs should store approval checkpoints as first-class records.

Examples:

- application final submit approval
- outreach message approval
- legal answer confirmation
- salary answer confirmation

If no approval exists, Hermes should stop and ask.
