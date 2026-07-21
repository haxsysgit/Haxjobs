"""Stable deterministic identifiers — shared by migration, assessment, and decision actions."""

from __future__ import annotations

import hashlib


def make_stable_id(prefix: str, *parts: str) -> str:
    """Produce a stable, repeatable ID from a prefix and ordered parts."""
    joined = "|".join(parts)
    digest = hashlib.sha256(joined.encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"
