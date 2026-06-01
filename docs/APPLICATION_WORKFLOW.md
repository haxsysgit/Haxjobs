# Application Workflow

## Goal

HaxJobs should make real job applications faster without becoming unsafe or spammy.

## End-to-end workflow

```text
1. Job enters system
2. Hermes analyzes fit
3. User decides whether to pursue
4. Hermes generates application pack
5. User reviews pack
6. Hermes assists with application where possible
7. Hermes stops on uncertain/sensitive fields
8. User approves final submission
9. HaxJobs records outcome
10. Hermes optionally finds contacts and drafts outreach
11. User approves any message
```

## Application statuses

Use these statuses by default:

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

## Fit and sponsorship review

Every serious job should get:

- fit score
- strongest matching evidence
- major gaps
- sponsorship risk
- recommendation
- next action

Sponsorship risk should be explicit because it heavily affects Arinze's current job search.

## Application pack rules

A pack usually includes:

- tailored CV
- cover letter
- likely application questions/answers
- optional fit/interview notes
- combined PDF if useful

The submitted CV must not include internal notes, fit scores, gap warnings, or claim-safety comments.

## Apply-assist boundaries

Hermes may:

- open the job page
- log in when explicitly approved
- fill known fields
- upload the tailored CV
- answer already-confirmed standard fields
- summarize blockers

Hermes must stop before:

- final submit
- sensitive legal declarations
- demographic/disability disclosures
- salary expectations not already confirmed
- anything uncertain

## Outreach workflow

Contacting people should be selective and human.

Good reasons to find/draft outreach:

- strong fit
- role has a visible poster
- recruiter is clearly responsible
- company/team has a relevant engineering manager
- application could benefit from context

Bad reasons:

- mass messaging everyone at a company
- generic copy-paste outreach
- weak fit where outreach would look desperate

## Outreach statuses

```text
Not Needed
Contact Search Needed
Contact Found
Message Drafted
Message Approved
Message Sent
Replied
No Response
Skipped
```

## Message style

Messages should be:

- short
- natural
- specific to the role/company
- honest about the user's angle
- not over-polished
- not spammy

## Audit trail

Every meaningful action should become a timeline event:

- job saved
- job analyzed
- pack generated
- application started
- user input requested
- application submitted
- contact found
- message drafted
- message sent
