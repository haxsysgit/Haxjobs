# Scripts

Utility scripts for development and debugging.

| Script | Purpose |
|--------|---------|
| `walkthrough_evaluator.py` | Step-by-step evaluator walkthrough — shows prompt building, LLM calls, parsing, and validation end-to-end |
| `dev-app.sh` | Start backend API + frontend dashboard for local development |

## walkthrough_evaluator.py

```bash
python3 scripts/walkthrough_evaluator.py                   # full walkthrough with real evaluation
python3 scripts/walkthrough_evaluator.py --dry-run         # show prompt without calling LLMs
python3 scripts/walkthrough_evaluator.py --quick           # evaluate without explanations
python3 scripts/walkthrough_evaluator.py --job 625         # evaluate specific job
python3 scripts/walkthrough_evaluator.py --adapter hermes  # use a specific adapter
```
