# Hermes Direction Brief for HaxJobs

This is the short brief Hermes should read when working on HaxJobs.

## Current direction

HaxJobs is now the UI, state, and workflow layer for a Hermes-powered job-search assistant.

The product should help users:

- monitor applications
- save jobs from browsing
- generate and reuse tailored application packs
- maintain a truthful career profile
- coordinate Hermes automation
- track contacts and outreach
- apply with human-approved automation

## Important pivot

Do not treat HaxJobs as only a CV/JD-to-application-pack generator.

That is now just one capability inside a broader application workspace.

## Hermes's role

Hermes should:

- search jobs
- extract job descriptions
- rank fit
- flag sponsorship risk
- generate packs
- fill applications when approved
- stop on sensitive fields
- find relevant contacts
- draft natural outreach
- write results back to HaxJobs

## HaxJobs's role

HaxJobs should:

- store durable job-search state
- show a beautiful dashboard
- track applications and statuses
- store generated documents
- store reusable profile facts and answers
- expose pending Hermes tasks
- record approvals and audit events

## Safety rules

Never final-submit or message people without explicit user approval.

Never invent user facts.

Never store raw passwords as product data.

Keep legal/work-authorisation answers reviewable and confirmation-based.

## Build mindset

Build the smallest useful product surface first:

1. tracker
2. profile
3. saved jobs inbox
4. pack library
5. Hermes task queue
6. extension
7. apply/outreach assistance

Do not overbuild before the loop works.
