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

Turn analysis into application output.

- Tailored CV draft
- Tailored cover letter draft
- Interview notes draft
- Exported application pack
- Better output formatting for ATS-friendly resumes

Definition of done:

- Final writing traces back to the evidence map and does not introduce unsupported claims.

## v0.3

Add role-aware tailoring.

- Resume profile presets for software, product, data, design, customer success, operations
- Academic CV path
- Federal resume path
- Better keyword extraction by role family

Definition of done:

- The system changes emphasis, section order, and wording based on target role type instead of using one generic resume style.

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
