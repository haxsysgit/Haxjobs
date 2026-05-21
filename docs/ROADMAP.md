# HaxJobs Roadmap

This roadmap is intentionally small.

The goal is to make the default path feel immediate: paste a JD, use the saved profile, and get a tailored application pack.

## Product Spine

HaxJobs should optimize for:

1. A reusable candidate profile that improves over time.
2. Fast JD intake.
3. A concise CV-led application pack.
4. Optional sharpening questions only when they improve the draft.
5. Internal claim-safety checks that stay out of the user's way unless a claim is clearly risky.

Evidence maps and fit diagnostics are implementation tools, not the primary user-facing product.

## v0.1

Ship the first usable application-pack slice.

- CV/PDF parsing
- JD parsing
- local profile memory
- tailored CV generation
- cover letter generation
- application notes
- internal match/safety metadata for debugging
- FastAPI + web UI

Definition of done:

- A user can upload or select a CV, paste a JD, and generate a useful tailored pack without needing to understand evidence maps.

## v0.2

Make the routed workspace feel application-first.

- Keep the main route sequence: Workspace -> Fit Check -> Pack.
- Make the workspace default to saved profile + pasted JD.
- Keep review questions compact and optional unless they materially improve the application.
- Make the Pack screen prioritize the tailored CV, then cover letter, then application notes.
- Keep raw match data as internal/debug metadata rather than a default exported document.

Definition of done:

- The web app reads like a practical application assistant, not a fit-analysis dashboard.

## v0.3

Improve profile-first morphing.

- Build generation from the full saved profile, not only one selected CV.
- Let users add broad profile notes in plain language.
- Reuse prior answers across future applications.
- Add role-family behavior for software, AI, data, product, operations, academic, and federal variants.
- Add CV length budgeting: usually two pages, three pages maximum for standard roles.

Definition of done:

- Repeated applications become sharper because the profile grows, while each output still feels job-specific.

## v0.4

Add controlled AI assistance.

- LLM-assisted rewriting for stronger role fit.
- JD-to-keyword extraction improvements.
- Bullet rewriting with stronger action-impact structure.
- Internal claim-safety review before export.
- Conditional extras such as project walkthrough notes only when the JD asks for examples, portfolio material, video, or similar artifacts.

Definition of done:

- AI improves clarity, relevance, and recruiter appeal without becoming a source of fabricated facts.

## v0.5.x

Harden and scale the workflow.

- Multi-application reuse from one base profile.
- Saved target-role profiles.
- Better scoring and evals.
- More fixture coverage.
- Polished CLI and web UX.

Definition of done:

- HaxJobs feels reliable enough for repeated real-world use, not just one-off demos.

## What Not To Do Yet

- No browser auto-apply.
- No login automation.
- No job scraping in core.
- No database-first redesign before the local profile workflow is strong.
- No default Loom/video output.

## Short Playbook

1. Make the tailored pack useful first.
2. Keep the CV concise and skimmable.
3. Treat profile memory as the main product asset.
4. Keep evidence and safety checks internal unless the user needs to act.
5. Evaluate with real CV/JD fixtures every step of the way.
