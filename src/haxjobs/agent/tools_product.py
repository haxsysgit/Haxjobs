"""Product tool stubs — defined by contract, implemented in plans 102+."""
from __future__ import annotations

import json as _json
from typing import Any

from haxjobs.agent.registry import register

# ── error helpers ──


def _not_implemented(tool: str) -> dict[str, Any]:
    return {"ok": False, "code": "not_implemented", "error": f"{tool} is defined but not implemented yet"}


def _future_tool(tool: str) -> dict[str, Any]:
    return {"ok": False, "code": "future_tool", "error": f"{tool} is defined for the product contract but not available in v1"}


from haxjobs import product_tools


# ── BUILD tools (plan 102) ──


def discover_jobs(**kwargs: Any) -> str:
    return _json.dumps(product_tools.discover_jobs(**kwargs))


def evaluate_fit(**kwargs: Any) -> str:
    return _json.dumps(product_tools.evaluate_fit(**kwargs))


def generate_pack(**kwargs: Any) -> str:
    return _json.dumps(product_tools.generate_pack(**kwargs))


def record_decision(**kwargs: Any) -> str:
    return _json.dumps(product_tools.record_decision(**kwargs))


# ── FUTURE tools (deferred) ──


def find_contacts(**kwargs: Any) -> str:
    return _json.dumps(_future_tool("find_contacts"))


def draft_message(**kwargs: Any) -> str:
    return _json.dumps(_future_tool("draft_message"))


def analyze_patterns(**kwargs: Any) -> str:
    return _json.dumps(_future_tool("analyze_patterns"))


# ── schema registration ──

register(
    "discover_jobs",
    {
        "name": "discover_jobs",
        "description": "Run ATS scrapers (Greenhouse, Ashby, Lever) and web search to find jobs matching the profile. Promotes new jobs to the jobs table and auto-evaluates likely matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["greenhouse", "ashby", "lever", "web"]},
                    "description": "Scrapers to run. Default: all.",
                },
                "auto_evaluate": {
                    "type": "boolean",
                    "description": "Auto-evaluate likely matches after discovery (default: true).",
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
        "description": "Score a job from the jobs table against the full profile. Returns fit_score 0-100, level L1-L4, matches, gaps, and sponsorship risk. Writes result to evaluations table.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID from the jobs table."},
                "auto_generate_pack": {
                    "type": "boolean",
                    "description": "Auto-generate application pack for L1/L2 after evaluation (default: true).",
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
        "description": "Generate an application pack for an evaluated job. For L1/L2 only (L3/L4 require manual review). Creates fit report, cover letter, field answers, and interview questions. References reusable CV variants — never generates per-job CVs.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID from the jobs table."},
                "force": {
                    "type": "boolean",
                    "description": "Force pack generation even for L3/L4 jobs (default: false).",
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
        "description": "Record a user decision on a job: apply, maybe, save, skip, or reject. Writes to the decisions table and updates job status.",
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

register(
    "find_contacts",
    {
        "name": "find_contacts",
        "description": "Search company pages and LinkedIn for hiring managers and team leads matching a role. Returns contacts with name, title, LinkedIn URL, and confidence score. Requires user approval before use.",
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name to search."},
                "role": {"type": "string", "description": "Role title to match against (e.g. 'Engineering Manager')."},
            },
            "required": ["company", "role"],
        },
    },
    find_contacts,
)

register(
    "draft_message",
    {
        "name": "draft_message",
        "description": "Template-fill a personalized outreach message using profile + job context. Returns subject line and message text. Never sends — requires user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "Contact identifier from find_contacts."},
                "job_id": {"type": "integer", "description": "Job ID the message references."},
                "template": {"type": "string", "description": "Message template name (default: 'default')."},
            },
            "required": ["contact_id", "job_id"],
        },
    },
    draft_message,
)

register(
    "analyze_patterns",
    {
        "name": "analyze_patterns",
        "description": "Process the decisions table for trends. Returns preferred companies, preferred roles, salary trends, and profile tightening suggestions.",
        "parameters": {
            "type": "object",
            "properties": {
                "timeframe": {
                    "type": "string",
                    "description": "Analysis window (e.g. '30d', '90d', 'all'). Default: '30d'.",
                },
            },
            "required": [],
        },
    },
    analyze_patterns,
)
