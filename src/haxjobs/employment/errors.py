"""Typed employment-layer errors shared by durable actions and stores."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IdempotencyConflict:
    """Same tool call ID was reused with a different semantic payload."""

    existing_assessment_id: str = ""
    existing_recommendation: str = ""
    conflict_detail: str = ""
    existing_decision_id: str = ""
    existing_label: str = ""
