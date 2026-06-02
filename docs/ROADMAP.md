# HaxJobs Version Roadmap

## Core direction

HaxJobs is the UI, state, and workflow layer for a Hermes-powered job application pipeline.

Hermes does the heavy lifting:

- job extraction and analysis
- fit scoring
- sponsorship-risk checks
- application-pack generation
- contact discovery
- outreach drafting
- apply assistance with approval gates
- structured writeback into HaxJobs

HaxJobs does not replace Hermes. HaxJobs gives Hermes a durable product surface:

- dashboard
- saved job inbox
- application tracker
- profile/survey interface
- task queue
- pack/document library
- review and approval UI
- browser-extension capture surface

The simplest mental model:

```text
Hermes = worker / reasoning / automation
HaxJobs = interface / state / workflow / approval surface
```

## Product principles

1. Human-approved automation first.
   - Never final-submit applications without explicit approval.
   - Never send outreach without explicit approval.
   - Stop on sensitive legal, visa, salary, demographic, or uncertain fields.

2. Truthful career profile.
   - HaxJobs should collect reusable facts and answers through guided questions.
   - Hermes can ask/survey the user through HaxJobs.
   - Profile data must be evidence-backed or clearly marked as needing confirmation.

3. Durable job-search memory.
   - Jobs, applications, packs, contacts, tasks, notes, and approvals should not disappear into chat history.

4. Small useful loop before big automation.
   - First make saving, tracking, analyzing, and generating packs work.
   - Assisted applying comes later because it is risky.

---

## Version map

| Version line | Major theme | Main outcome | Detailed plan |
| --- | --- | --- | --- |
| 0.1.x | Foundation, planning, data model, local app skeleton | HaxJobs has a real backend/data base to build on | [0.1.x_Haxjobs.md](roadmaps/0.1.x_Haxjobs.md) |
| 0.2.x | Hermes task queue and job-platform ingestion foundation | HaxJobs can create work for Hermes and store results | [0.2.x_Haxjobs.md](roadmaps/0.2.x_Haxjobs.md) |
| 0.3.x | Main dashboard and core UI | User can manage jobs/applications visually | [0.3.x_Haxjobs.md](roadmaps/0.3.x_Haxjobs.md) |
| 0.4.x | Profile, survey flow, packs, refinements | Hermes can ask through HaxJobs and reuse stored user truth | [0.4.x_Haxjobs.md](roadmaps/0.4.x_Haxjobs.md) |
| 0.5.x | Chrome extension | User can save jobs from the browser into HaxJobs | [0.5.x_Haxjobs.md](roadmaps/0.5.x_Haxjobs.md) |
| 0.6.x | Firefox extension | Same capture workflow works in Firefox | [0.6.x_Haxjobs.md](roadmaps/0.6.x_Haxjobs.md) |
| 0.7.x | Assisted apply and outreach | Hermes helps apply/message, but only with approval gates | [0.7.x_Haxjobs.md](roadmaps/0.7.x_Haxjobs.md) |
| 0.8.x | Production hardening and polish | Reliability, security, deployment, and better UX | [0.8.x_Haxjobs.md](roadmaps/0.8.x_Haxjobs.md) |

---

# 0.1.x — Foundation and local product skeleton

## Theme

Set up the project properly and define the core database/workflow shape before building fancy UI.

This phase is about making HaxJobs structurally real: backend, database, migrations, base frontend, config, and clean docs.

## 0.1.0 — Project skeleton

Build:

- backend app skeleton
- frontend app skeleton
- shared development commands
- local config layout
- basic health check
- clean README/AGENTS direction docs

Recommended stack:

- Backend: Python + FastAPI
- Frontend: Vue 3 + Vite
- Local DB: SQLite
- Future production DB: PostgreSQL
- ORM/migrations: SQLAlchemy + Alembic, or SQLModel + Alembic
- Document storage: local filesystem first

Done when:

- backend starts locally
- frontend starts locally
- frontend can call backend health endpoint
- repo has clear setup instructions

## 0.1.1 — Core database models

Build models for:

- UserProfile
- ProfileFact
- SavedAnswer
- Job
- JobSourceSnapshot
- Application
- ApplicationPack
- Document
- Contact
- OutreachMessage
- HermesTask
- ApprovalCheckpoint
- StatusEvent

Done when:

- migrations create all core tables
- sample seed data can be inserted
- tests prove the model relationships work

## 0.1.2 — Core API CRUD

Build API endpoints for:

- jobs
- applications
- profile facts
- saved answers
- packs/documents
- Hermes tasks
- status events

Done when:

- API can create/read/update/delete core records
- application status transitions can be recorded
- every meaningful state change can create a StatusEvent

## 0.1.3 — Manual job save

Build:

- create job manually from URL/title/company/description
- create linked Application automatically or by explicit action
- basic notes and next action fields

Done when:

- user can manually save a job through API
- job appears as Saved
- application tracking record exists

## 0.1.4 — Local persistence and file storage

Build:

- local data directory convention
- document artifact paths
- basic pack/document file attachment support
- safe path handling

Done when:

- generated files can be registered as Document records
- app can show paths/metadata without needing cloud storage

## 0.1.5 — Connected starter dashboard

Build:

- dashboard reads real jobs/profiles/Hermes-task data
- backend root endpoint gives a friendly API message instead of raw 404
- home page explains the HaxJobs ↔ Hermes split inside the UI
- recent saved jobs panel

Done when:

- opening the UI shows real backend-backed counts
- visiting `http://localhost:8000/` is human-friendly during dev
- user can tell whether real job-search state exists without touching the API

## 0.1.6 — Manual job save UI and profile workspace basics

Build:

- manual job save form in the UI
- saved jobs list/inbox view in the UI
- basic profile list/view in the UI
- obvious callouts for private local profile import data

Done when:

- user can save a job from the browser UI, not just the API
- saved job appears immediately in the dashboard/inbox
- user can view the stored profile records from the frontend

---

# 0.2.x — Hermes task queue and job-platform foundation

## Theme

Make HaxJobs and Hermes work hand in hand.

This is where HaxJobs stops being just a tracker and becomes Hermes's job-search control panel.

## 0.2.0 — HermesTask queue contract

Build:

- task creation API
- task lifecycle: pending → running → needs_user_input → completed / failed / cancelled
- structured input_payload_json/result_payload_json
- task target references: job, application, contact, profile, pack

Task types:

- analyze_job
- generate_pack
- find_contact / find_contacts
- draft_message / draft_outreach
- apply_assist
- rank_saved_jobs
- refresh_application_status

Done when:

- HaxJobs can create a pending HermesTask
- Hermes can identify pending tasks from stored state
- HaxJobs can display task status/result

## 0.2.1 — Hermes writeback format

Build structured result contracts for:

- analyze_job result
- generate_pack result
- find_contacts result
- draft_outreach result
- apply_assist result

Each result should include:

- status
- summary
- artifacts
- questions
- next_action
- entity updates
- timeline event(s)

Done when:

- Hermes output can update jobs/applications/packs/contacts without manual copy-paste
- failed or blocked tasks produce useful UI-visible errors

## 0.2.2 — Job platform source model

Build source-platform handling for:

- LinkedIn
- Indeed
- Reed
- Workday
- Greenhouse
- Lever
- Ashby
- company site/manual

Important: this phase does not need perfect scraping.

The goal is source classification and storage, not full automation.

Done when:

- jobs/snapshots can store where they came from
- source_platform is normalized
- source URL is stable

## 0.2.3 — Snapshot normalization flow

Build:

- JobSourceSnapshot ingestion API
- snapshot → HermesTask(analyze_job)
- analyze_job result → normalized Job/Application

Done when:

- raw page text can enter HaxJobs
- Hermes can turn it into a normalized job record
- user can review the normalized result

## 0.2.4 — Optional streaming/realtime task updates

Only add this if polling feels bad.

Options:

- simple frontend polling first
- Server-Sent Events for task progress
- WebSockets only if bidirectional live interaction is truly needed

Default decision:

- Start with polling.
- Add SSE before WebSockets.
- Do not build realtime infra before the queue works.

Done when:

- user can see task progress without refreshing manually
- no heavy realtime system exists unless it is clearly needed

---

# 0.3.x — Main dashboard and core UI

## Theme

Make the product usable day-to-day.

This phase turns the backend/state into a real job-search command center.

## 0.3.0 — Basic dashboard

Build:

- saved jobs count
- applications by status
- pending Hermes tasks
- next actions
- recent timeline events

Done when:

- user opens HaxJobs and immediately knows what needs attention

## 0.3.1 — Job inbox

Build:

- saved jobs table/list
- filters by status/source/company/role
- search by title/company/description
- quick actions: analyze, archive, create pack

Done when:

- user can browse saved jobs without using chat/history

## 0.3.2 — Application pipeline

Build:

- statuses from Saved → Applied/Interview/Rejected/Offer
- visual pipeline columns or grouped list
- status update controls
- next_action field surfaced clearly

Done when:

- user can track application progress from HaxJobs

## 0.3.3 — Job detail page

Build:

- job info
- source snapshot
- fit score
- sponsorship risk
- recommendation
- pack files
- contacts/outreach section
- timeline
- next action
- Hermes task actions

Done when:

- one job page tells the full story of that opportunity

## 0.3.4 — Task queue UI

Build:

- pending/running/completed/failed task list
- task detail drawer/page
- result preview
- retry/cancel controls

Done when:

- Hermes work is visible and auditable from HaxJobs

---

# 0.4.x — Profile, survey flow, pack library, and refinement

## Theme

Make HaxJobs the interface Hermes uses to understand the user truthfully.

This phase is the big “profile + reusable application intelligence” phase.

## 0.4.0 — Profile page

Build:

- UserProfile edit page
- profile facts list
- confidence labels: confirmed, inferred, weak, needs_confirmation
- evidence source display
- safe wording / avoid wording fields

Done when:

- user can see and edit the profile facts Hermes will rely on

## 0.4.1 — Guided profile survey

Build HaxJobs questions for:

- identity/contact basics
- work authorization and sponsorship
- preferred roles
- preferred locations/work modes
- salary preference
- availability
- strongest projects
- backend/AI/software skills
- education/certification
- application-answer reuse

Safety:

- sensitive answers should be marked review_before_use, legal_sensitive, or never_auto_answer
- Hermes should ask through HaxJobs instead of burying profile questions in chat

Done when:

- Hermes can create “questions for user”
- HaxJobs displays them clearly
- user answers are stored as ProfileFact or SavedAnswer records

## 0.4.2 — Saved answers page

Build:

- reusable application answers
- sensitivity labels
- last_confirmed_at
- edit/confirm controls

Done when:

- Hermes can reuse confirmed answers and stop on stale/sensitive ones

## 0.4.3 — Pack library

Build:

- ApplicationPack list
- document attachments
- PDF/Markdown/HTML path display
- submitted-version marker
- based_on_pack_id reuse tracking

Done when:

- user can view, download, compare, and reuse previous packs

## 0.4.4 — Pack generation approval flow

Build:

- “Generate pack” action
- HermesTask(generate_pack)
- generated document writeback
- pack review status

Done when:

- user can request a pack from HaxJobs
- Hermes generates it
- HaxJobs displays the result and attached files

## 0.4.5 — UX refinement pass

Refine:

- empty states
- loading states
- error states
- status labels
- timeline readability
- safety copy around sensitive approvals

Done when:

- app feels calm and understandable, not like a hacked-together admin panel

---

# 0.5.x — Chrome extension

## Theme

Let users capture jobs while browsing normally.

The extension should be boring, reliable, and explicit.

## 0.5.0 — Chrome Manifest V3 extension skeleton

Build:

- extension manifest
- popup UI
- content script
- local config for HaxJobs API URL

Done when:

- Chrome loads the extension locally
- popup opens without errors

## 0.5.1 — Save current page snapshot

Capture:

- current URL
- page title
- visible page text
- selected text if any
- source platform guess
- timestamp
- optional user note

Send to:

- HaxJobs JobSourceSnapshot API

Done when:

- user can click “Save to HaxJobs” on a job page
- snapshot appears in HaxJobs

## 0.5.2 — Chrome privacy/safety pass

Build:

- explicit click-only capture
- preview of what will be saved where possible
- no intentional password/form-field capture
- deletion support from HaxJobs side

Done when:

- extension capture is intentional and user-controlled

## 0.5.3 — Chrome source-specific polish

Improve handling for:

- LinkedIn Jobs
- Indeed
- Reed
- Workday
- Greenhouse
- Lever
- Ashby
- company pages

Done when:

- common job platforms produce useful snapshots
- extension still works on unknown pages

---

# 0.6.x — Firefox extension

## Theme

Bring the same capture workflow to Firefox without changing the core product.

## 0.6.0 — Firefox extension port

Build:

- Firefox-compatible manifest/config
- popup UI reuse where possible
- content script reuse where possible

Done when:

- Firefox loads the extension locally
- Save to HaxJobs works

## 0.6.1 — Cross-browser extension packaging

Build:

- shared extension source layout
- browser-specific manifest generation if needed
- build scripts for Chrome and Firefox

Done when:

- both extensions can be built from the repo without copy-paste drift

## 0.6.2 — Cross-browser QA

Test against:

- LinkedIn
- Indeed
- Reed
- Workday
- Greenhouse
- Lever
- Ashby
- generic company page

Done when:

- Chrome and Firefox behave consistently enough for real use

---

# 0.7.x — Assisted apply and outreach

## Theme

Add the risky automation only after tracking, profile, packs, and approvals are solid.

## 0.7.0 — Approval checkpoints

Build:

- ApprovalCheckpoint records
- approval UI
- expiry support for approvals where needed
- timeline events for approval decisions

Actions needing approval:

- submit_application
- send_message
- use_sensitive_answer
- confirm_legal_answer
- upload_final_document if needed

Done when:

- Hermes can check whether an approval exists before high-stakes actions

## 0.7.1 — Apply-assist state UI

Build:

- blockers/questions UI
- fields completed summary
- uploaded files summary
- final review summary
- status updates: Applying, Needs User Input, Applied

Done when:

- Hermes can assist with applications and report exactly where it stopped

## 0.7.2 — Contacts and outreach

Build:

- contact records
- find_contacts task UI
- draft_outreach task UI
- message draft review
- message approval flow

Done when:

- Hermes can find contacts/draft messages
- user can approve or reject drafts before anything is sent

## 0.7.3 — Safe apply/outreach audit trail

Build:

- full event timeline for apply/outreach actions
- “what Hermes did” summaries
- failed/blocker records

Done when:

- every meaningful automation step is explainable after the fact

---

# 0.8.x — Production hardening and polish

## Theme

Make HaxJobs reliable enough to use continuously.

Build:

- auth/user isolation if needed
- deployment config
- Postgres migration path
- better logging
- backups/export
- document cleanup/versioning
- import/export profile data
- performance improvements
- stronger automated tests
- better UI polish

Done when:

- HaxJobs can safely run as the long-term workspace for a real job search

---

# Non-goals before 1.0

Do not build these too early:

- mass auto-apply
- mass recruiter messaging
- raw password storage
- a heavy CRM
- perfect scraping for every platform
- realtime WebSockets before polling/SSE is proven insufficient
- fake-experience or keyword-stuffing systems
- final-submit automation without explicit approval

---

# First build sequence

The practical starting order is:

1. Create backend/frontend skeleton.
2. Create database models and migrations.
3. Add manual job save.
4. Add dashboard/job list/job detail.
5. Add HermesTask queue.
6. Add analyze_job and generate_pack writeback.
7. Add profile survey and saved answers.
8. Add browser extension capture.
9. Add apply/outreach only after approval checkpoints are solid.

That gives us a clean loop:

```text
Save job
→ analyze with Hermes
→ review fit/sponsorship risk
→ generate pack
→ store documents
→ track application
→ ask/answer profile questions through HaxJobs
→ reuse what worked next time
```
