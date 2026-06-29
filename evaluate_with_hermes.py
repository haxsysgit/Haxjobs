#!/usr/bin/env python3
"""Compatibility shim for the old evaluate_with_hermes.py entry point.

Delegates to ``evaluate.run`` which uses the pluggable agent system.
All existing CLI flags (--next, --batch, --all-pending) are preserved.

To use a non-Hermes agent, set ``[evaluation].agent`` in ``haxjobs.toml``.
"""
from evaluate.run import main

# Re-export functions that existing tests import from this module
from evaluate.common import extract_json, validate_result, EXPECTED_SCHEMA, build_prompt, build_profile_blurb  # noqa: F401

if __name__ == "__main__":
    raise SystemExit(main())
