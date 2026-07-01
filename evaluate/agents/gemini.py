"""Gemini CLI adapter — deferred until tier migration resolved.

Blocked by ``IneligibleTierError`` (Plan 028): free tier deprecated,
requires migration to Antigravity suite at https://antigravity.google.

When resolved, the invocation is:
    gemini -p <prompt> -o json -y

This stub adapter reports as unavailable. No evaluation happens through it.
"""

from __future__ import annotations

import shutil

from evaluate.agents.base import BaseAdapter


class GeminiAdapter(BaseAdapter):
    name = "gemini"

    def can_evaluate_headless(self) -> bool:
        # Gemini binary exists but can't authenticate
        # ponytail: re-enable when tier migration is complete
        # return shutil.which("gemini") is not None
        return False

    def evaluate_headless(self, prompt: str) -> str | None:
        """Blocked — Gemini CLI free tier deprecated."""
        return None
