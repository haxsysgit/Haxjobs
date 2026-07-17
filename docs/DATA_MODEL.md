# Data Model

This file separates current storage from the planned career memory model.

## Current storage

SQLite defaults to `state/haxjobs.db`. The profile defaults to `state/profile.json`.

### Active tables

| Table | Current purpose |
|---|---|
| `discovered_jobs` | Raw normalized jobs before promotion |
| `jobs` | Promoted jobs, classification, pack, and outreach status |
| `evaluations` | One current evaluation per job, including profile snapshot and report |
| `decisions` | Append-only apply, maybe, save, skip, or reject events |
| `profile_snapshots` | Reserved table with no current writer |
| `activity_log` | Product and pipeline events |
| `whitelist` | Patterns allowed through filters |
| `outreach_contacts` | Contact records linked to jobs |
| `outreach_drafts` | Unsent draft records linked to jobs and contacts |

Foreign keys are enabled. Job deletion cascades to evaluations, decisions, contacts, and drafts. SQLite runs in WAL mode.

## Current profile

`state/profile.json` is the canonical profile file today. The schema defines personal details, skills, preferences, work authorization, experience, projects, education, profile health, and onboarding state. Current onboarding does not populate every defined field, including profile health.

It works for onboarding and evaluation, but it has limits:

- career tracks are not independent objects
- evidence is not consistently normalized
- history and verification dates are weak
- relationships are stored inside a large document
- updates are hard to query over time

## Target career memory

The planned career graph should model records such as:

- career track
- skill
- evidence
- project
- work experience
- education
- job
- company
- application
- interview
- learning plan
- resource
- goal
- constraint
- preference
- contact
- outcome

Each record should support:

- source
- confidence
- last verified date
- privacy level
- related career tracks
- evidence links

This model is not built. Do not add its tables one by one before the session, context, and migration design is agreed.

## Evidence levels

The target evidence vocabulary is:

1. `verified_from_cv`
2. `verified_from_github_project`
3. `verified_from_uploaded_document`
4. `user_stated`
5. `inferred`
6. `unsupported`

Outputs should map those levels to:

- safe to claim
- phrase carefully
- not enough evidence

No generated application material should promote inferred or unsupported data into a verified claim.

## Missing durable run state

The database has no proper tables for:

- agent sessions
- messages
- tool calls
- run checkpoints
- compaction summaries
- context selections
- token, latency, and cost records
- scheduled watches and durable worker leases
- learning progress

Those records should be designed together so the agent can resume, explain what happened, and avoid conflicting state.

## Migration rule

Do not keep dual write paths for compatibility. When the career-memory model lands:

1. define the new schema
2. write one explicit migration from `profile.json` and current tables
3. verify counts and evidence links
4. switch all readers and writers
5. remove the old path

Git and database backups are the rollback plan. Permanent compatibility layers are not.
