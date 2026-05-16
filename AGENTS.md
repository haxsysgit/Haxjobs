# AGENTS.md

# HaxJobs

HaxJobs is an installable agent workflow for turning a base CV and job description into a stronger, defensible application pack.

It should feel like a recruiter, CV editor, career coach, and interview-prep assistant working together.

It should not feel like a generic CV generator.

Core principle:

> Evidence before polish. Safety before hype.

---

## Product Goal

HaxJobs helps users:

1. Understand what a job description is really asking for
2. Extract real evidence from their base CV
3. Map job requirements to confirmed, partial, transferable, weak, or missing evidence
4. Ask useful follow-up questions where evidence is unclear
5. Produce a tailored CV, cover letter, evidence map, and interview notes
6. Warn about claims that may be unsupported, exaggerated, or unsafe

The goal is not to invent a better candidate.

The goal is to present the real candidate more clearly.

---

## Inputs

Expected inputs:

1. Base CV
2. Job description
3. Optional user notes or follow-up answers

Local fixtures may live in:

1. `tests/cv/`
2. `tests/jd/`

---

## Outputs

Expected outputs:

1. `outputs/tailored_cv.md`
2. `outputs/cover_letter.md`
3. `outputs/evidence_map.json`
4. `outputs/interview_notes.md`
5. Optional `outputs/application_pack.json`

The evidence map must be created before final writing.

---

## Modes

### `safe`

Use only clearly confirmed evidence from the CV or user answers.

Best for conservative applications.

### `stretch`

Default mode.

Use confirmed evidence, transferable experience, adjacent skills, projects, and user-confirmed answers to create the strongest defensible version.

### `interview`

Pause before drafting and ask targeted questions that would improve the application.

### `ideal`

Create an aspirational example of the kind of candidate the JD appears to want.

This must be clearly labeled as an example and must not be presented as the user's real CV.

---

## Hard Boundary

HaxJobs must not invent:

1. Employers, job titles, dates, or responsibilities
2. Degrees, certifications, visas, clearance, or credentials
3. Tools, platforms, or technologies not supported by evidence
4. Production deployments, client work, leadership, or ownership not supported by evidence
5. Metrics, revenue, users, impact, or savings the user cannot defend

When evidence is missing, use:

1. Follow-up questions
2. Stretch wording
3. Gap notes
4. Risk warnings
5. Clearly labeled aspirational examples

Useful gaps are better than fake matches.

---

## Workflow

Follow this order:

1. Read the job description
2. Extract employer requirements
3. Read the CV
4. Extract confirmed evidence
5. Build the evidence map
6. Ask targeted questions if useful
7. Generate the tailored CV and cover letter
8. Review claims for safety
9. Generate interview notes
10. Export the application pack

The orchestrator manages the flow.

Specialist agents or stages should do focused work.

---

## Internal Roles

Suggested internal roles:

1. `orchestrator`
2. `jd_reader`
3. `recruiter_expectation`
4. `cv_evidence`
5. `requirement_mapper`
6. `experience_interviewer`
7. `tailoring`
8. `claim_safety`
9. `interview_defence`

The orchestrator should not do all the work itself.

It should route work, collect outputs, enforce order, and stop unsafe claims.

---

## Evidence Map

The evidence map is the source of truth.

Each job requirement should include:

1. Requirement text
2. Importance
3. Match label
4. Claim label
5. Supporting CV evidence
6. Suggested safe wording
7. Follow-up question if needed
8. Risk warning if needed

Claim labels:

1. `Confirmed`
2. `Inferred`
3. `Needs User Confirmation`
4. `Stretch Wording`
5. `Unsafe Claim`

Match labels:

1. `Strong Match`
2. `Partial Match`
3. `Transferable Match`
4. `Weak Match`
5. `Gap`
6. `Unsupported Claim`

Final outputs should trace back to the evidence map.

---

## Writing Style

Outputs should be:

1. Natural
2. Specific
3. Recruiter-friendly
4. Easy to skim
5. ATS-readable
6. Defensible in interview

Avoid:

1. Empty corporate filler
2. Generic buzzwords
3. Robotic phrasing
4. Unsupported confidence
5. Claims that sound stronger than the evidence

Prefer clear, evidence-based language.

---

## Build Direction

HaxJobs should stay:

1. Workflow-first
2. Installable
3. Local-friendly
4. Reusable across job applications
5. Small enough to maintain
6. Safety-first around claims

Start with:

1. CLI workflow
2. Structured schemas
3. Evidence map
4. Markdown and JSON outputs
5. Tests using local CV and JD fixtures

Avoid early scope creep:

1. No auto-apply
2. No browser login automation
3. No job scraping in core
4. No database in the first version
5. No web UI until the CLI workflow is stable

---

## Haxaml Managed Workflow

This repository uses Haxaml as the workflow governor.

Follow the managed adapter file at:

1. `.haxaml/setup/targets/generic.md`
2. `.agents/skills/haxaml/SKILL.md`

Lifecycle:

```text
about -> guidance -> prebuild -> context_pack -> build -> verify -> record -> expect_sync