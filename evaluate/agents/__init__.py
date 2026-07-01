"""HaxJobs evaluation agent adapters — two-mode architecture.

Each adapter implements BaseAdapter with:
- evaluate_session(prompt) — FREE, uses host agent's session model
- evaluate_headless(prompt) — Cron, subprocess CLI

Agent order is config-driven via haxjobs.toml [evaluation].agent + fallback_agents.
If unconfigured, auto_discover() finds installed agents via PATH probes.
"""

from __future__ import annotations

import shutil

from evaluate.agents.base import BaseAdapter
from evaluate.agents.claude_code import ClaudeCodeAdapter
from evaluate.agents.codex import CodexAdapter
from evaluate.agents.hermes import HermesAdapter
from evaluate.agents.pi import PiAdapter
from evaluate.agents.gemini import GeminiAdapter

# All registered adapters — every adapter that can be configured or discovered
AGENT_LIST: dict[str, BaseAdapter] = {
    "claude_code": ClaudeCodeAdapter(),
    "codex": CodexAdapter(),
    "hermes": HermesAdapter(),
    "pi": PiAdapter(),
    "gemini": GeminiAdapter(),
}


def auto_discover() -> list[str]:
    """Return agent names that are installed and ready for evaluation.

    Used only when haxjobs.toml [evaluation].agent is not set.
    Discovers via PATH probes and adapter capability checks.

    Claude Code is NOT auto-discovered — it requires explicit opt-in via config
    because headless mode is blocked by Anthropic credit gate.
    Gemini is NOT auto-discovered — tier migration required.
    """
    available: list[str] = []

    # Codex: headless via --output-schema
    if shutil.which("codex"):
        available.append("codex")

    # Hermes: headless via -z
    if shutil.which("hermes"):
        available.append("hermes")

    # Pi: session-native always available when running inside Pi;
    # headless via pi --mode json when pi is on PATH
    available.append("pi")

    return available
