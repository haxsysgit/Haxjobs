# AGENTS.md

# HaxJobs

HaxJobs is an installable agent workflow for turning a base CV or saved candidate profile plus a job description into a stronger, tailored application pack.

It should feel like a recruiter, CV editor, career coach, and interview-prep assistant working together.

It should not feel like a generic CV generator.

Core principle:

> Best truthful impression first. Safety before hype.

Product interpretation:

> Evidence and safety checks are internal guardrails, not the main user-facing product.

---

## Product Goal

HaxJobs helps users:

1. Paste a job description and reuse a saved candidate profile
2. Understand what the role is really asking for
3. Morph the candidate profile toward the role without inventing core facts
4. Ask useful follow-up questions only when they improve the application
5. Produce a concise tailored CV, cover letter, and application notes
6. Keep claim safety and evidence checks behind the scenes unless the user needs to act

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
3. `outputs/application_notes.md`
4. `outputs/application_pack.json`

Internal match data may be created before final writing, but it should not be treated as a primary user-facing artifact.

---

## Modes

### `safe`

Use only clearly confirmed evidence from the CV, saved profile, or user answers.

Best for conservative applications.

### `stretch`

Default mode.

Use confirmed evidence, transferable experience, adjacent skills, projects, plausible inference, and user-confirmed answers to create the strongest defensible version.

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
3. Transferable positioning
4. Internal risk warnings
5. Clearly labeled aspirational examples

Useful profile shaping is better than fake matches, and internal gaps should not clutter the user's CV unless they matter.

---

## Workflow

Follow this order:

1. Read the job description
2. Extract employer requirements
3. Read the saved profile and selected CV
4. Infer the strongest truthful positioning for the role
5. Ask targeted questions only if useful
6. Generate the tailored CV and cover letter
7. Review claims internally for safety
8. Generate application notes or interview prep only where useful
9. Export the application pack

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

## Internal Match Layer

The match layer is internal scaffolding for safer generation.

When generated, each job requirement may include:

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

Final outputs should benefit from this layer, but users should not need to inspect it to get value.

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

For standard private-sector CVs, target two pages and never exceed three pages unless the role explicitly asks for an academic CV, federal resume, or long-form dossier.

Do not generate Loom/video/project-walkthrough material by default. Prepare it only when the JD asks for video, examples of systems built, portfolio material, or a walkthrough-style artifact.

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
3. Profile-first application pack generation
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

<!-- HAXAML:MANAGED START {"generator":"haxaml-setup","kind":"pointer","recipe_hash":"770bda2c454fa4fc6dfe801863a0652c115f732f420299acb100aec6c783e6d1","scope":"project","target":"codex","version":"0.7.5"} -->
## Haxaml Managed Workflow

This repository uses Haxaml as the workflow governor. Keep your existing native instructions, but follow the managed adapter file at `.haxaml/setup/targets/codex.md` and the governed skill at `.agents/skills/haxaml/SKILL.md`.

Lifecycle: about -> guidance -> prebuild -> context_pack -> build -> verify -> record -> expect_sync

Fallback when tooling is unavailable:
- Read the local instructions and the relevant source files before editing.
- Classify the task, note risks, and state assumptions publicly.
- Make the smallest safe change that satisfies the request.
- Verify with commands, tests, or direct inspection and report evidence.
- Record what changed and any remaining risks before claiming completion.
<!-- HAXAML:MANAGED END -->
