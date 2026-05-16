# HaxJobs

HaxJobs is an evidence-first workflow for turning a base CV and job description into a safer, more defensible application package.

## Current Scope

`v0.1.0` is the first usable slice.

Right now the product is a deterministic analysis preview:

- upload or parse a CV
- paste a JD
- extract requirements
- map evidence
- flag gaps and unsafe claims
- return JSON and Markdown analysis outputs

The full tailored CV, cover letter, and interview-pack workflow is planned next.

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

Run an analysis from local fixtures or your own files:

```bash
uv run haxjobs analyze --cv tests/cv/Arinze_Agent_engineer_cv.pdf --jd-text "$(cat tests/jd/60x.txt)"
```

Outputs currently land in:

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
