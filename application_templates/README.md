# Application Templates

This folder contains reusable application template contracts for HaxJobs.

The important idea is simple: CVs stay reusable, cover letters and pack notes become dynamic.

- `registry.json` maps each role family to its CV brief, cover letter template, and pack template.
- `cv_variant_briefs/` explains how each reusable CV variant should be positioned.
- `cover_letters/` contains dynamic templates with Arinze's actual voice.
- `pack_templates/` defines what each per-job pack should contain.

Guardrails:
- No per-job CV generation by default.
- `pack_owns_cv: false` stays true for every CV variant brief.
- Cover letters can have personality and swagger, but they cannot invent facts.
- Every application still needs manual review before submit.
