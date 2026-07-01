"""Pi Coding Agent adapter — headless cron evaluator.

Uses ``pi -p <prompt> -nt`` for non-interactive one-shot evaluation.
Pi must be installed at ``~/.local/bin/pi``.

Unlike the hermes adapter, Pi evaluates using its OWN configured LLM
(DeepSeek, OpenAI, etc.) — no subprocess spawning a different agent.
The ``-nt`` flag disables tools so Pi returns a pure text response.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PI_BIN = os.path.expanduser("~/.local/bin/pi")

# Default model — can be overridden via env var
PI_MODEL = os.environ.get("HAXJOBS_PI_MODEL", "deepseek/deepseek-v4-pro")

# ponytail: fallback models if primary is rate-limited. Ordered by preference.
PI_FALLBACK_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4.1",
]

_EVAL_LOG_PATH = Path(__file__).resolve().parents[2] / "state" / "pi_eval.log"


def _pi_call(prompt: str, model: str, timeout_seconds: int) -> subprocess.CompletedProcess | None:
    """Run pi in headless mode. Returns CompletedProcess or None on timeout."""
    try:
        return subprocess.run(
            [PI_BIN, "-p", prompt, "-nt", "--model", model],
            capture_output=True, text=True, timeout=timeout_seconds,
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        return None
    except Exception:
        return None


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    """Send evaluation prompt to Pi in headless mode.

    Tries configured model first, then fallbacks. Returns raw text output.
    Returns None if all models fail (rate-limited, timeout, or not found).
    """
    models = [PI_MODEL] + [m for m in PI_FALLBACK_MODELS if m != PI_MODEL]

    for model in models:
        for attempt in range(retries + 1):
            result = _pi_call(prompt, model, timeout_seconds)

            if result is None:
                continue  # Timeout — retry

            output = result.stdout.strip()

            # Rate-limit detection — try next model
            if any(sig in output.lower() for sig in ("rate limit", "usage limit", "429", "quota")):
                break  # Don't retry this model, try next

            # Successful response
            if output:
                _log_output(output, model, attempt, result.returncode)
                return output

            # Empty stdout but no error — retry
            if attempt < retries:
                continue

        # All retries exhausted for this model, try next

    return None


def _log_output(output: str, model: str, attempt: int, returncode: int) -> None:
    """Write evaluation output to debug log."""
    try:
        _EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_EVAL_LOG_PATH, "a") as lf:
            lf.write(f"\n--- {datetime.now(timezone.utc).isoformat()} model={model} attempt={attempt+1} ---\n")
            lf.write(f"EXIT: {returncode}\n")
            lf.write(f"STDOUT ({len(output)} chars):\n{output[:3000]}\n")
    except OSError:
        pass  # ponytail: log failure is non-fatal
