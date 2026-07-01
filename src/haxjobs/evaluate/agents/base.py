"""Base class for evaluation agent adapters.

Every adapter inherits from this and implements at least one of:
- evaluate_session(prompt) -> str | None  — free, uses host agent's session model
- evaluate_headless(prompt) -> str | None — subprocess CLI, for cron
"""

from __future__ import annotations

from haxjobs.evaluate.common import build_prompt, extract_json, validate_result


class BaseAdapter:
    """Abstract base for evaluation agent adapters.

    Subclasses override evaluate_session() and/or evaluate_headless().
    evaluate_job() is the main entry point — tries session-native first,
    falls back to headless.
    """

    name: str = "base"

    def can_evaluate_session(self) -> bool:
        """Can this adapter use the host agent's session model? (default: no)"""
        return False

    def can_evaluate_headless(self) -> bool:
        """Can this adapter spawn a headless subprocess? (default: no)"""
        return False

    def evaluate_session(self, prompt: str) -> str | None:
        """Evaluate using the host agent's session model. Override in subclass."""
        raise NotImplementedError(f"{self.name}: evaluate_session not implemented")

    def evaluate_headless(self, prompt: str) -> str | None:
        """Evaluate via headless subprocess. Override in subclass."""
        raise NotImplementedError(f"{self.name}: evaluate_headless not implemented")

    def evaluate_job(self, job: dict, *, prompt: str | None = None) -> dict | None:
        """Evaluate a job dict. Prefers session-native, falls back to headless.

        Returns a validated evaluation dict or None on failure.
        """
        prompt = prompt or build_prompt(
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("jd_text", ""),
            job.get("source_url", ""),
        )

        raw = None
        if self.can_evaluate_session():
            raw = self.evaluate_session(prompt)
        if raw is None and self.can_evaluate_headless():
            raw = self.evaluate_headless(prompt)

        if not raw:
            return None

        result = extract_json(raw)
        if result:
            # Normalize: fill in optional fields validate_result expects
            result.setdefault("skip_reason", "")
            result.setdefault("decision", "completed")
            result.setdefault("sponsorship_risk", "unknown")

            issues = validate_result(result)
            if not issues:
                result["evaluated_by"] = self.name
                return result
        return None
