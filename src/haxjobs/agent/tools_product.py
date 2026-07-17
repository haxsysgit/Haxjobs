"""Agent-facing wrappers for implemented HaxJobs product actions."""
from __future__ import annotations

import json
from typing import Any

from haxjobs import product_tools
from haxjobs.agent.registry import register


def discover_jobs(**kwargs: Any) -> str:
    return json.dumps(product_tools.discover_jobs(**kwargs))


def evaluate_fit(**kwargs: Any) -> str:
    return json.dumps(product_tools.evaluate_fit(**kwargs))


def generate_pack(**kwargs: Any) -> str:
    return json.dumps(product_tools.generate_pack(**kwargs))


def record_decision(**kwargs: Any) -> str:
    return json.dumps(product_tools.record_decision(**kwargs))


register(
    "discover_jobs",
    {
        "name": "discover_jobs",
        "description": "Run ATS scrapers, promote new jobs, and optionally evaluate likely matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["greenhouse", "ashby", "lever"]},
                    "description": "Sources to run. Defaults to all available ATS scrapers.",
                },
                "auto_evaluate": {
                    "type": "boolean",
                    "description": "Evaluate likely matches after discovery. Defaults to true.",
                },
            },
            "required": [],
        },
    },
    discover_jobs,
)

register(
    "evaluate_fit",
    {
        "name": "evaluate_fit",
        "description": "Evaluate one stored job against the profile and save the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID from the jobs table."},
                "auto_generate_pack": {
                    "type": "boolean",
                    "description": "Generate a pack for an eligible evaluation. Defaults to true.",
                },
            },
            "required": ["job_id"],
        },
    },
    evaluate_fit,
)

register(
    "generate_pack",
    {
        "name": "generate_pack",
        "description": "Generate application materials for an evaluated job using a reusable CV variant.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID from the jobs table."},
                "force": {
                    "type": "boolean",
                    "description": "Allow pack generation for an otherwise ineligible evaluation.",
                },
            },
            "required": ["job_id"],
        },
    },
    generate_pack,
)

register(
    "record_decision",
    {
        "name": "record_decision",
        "description": "Record an apply, maybe, save, skip, or reject decision for a job.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID from the jobs table."},
                "decision": {
                    "type": "string",
                    "enum": ["apply", "maybe", "save", "skip", "reject"],
                    "description": "User decision.",
                },
                "reason": {"type": "string", "description": "Optional reason for the decision."},
            },
            "required": ["job_id", "decision"],
        },
    },
    record_decision,
)
