"""Minimal agent loop — single-turn. Extended by plan 043 with tools + tiers."""
import os
from openai import OpenAI


class Agent:
    """Thin wrapper over OpenAI-compatible chat API."""

    def __init__(self, model: str | None = None, timeout: int = 60):
        cfg = self._load_config()
        p = cfg["provider"]
        self.client = OpenAI(
            api_key=p["api_key"], base_url=p["base_url"], timeout=timeout
        )
        self.model = model or p["model"]

    @staticmethod
    def _load_config() -> dict:
        """Load provider config from ~/.haxjobs/haxjobs.toml (provider credentials).

        NOT the repo haxjobs.toml (that's product config — roles, paths, cron).

        Primary: imports from haxjobs.features.setup.service (plan 044).
        Failsafe: env vars for headless/CI environments.
        """
        try:
            from haxjobs.features.setup.service import get_config
            cfg = get_config()
            if cfg:
                return cfg
        except ImportError:
            pass
        key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if key:
            base = os.getenv("HAXJOBS_API_BASE", "https://api.deepseek.com")
            model = os.getenv("HAXJOBS_MODEL", "deepseek-chat")
            return {"provider": {"api_key": key, "base_url": base, "model": model}}
        raise RuntimeError(
            "No provider configured. Run haxjobs start and visit /setup or "
            "set DEEPSEEK_API_KEY in your environment."
        )

    def run(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Single-turn: system → user → call → return text.

        Callers who need structured output should use evaluate.common.extract_json()
        on the returned text — it handles fences, box chars, and brace-matching.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
