# Hermes Integration

## Purpose

Hermes is the agentic worker behind HaxJobs.

HaxJobs should not rely on chat history as the only place where work happens. It should create tasks, store context, and receive structured results from Hermes.

## Integration model for MVP

Use a task queue.

```text
HaxJobs creates HermesTask
→ Hermes reads pending task
→ Hermes performs work
→ Hermes writes result files / JSON / status updates
→ HaxJobs displays result
```

This works even if Hermes is offline when a job is saved.

## Task types

### analyze_job

Input:

- job URL
- raw page text or job description
- user profile summary

Output:

- normalized job profile
- fit score
- sponsorship risk
- recruiter priorities
- recommended action
- questions if needed

### generate_pack

Input:

- job profile
- user profile
- previous similar packs if any
- confirmed answers

Output:

- tailored CV
- cover letter
- application questions/answers
- optional notes
- generated PDF paths

### apply_assist

Input:

- job/application
- pack files
- saved answers
- login/session availability

Output:

- fields completed
- files uploaded
- blockers/questions
- final review summary
- submitted status only if approved and actually submitted

### find_contacts

Input:

- company
- role
- job poster info if available

Output:

- possible recruiters/managers
- relevance notes
- confidence

### draft_outreach

Input:

- contact
- job
- user profile angle
- generated pack summary

Output:

- short natural message draft
- channel recommendation
- risks/notes

## Approval contract

Hermes must stop and request approval before:

- clicking final submit
- sending a message
- confirming legal/work-authorisation declarations not already approved
- using sensitive saved answers with stale confirmation

HaxJobs should store approvals as `ApprovalCheckpoint` records.

## Result shape

Hermes results should be structured enough for the UI.

Example:

```json
{
  "status": "needs_user_input",
  "summary": "Application reached work-authorisation questions.",
  "artifacts": [],
  "questions": [
    {
      "key": "requires_sponsorship",
      "text": "Will you now or in the future require sponsorship?",
      "sensitivity": "legal_sensitive"
    }
  ],
  "next_action": "Ask user to confirm legal answer."
}
```

## Credential policy

Do not store raw passwords in HaxJobs.

Prefer:

- user authenticates manually when needed
- browser/session cookies where safe and explicit
- per-session credentials only
- secure secrets storage only if intentionally designed later

## Audit policy

Every Hermes action that changes application state should create a timeline event.

Examples:

- `job_analyzed`
- `pack_generated`
- `cv_uploaded`
- `needs_user_input`
- `application_submitted`
- `contact_found`
- `message_drafted`
- `message_sent`
