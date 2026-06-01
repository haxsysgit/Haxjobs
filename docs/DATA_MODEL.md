# HaxJobs Data Model

This is the target conceptual data model. It can be implemented gradually.

## Entity overview

```text
UserProfile
ProfileFact
SavedAnswer
Job
JobSourceSnapshot
Application
ApplicationPack
Document
Contact
OutreachMessage
HermesTask
ApprovalCheckpoint
StatusEvent
```

## UserProfile

Stores top-level user identity and job-search preferences.

Fields:

```text
id
name
email
phone
location
linkedin_url
github_url
portfolio_url
requires_sponsorship
work_authorization_summary
salary_preference
availability
preferred_locations
preferred_work_modes
preferred_roles
created_at
updated_at
```

## ProfileFact

Stores evidence-backed career truth.

Fields:

```text
id
profile_id
category          # skill, project, education, work, preference, constraint
claim
safe_wording
avoid_wording
evidence_source
confidence        # confirmed, inferred, weak, needs_confirmation
last_confirmed_at
created_at
updated_at
```

## SavedAnswer

Reusable application answers.

Fields:

```text
id
profile_id
question_key
question_text
answer
sensitivity       # normal, review_before_use, legal_sensitive, never_auto_answer
last_confirmed_at
created_at
updated_at
```

Sensitive answers include visa/work authorization, salary numbers, demographic/disability disclosures, criminal/legal declarations, and anything with a certification checkbox.

## Job

Represents an opportunity.

Fields:

```text
id
company
title
location
source_platform   # linkedin, indeed, reed, company_site, workday, greenhouse, lever, ashby, manual, other
source_url
job_description
salary_text
work_mode
seniority
employment_type
sponsorship_signal
status            # saved, analyzing, analyzed, archived
created_at
updated_at
```

## JobSourceSnapshot

Raw saved page data, especially from the browser extension.

Fields:

```text
id
job_id nullable
url
title
source_platform
visible_text
selected_text
html_snapshot_path optional
screenshot_path optional
user_note
captured_at
processed_at
```

The extension should create snapshots first. Hermes can normalize them into Jobs later.

## Application

Represents the user's pursuit of a Job.

Fields:

```text
id
job_id
status
fit_score
sponsorship_risk
recommendation
next_action
applied_at
external_application_id optional
notes
created_at
updated_at
```

Preferred statuses:

```text
Saved
Analyzing
Analyzed
Pack Generated
Ready to Apply
Applying
Needs User Input
Applied
Contact Found
Message Drafted
Message Approved
Message Sent
Interview
Rejected
Offer
Archived
```

## ApplicationPack

Generated materials for a job/application.

Fields:

```text
id
application_id
company
role_title
based_on_pack_id nullable
generation_mode
fit_summary
created_at
updated_at
```

## Document

Files attached to a pack or application.

Fields:

```text
id
application_pack_id
document_type      # tailored_cv, cover_letter, application_questions, combined_pack, fit_report, notes
format             # pdf, md, html, json, docx
path
version
is_submitted_version
created_at
```

## Contact

Potential recruiter/hiring-manager/contact.

Fields:

```text
id
job_id
name
title
company
platform          # linkedin, email, website, other
profile_url
email nullable
relevance_reason
confidence
created_at
updated_at
```

## OutreachMessage

Drafted or sent outreach.

Fields:

```text
id
contact_id
application_id
channel
message_text
status            # drafted, approved, sent, replied, no_response, skipped
approved_at
sent_at
created_at
updated_at
```

## HermesTask

Work request for Hermes.

Fields:

```text
id
task_type
target_type
target_id
status
instructions
input_payload_json
result_payload_json
error
created_at
started_at
completed_at
```

Task types:

```text
analyze_job
generate_pack
apply_assist
find_contacts
draft_outreach
rank_saved_jobs
refresh_application_status
```

## ApprovalCheckpoint

Records user approval before high-stakes actions.

Fields:

```text
id
target_type
target_id
action_type        # submit_application, send_message, use_sensitive_answer
summary
approved_by
approved_at
expires_at optional
```

## StatusEvent

Append-only timeline event.

Fields:

```text
id
entity_type
entity_id
event_type
message
metadata_json
created_at
```

This makes the job-search history auditable without overcomplicating the current status fields.
