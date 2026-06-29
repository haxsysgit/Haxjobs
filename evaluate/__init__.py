"""Pluggable evaluation system for HaxJobs.

The evaluator scores job fit using a configured agent (hermes by default).
Agent adapters live in ``evaluate.agents.*`` and implement a tiny interface:
``call_agent(prompt: str, *, timeout_seconds: int) -> str``.

Agent selection is controlled by ``haxjobs.toml`` ``[evaluation].agent``.
"""
from .common import (
    EXPECTED_SCHEMA,
    extract_json,
    validate_result,
    build_profile_blurb,
    build_prompt,
)

__all__ = [
    "EXPECTED_SCHEMA",
    "extract_json",
    "validate_result",
    "build_profile_blurb",
    "build_prompt",
]
