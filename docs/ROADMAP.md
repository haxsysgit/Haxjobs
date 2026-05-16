# HaxJobs Roadmap

This roadmap is intentionally small.

The goal is not to invent many versions.

The goal is to get to a strong, usable product quickly.

## v0.1

Ship the first usable slice.

- Deterministic JD parsing
- CV evidence extraction
- Evidence map with safe wording and warnings
- FastAPI + web UI
- Demo flow and local dev runner
- JSON and Markdown exports

Definition of done:

- A user can run one command, test with fixtures, upload a CV, paste a JD, and get a defensible fit map.

## v0.2

Turn analysis into the first routed application workspace.

- First tailored outputs: `tailored_cv.md`, `cover_letter.md`, `interview_notes.md`, `evidence_map.json`, and `application_pack.json`
- Deterministic output generation that depends on the completed evidence map instead of bypassing it
- Routed web workflow with `vue-router` and a simple three-step Workspace, Review, and Drafts flow
- Card-based analysis and output UX that is readable, interactive, and export-friendly instead of one long text-heavy page
- Copy, download, and regenerate actions inside the outputs workspace
- Demo flow and backend health checks kept inside the routed input experience

Definition of done:

- Final writing traces back to the evidence map, the routed web app is usable without dense scrolling, and output export is part of the core release rather than optional polish.

## v0.3

Shift to an AI-first, staged workflow while preserving evidence-first safety.

- Keep the same `Workspace -> Review -> Drafts` product flow and API routes
- Add AI stage roles: `recruiter_agent`, `applicant_agent`, `evaluator_agent`, `verification_agent`
- Use tiered models (smaller models for extraction/evaluation, stronger model for final aspirational synthesis)
- Add additive AI fields on `/api/analyze`: `analysis_engine`, `recruiter_assessment`, `evaluator_assessment`, `verification_questions`, `aspirational_pack`
- Add `user_claim_confirmations[]` support on `/api/generate-application-pack`
- Generate an aspirational sample track in parallel, clearly labeled non-submittable until confirmed

Definition of done:

- The app produces recruiter/evaluator/verification outputs with explicit claim confirmation paths and a clearly separated aspirational track, without breaking existing deterministic contracts.

## v0.4

Add controlled AI assistance.

- LLM-assisted rewriting behind evidence checks
- JD-to-keyword extraction improvements
- Bullet rewriting with stronger action-impact structure
- Claim-safety review before final export

Definition of done:

- AI improves clarity and relevance without becoming the source of truth.

## v0.5.x

Harden and scale the workflow.

- Multi-application reuse from one base CV
- Saved target-role profiles
- Better scoring and evals
- More fixture coverage
- Polished CLI and web UX

Definition of done:

- HaxJobs feels reliable enough for repeated real-world use, not just one-off demos.

## What Not To Do Yet

- No browser auto-apply
- No large agent swarm
- No database-first redesign
- No complex workflow engine before core writing quality is good

## Short Playbook

1. Make the current evidence map and writing outputs solid.
2. Add role-specific resume behavior before adding more automation.
3. Add LLM help only where deterministic output is clearly weak.
4. Evaluate with real CV/JD fixtures every step of the way.
