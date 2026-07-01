"""Claude Code adapter — session-native evaluation.

When HaxJobs runs as a Claude Code plugin/hook, evaluation uses the session's
model (e.g. DeepSeek) for free — no API key, no credit check, no subprocess.

Headless mode (``claude -p``) is documented but blocked by Anthropic credit gate
(Plan 028 finding: ``Credit balance is too low`` even with DeepSeek model).
Users who want headless Claude Code must configure their own Anthropic account.

Session-native: the adapter writes the prompt to a temp file and invokes
``claude -p --output-format json --permission-mode bypassPermissions`` within
the session context. When Claude Code's hook system invokes this, it inherits
the session's auth context.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from haxjobs.evaluate.agents.base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    name = "claude_code"

    def can_evaluate_session(self) -> bool:
        """True when running inside a Claude Code session."""
        return bool(os.environ.get("CLAUDE_CODE_SESSION_ID"))

    def can_evaluate_headless(self) -> bool:
        """Claude Code is installed, but headless is blocked by credit gate."""
        # Even though claude binary exists, headless fails with "Credit balance too low"
        # ponytail: re-enable when user has Anthropic credits
        return False

    def evaluate_session(self, prompt: str) -> str | None:
        """Session-native evaluation via Claude Code.

        Writes the prompt to a temp file and invokes claude -p within the session.
        The session inherits the user's configured model (DeepSeek, etc.).
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--output-format", "json",
                    "--permission-mode", "bypassPermissions",
                    f"Read the file at {prompt_file} and evaluate it. Return ONLY valid JSON with no markdown.",
                ],
                capture_output=True, text=True, timeout=180,
                env={**os.environ},
            )

            output = result.stdout.strip()
            if not output:
                return None

            # claude -p returns JSON with a result field when successful
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    # Success response: {"type":"result","subtype":"success","result":"..."}
                    if data.get("subtype") == "success" and "result" in data:
                        return data["result"]
                    # Error response: {"type":"result","is_error":true,"result":"Credit..."}
                    if data.get("is_error"):
                        return None
            except json.JSONDecodeError:
                pass

            return output

        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None
        finally:
            Path(prompt_file).unlink(missing_ok=True)
