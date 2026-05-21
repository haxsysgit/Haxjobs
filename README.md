# HaxJobs

HaxJobs turns a base CV or saved candidate profile plus a job description into a tailored application pack.

The main user flow is simple:

1. Add one or more CVs to build a local profile.
2. Paste a job description.
3. Generate a role-specific pack led by a concise tailored CV.

Evidence matching and claim safety are internal guardrails. They should improve the output, not become the product the user has to manage.

## Current Scope

`v0.1.0` is the first usable slice.

The product supports:

- CV/PDF text extraction
- job description parsing
- saved local profile memory
- tailored CV generation
- cover letter generation
- application notes for interview or follow-up preparation
- internal match and claim-safety metadata for debugging and future improvements

The standard CV target is two pages for most private-sector roles, with three pages as the hard maximum unless the role explicitly asks for an academic CV, federal resume, or long-form dossier.

Video/Loom/project walkthrough material is not a default output. HaxJobs should prepare it only when the job description asks for a video, examples of systems built, a portfolio, or a walkthrough-style application artifact.

## Local Development

Backend and frontend together:

```bash
./scripts/dev.sh start
./scripts/dev.sh status
```

Backend only:

```bash
uv run fastapi dev main.py --host 127.0.0.1 --port 8000
```

Frontend only:

```bash
cd web
npm run dev -- --host 127.0.0.1 --port 5173
```

## CLI

Generate an application pack from local files:

```bash
uv run haxjobs analyze --cv tests/cv/Arinze_Agent_engineer_cv.pdf --jd-text "$(cat tests/jd/60x.txt)"
```

Outputs currently land in:

- `outputs/tailored_cv.md`
- `outputs/cover_letter.md`
- `outputs/application_notes.md`
- `outputs/application_pack.json`
- `outputs/analysis.json`
- `outputs/analysis.md`

## Requirements

- Python 3.12+
- Node.js for the web app
- `pdftotext` installed on the system for PDF CV extraction

## Verification

```bash
uv run pytest
cd web && npm test -- --run
```
