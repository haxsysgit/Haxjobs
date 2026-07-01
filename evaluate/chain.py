"""Fallback chain — reads agent order from config, falls back to auto-discovery.

Config drives everything. No hardcoded preferences.

Usage:
    from evaluate.chain import evaluate_one_job, evaluate_batch
    result = evaluate_one_job(job_dict)
"""

from __future__ import annotations

from haxjobs_config import EVALUATION_AGENT, EVALUATION_FALLBACK_AGENTS
from evaluate.common import build_prompt
from evaluate.agents import AGENT_LIST, auto_discover


def _resolve_order() -> list[str]:
    """Return agent chain order: config first, auto-discovery if config is empty."""
    order: list[str] = []
    if EVALUATION_AGENT:
        order.append(EVALUATION_AGENT)
    order.extend(EVALUATION_FALLBACK_AGENTS)
    if not order:
        order = auto_discover()
    return order


def evaluate_one_job(
    job: dict,
    *,
    agent_order: list[str] | None = None,
    prompt: str | None = None,
) -> dict | None:
    """Evaluate a job. Tries each agent in order, returns first valid result."""
    prompt = prompt or build_prompt(
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("jd_text", ""),
        job.get("source_url", ""),
    )

    order = agent_order or _resolve_order()

    for agent_name in order:
        adapter = AGENT_LIST.get(agent_name)
        if not adapter:
            continue

        result = adapter.evaluate_job(job, prompt=prompt)
        if result:
            return result

    return None


def evaluate_batch(
    jobs: list[dict],
    *,
    agent_order: list[str] | None = None,
) -> list[dict | None]:
    """Evaluate multiple jobs. Returns results in same order."""
    return [evaluate_one_job(job, agent_order=agent_order) for job in jobs]
