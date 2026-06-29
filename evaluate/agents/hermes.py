"""Hermes CLI agent adapter.

Calls ``hermes chat`` with the evaluation prompt and returns raw output.
The Hermes binary must be on PATH.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERMES_BIN = "hermes"

# Log path for debugging evaluation output
_EVAL_LOG_PATH = Path(__file__).resolve().parents[2] / "state" / "hermes_eval.log"


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    """Call Hermes with the evaluation prompt and return raw output.

    Args:
        prompt: Full evaluation prompt text.
        timeout_seconds: Subprocess timeout.
        retries: Number of retry attempts.

    Returns:
        Raw stdout string, or None if all attempts fail.
    """
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                [HERMES_BIN, "chat", "--yolo", "-Q", "-q", prompt],
                capture_output=True, text=True, timeout=timeout_seconds,
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )
            output = result.stdout.strip()

            # Surface rate-limiting clearly
            if "HTTP 429" in output or "usage limit" in output:
                return None  # ponytail: None triggers retry/fallback in caller

            # Log raw output
            _EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_EVAL_LOG_PATH, "a") as lf:
                lf.write(f"\n--- {datetime.now(timezone.utc).isoformat()} (attempt {attempt+1}) ---\n")
                lf.write(f"EXIT: {result.returncode}\n")
                lf.write(f"STDOUT ({len(output)} chars):\n{output[:2000]}\n")
                if result.stderr:
                    lf.write(f"STDERR:\n{result.stderr[:500]}\n")

            return output

        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue

    return None
