# Hermes Integration

Hermes is one evaluation agent option for HaxJobs, not the only agent.

## How Hermes is used

The `evaluate/agents/hermes.py` adapter calls `hermes chat` with a structured evaluation prompt. Hermes returns JSON with fit_score, fit_verdict, level, matches, gaps, and summary.

## Agent selection

Configured in `haxjobs.toml`:

```toml
[evaluation]
agent = "hermes"
timeout_seconds = 180
```

## Adding new agents

Each agent lives in `evaluate/agents/<name>.py` and exports:

```python
def call_agent(prompt: str, *, timeout_seconds: int) -> str:
    """Call the agent with an evaluation prompt. Return raw output text."""
    ...
```

The `evaluate/common.py` module handles JSON extraction and schema validation — agent adapters only need to return raw text.

## Hermes prompt format

The evaluation prompt includes:
- Arinze's profile (from profile JSON and haxjobs.toml)
- Behavioral guardrails
- Scoring guidance with levels L1-L4
- Whitelist context from DB
- Required JSON output schema

The prompt explicitly forbids: em dashes, corporate verbs (spearheaded, leveraged, orchestrated), and inflated scores. Arinze is junior/mid, not senior.
