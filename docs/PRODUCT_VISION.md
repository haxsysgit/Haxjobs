# HaxJobs Product Vision

## What HaxJobs is now

HaxJobs is a job-search workspace powered by Hermes.

It gives users a place to monitor applications, save jobs, review generated application packs, manage recruiter outreach, and build a truthful profile that improves over time.

Hermes can already operate across messy workflows: browsing job boards, extracting job descriptions, tailoring documents, helping fill forms, and drafting messages. HaxJobs exists so that work does not disappear into chat history.

## Why this exists

Job searching is not one isolated action. It is a loop:

- find roles
- judge fit
- adapt the CV
- answer application questions
- submit forms
- follow up with the right people
- track responses
- learn what kinds of roles work
- reuse what worked next time

Most tools only handle one slice. HaxJobs should be the place where the whole loop is visible.

## First user outcome

A user should be able to open HaxJobs and immediately answer:

- What jobs have I saved?
- Which ones are worth applying to?
- Which applications are in progress?
- Which packs were generated?
- What do I need to review next?
- Who should I message, if anyone?
- What has Hermes already done?

## Product principles

### 1. Human-approved automation

The system should reduce repetitive effort, not remove user control.

The user must approve final submits and real outreach.

### 2. Truthful profile over fake optimization

HaxJobs should build a genuine evidence-backed profile, not a keyword-stuffed persona.

### 3. Reuse without laziness

Prior packs, answers, and messages should be reusable, but every new role still needs a fresh fit check.

### 4. Job search memory beats one-off chat

Every job, pack, answer, status update, and contact should become durable state.

### 5. Beautiful but simple UI

The UI should feel like a clear command center, not enterprise ATS software.

## What HaxJobs is not

HaxJobs is not:

- a spam bot
- a mass auto-apply tool
- a fake-experience generator
- a generic resume builder
- a replacement for Hermes
- a heavy CRM
- a platform that submits sensitive declarations without review

## Product shape

The main areas are:

1. Dashboard
2. Job Inbox
3. Application Pipeline
4. Job Detail
5. Application Pack Library
6. User Profile
7. Saved Answers
8. Outreach
9. Hermes Task Queue
10. Browser Extension

## Default workflow

```text
Job enters HaxJobs
→ status: Saved
→ Hermes analyzes fit
→ status: Analyzed
→ user approves pack generation
→ Hermes generates pack
→ status: Pack Generated
→ user approves application attempt
→ Hermes assists application
→ status: Applied or Needs User Input
→ Hermes optionally finds contact
→ user reviews message
→ outreach status updates
```

## Core success metric

HaxJobs succeeds if repeated applications become faster, clearer, and more truthful because the workspace remembers what has already been learned.
