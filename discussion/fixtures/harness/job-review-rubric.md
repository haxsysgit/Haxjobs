# Job review rubric — Stage 0 observed run

## Why this rubric exists

This rubric defines the checks a human reviewer should apply to each Stage 0 job-review output. It is a verification aid, not a pass/fail gate. Model outputs will vary. The rubric tells you what to look for, not which exact words must appear.

## Job 49 — Trainline IT Support Analyst

### Truth checks
- [ ] Hax does not call this a software-engineering or backend role.
- [ ] Hax identifies it as an internal IT-support position.
- [ ] Hax distinguishes the single automation/AI/ML bullet from the role's main work.
- [ ] Hax notes that the stored description was truncated and a full fetch may reveal more.
- [ ] Hax does not invent missing content (salary, sponsorship, work mode, closing date, employer facts).

### Direction checks
- [ ] Hax identifies this as the wrong career direction for a Python backend and AI track.
- [ ] Hax explains which specific evidence points (Windows admin, JAMF, Intune, ticket lifecycle, meeting-room support) conflict with the user's target.
- [ ] Hax does not suggest applying anyway.

## Job 328 — Oritain Software Engineer (title-and-URL stub)

### Truth checks
- [ ] Hax states plainly that the stored vacancy is only a title and LinkedIn URL.
- [ ] Hax does not infer responsibilities, stack, seniority, salary, sponsorship, or employer facts beyond the stored evidence.
- [ ] Hax does not reference the old evaluation score, verdict, or prose.
- [ ] Hax identifies that the employer name is not stored as a machine-verified field.
- [ ] Hax names source inspection as the next useful step before a fit judgement.

### Direction checks
- [ ] Hax does not return a confident fit score or verdict from a stub.
- [ ] Hax explains that without real source content, no honest assessment is possible.
- [ ] Hax suggests what a full source fetch might reveal before a decision.

## Engineering checks (both jobs)
- [ ] The output includes a run ID and artifact path.
- [ ] The output includes a path to the human review markdown file.
- [ ] No credentials, raw API keys, or provider auth headers appear in the output.
- [ ] The events.jsonl file contains redacted events (no raw prompts, career data, or model text in the event payloads).
- [ ] Receipt files are present and non-empty (events.jsonl, manifest.json, context.json, transcript.json, result.json, review.md).
- [ ] The fake run completes without network access.

## Voice checks (both jobs)
- [ ] Hax sounds like a helpful career agent, not a recruiter, automated scorer, or academic reviewer.
- [ ] Hax distinguishes supported facts from user statements, inference, and unknowns.
- [ ] Hax explains why it thinks what it thinks, not just what it thinks.
