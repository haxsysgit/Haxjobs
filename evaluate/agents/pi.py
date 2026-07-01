"""Pi Coding Agent adapter — two-mode evaluation.

Session-native: Pi IS the evaluator — no subprocess needed when running as a Pi skill.
Headless: ``pi -p <prompt> --mode json --no-tools`` with JSONL event stream parsing.

Pi uses its own configured LLM (DeepSeek, OpenAI, etc.). The JSONL event stream
requires extraction of the final assistant text (Plan 028 finding).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evaluate.agents.base import BaseAdapter

PI_BIN = "pi"

# ponytail: model fallback chain — tried in order if primary rate-limits
PI_MODEL = os.environ.get("HAXJOBS_PI_MODEL", "deepseek/deepseek-v4-pro")
PI_FALLBACK_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4.1",
]

_EVAL_LOG_PATH = Path(__file__).resolve().parents[2] / "state" / "pi_eval.log"


class PiAdapter(BaseAdapter):
    name = "pi"

    def can_evaluate_session(self) -> bool:
        """Pi is the evaluator itself — always true when running inside Pi."""
        # ponytail: detect via env var or import check
        return True  # When this code runs, we're inside Pi

    def can_evaluate_headless(self) -> bool:
        return shutil.which(PI_BIN) is not None

    def evaluate_session(self, prompt: str) -> str | None:
        """Session-native: Pi evaluates with its own LLM.

        When running as a Pi skill, the session model evaluates directly.
        No subprocess — the skill's LLM processes the prompt.
        """
        # ponytail: session-native evaluation passes through the BaseAdapter
        # chain but conceptually, Pi IS the evaluator here.
        # For actual implementation: Pi skills can call session.prompt()
        # but that requires SDK integration. For now, delegate to headless.
        return self.evaluate_headless(prompt)

    def evaluate_headless(self, prompt: str) -> str | None:
        """Pi headless via ``pi -p --mode json --no-tools``.

        Parses JSONL event stream to extract the final assistant text.
        Model fallback: tries PI_MODEL first, then PI_FALLBACK_MODELS.
        """
        models = [PI_MODEL] + [m for m in PI_FALLBACK_MODELS if m != PI_MODEL]

        for model in models:
            result = self._run_pi(prompt, model)
            if result is None:
                continue

            output = result.stdout.strip()

            # Rate-limit detection
            if any(sig in output.lower() for sig in ("rate limit", "usage limit", "429", "quota")):
                continue

            if output:
                json_text = self._extract_json_from_jsonl(output)
                if json_text:
                    _log_output(json_text, model)
                    return json_text

                # Fallback: use raw output if JSONL parsing fails
                _log_output(output[:3000], model)
                return output

        return None

    def _run_pi(self, prompt: str, model: str) -> subprocess.CompletedProcess | None:
        """Run pi in headless JSON mode. Returns CompletedProcess or None."""
        try:
            return subprocess.run(
                [PI_BIN, "-p", prompt, "--mode", "json", "--no-tools", "--model", model],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None

    @staticmethod
    def _extract_json_from_jsonl(raw: str) -> str | None:
        """Parse Pi's JSONL event stream for the final evaluation JSON.

        Pi's --mode json returns a stream of JSON events (one per line).
        We extract text from message_end or message_update events, then
        find the last JSON object containing "fit_score".
        """
        texts = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            evt_type = evt.get("type", "")

            if evt_type in ("message_end", "message_update"):
                content = evt.get("message", {}).get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        texts.append(c["text"])
            elif evt_type == "text":
                texts.append(evt.get("text", ""))

        full_text = "".join(texts)

        # Find the last JSON object containing fit_score
        # (Pi may echo the prompt, and there may be duplicate outputs)
        objs = re.findall(r'\{[^{}]*"fit_score"[^{}]*\}', full_text)
        if objs:
            return objs[-1]

        # No fit_score JSON found — return raw text if it looks like JSON
        if full_text.strip().startswith("{"):
            return full_text.strip()

        return None


def _log_output(output: str, model: str) -> None:
    """Write evaluation output to debug log."""
    try:
        _EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_EVAL_LOG_PATH, "a") as lf:
            lf.write(f"\n--- {datetime.now(timezone.utc).isoformat()} model={model} ---\n")
            lf.write(f"STDOUT ({len(output)} chars):\n{output[:3000]}\n")
    except OSError:
        pass


# Backward-compat wrapper — kept until evaluate/run.py is migrated to BaseAdapter
_adapter = PiAdapter()


def call_agent(prompt: str, *, timeout_seconds: int = 300, retries: int = 2) -> str | None:
    """Backward-compat entry point. Delegates to PiAdapter.evaluate_headless()."""
    return _adapter.evaluate_headless(prompt)
