"""Hermes adapter — two-mode evaluation.

Session-native: import ``agent.oneshot.run_oneshot`` when running inside Hermes.
Headless: ``hermes -z`` subprocess for cron (validated in Plan 028).

Also supports native Python import (``agent.oneshot.run_oneshot``) when the
``openai`` module dependency is resolvable (blocked locally in Plan 028:
``ModuleNotFoundError: No module named openai``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from haxjobs.evaluate.agents.base import BaseAdapter

HERMES_BIN = "hermes"
_EVAL_LOG_PATH = Path(__file__).resolve().parents[2] / "state" / "hermes_eval.log"


class HermesAdapter(BaseAdapter):
    name = "hermes"

    def can_evaluate_session(self) -> bool:
        """True when running inside a Hermes process."""
        return bool(os.environ.get("HERMES_SESSION_ID"))

    def can_evaluate_headless(self) -> bool:
        return shutil.which(HERMES_BIN) is not None

    def evaluate_session(self, prompt: str) -> str | None:
        """Try native Python API first, fall back to headless CLI."""
        # Attempt native import
        try:
            hermes_src = str(Path.home() / ".hermes" / "hermes-agent")
            if hermes_src not in sys.path:
                sys.path.insert(0, hermes_src)
            from agent.oneshot import run_oneshot
            result = run_oneshot(
                instructions="You are a job fit evaluator. Respond with ONLY valid JSON.",
                user_input=prompt,
                max_tokens=4096,
                temperature=0.3,
                timeout=180.0,
            )
            return result.strip() if result else None
        except ImportError:
            pass
        except Exception:
            pass

        # Fall back to headless CLI
        return self.evaluate_headless(prompt)

    def evaluate_headless(self, prompt: str) -> str | None:
        """Hermes headless via ``hermes -z``. Validated in Plan 028."""
        try:
            result = subprocess.run(
                [HERMES_BIN, "-z", prompt],
                capture_output=True, text=True, timeout=180,
                env={**os.environ, "HERMES_YOLO_MODE": "1"},
            )

            output = result.stdout.strip()

            # Rate-limit detection
            if any(sig in output.lower() for sig in ("rate limit", "usage limit", "429", "quota")):
                return None

            if output:
                _log_output(output, result.returncode)
                return output

            return None

        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None


def _log_output(output: str, returncode: int) -> None:
    """Write evaluation output to debug log."""
    try:
        _EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_EVAL_LOG_PATH, "a") as lf:
            lf.write(f"\n--- {datetime.now(timezone.utc).isoformat()} ---\n")
            lf.write(f"EXIT: {returncode}\n")
            lf.write(f"STDOUT ({len(output)} chars):\n{output[:2000]}\n")
    except OSError:
        pass


# Backward-compat wrapper — kept until evaluate/run.py is migrated to BaseAdapter
# ponytail: thin compat layer, remove after run.py uses chain.py
_adapter = HermesAdapter()


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    """Backward-compat entry point. Delegates to HermesAdapter.evaluate_headless()."""
    return _adapter.evaluate_headless(prompt)
