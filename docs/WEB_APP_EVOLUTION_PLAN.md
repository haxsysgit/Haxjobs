# HaxJobs Web App Evolution Plan

## Current Priority

Make the main job-to-pack workflow obvious and dependable:

1. Add a job description by paste, readable file, or URL import.
2. Analyze it against the saved candidate profile or uploaded CV.
3. Answer only the checks that improve safety or draft quality.
4. Generate the tailored CV, cover letter, and application notes.
5. Copy or download the application pack.

The interface should stay simple until this path is boringly reliable.

## Version 1: Core Flow Polish

Goal: make the current app feel complete enough for early users.

- Keep the three-step structure: Workspace, Review, Drafts.
- Make JD input flexible: paste, file import, URL import where browser access allows it.
- Make the primary CTA unambiguous: analyze JD with saved CV, then generate pack.
- Keep evidence and safety checks visible but secondary.
- Add small state transitions for loading, selected choices, generated documents, and route changes.
- Preserve local-first profile behavior and existing backend persistence.

Success criteria:

- A user can arrive with a JD and CV/profile and produce a tailored pack without reading instructions.
- Required survey answers and claim confirmations still shape the generation payload.
- Tests cover the core flow and route guards.

## Version 2: AI Onboarding

Goal: make HaxJobs feel like an assistant that builds the user's profile with them.

- Add a first-run onboarding flow for users with no saved profile.
- Let users upload one or more CVs, paste a LinkedIn-style summary, or add notes.
- Show an AI-assisted profile build sequence:
  - parse source material
  - extract evidence
  - identify skills and role positioning
  - ask only high-value clarifying questions
  - save the local profile
- Add gentle progress animation and conversational status text during profile creation.
- Add profile review/edit before the first application run.

Success criteria:

- New users understand what HaxJobs needs before seeing the workspace.
- The initial saved profile is created from real evidence, not invented claims.
- Returning users skip onboarding unless they choose to update the profile.

## Version 3: Living Application Studio

Goal: make the app feel alive, premium, and worth returning to.

- Add animated transitions between Workspace, Review, and Drafts.
- Add a richer document workspace with document preview, diff/refresh moments, and section-level regeneration.
- Add application history with previous JDs, fit summaries, and generated packs.
- Add profile growth prompts after each application:
  - save confirmed answers
  - add newly discovered evidence
  - flag gaps to improve later
- Add a polished empty state and first-run experience with motion, but keep the main screen a tool, not a landing page.

Success criteria:

- The app feels like an AI recruiter/editor workspace rather than a form.
- Motion supports progress, feedback, and confidence instead of decoration.
- Users can reuse HaxJobs across multiple applications without starting over.
