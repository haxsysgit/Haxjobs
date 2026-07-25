# HaxJobs

Your personal job-search agent. Runs in the terminal. Remembers your career. Helps you find and evaluate jobs.

Hax is a conversational agent that knows your skills, experience, and constraints. You talk to Hax about jobs, and Hax evaluates them against your profile, records your decisions, and keeps track of everything.

## Install

```bash
pip install haxjobs
# or
uv tool install haxjobs
```

## First run

```bash
# 1. Configure your provider (API key, model)
haxjobs setup

# 2. Create your career profile
#    You'll need a career fixture JSON. Start from the example:
#    https://github.com/haxsysgit/Haxjobs/blob/main/tests/fixtures/job_review/career.json
haxjobs migrate --fixture your-career.json

# 3. Start talking to Hax
haxjobs
```

## What HaxJobs can do

- **Terminal chat** — talk to Hax about jobs, get assessments, record decisions
- **Career graph** — your skills, experience, evidence, constraints, all in one place
- **Job assessments** — Hax evaluates jobs against your profile and tells you why
- **Job decisions** — save your Apply/Maybe/Skip/Reject verdicts
- **Session resume** — pick up conversations where you left off

## Requirements

- Python 3.12 or 3.13
- An OpenAI-compatible API key (DeepSeek, OpenAI, Anthropic via proxy, or custom endpoint)

## Development

```bash
git clone https://github.com/haxsysgit/Haxjobs.git
cd Haxjobs
uv sync --dev

# Dev mode: keeps dev data separate from your real ~/.haxjobs
source scripts/dev.sh

# Fake mode (no network, no API key)
haxjobs chat --new --fake --person-id test-person --track-id test-track

# Run tests
uv run -- python3 -m pytest -q tests/
```

## License

MIT — see [LICENSE](LICENSE)
