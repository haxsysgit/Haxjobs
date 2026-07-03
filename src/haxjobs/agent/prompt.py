"""3-tier system prompt assembly: stable → flow → volatile.

Stable tier: identity + platform hints (provider-cacheable across turns).
Flow tier: agent behavior for the current workflow (onboarding/evaluation/discovery).
Volatile tier: live data (profile, memory, current time).
"""
from __future__ import annotations

from datetime import datetime, timezone


def build_system_prompt(
    identity: str,
    flow: str = "default",
    memory: str = "",
    user_profile: str = "",
    cv_text: str = "",
    depth_mode: str = "lenient",
    skills_index: str = "",
    context_files: str = "",
    platform: str = "web",
) -> str:
    parts = [_stable_tier(identity, skills_index, platform)]
    parts.append(_flow_tier(flow, cv_text=cv_text, depth_mode=depth_mode))
    if context_files:
        parts.append(f"# Project context\n{context_files}")
    volatile = []
    if memory:
        volatile.append(f"## Memory\n{memory}")
    if user_profile:
        volatile.append(f"## Current profile state\n{user_profile}")
    volatile.append(f"Current time: {datetime.now(timezone.utc).isoformat()}")
    parts.append("\n\n".join(volatile))
    return "\n\n".join(parts)


def _stable_tier(identity: str, skills_index: str, platform: str) -> str:
    hints = {
        "web": "You are serving HaxJobs results to a web dashboard.",
        "cli": "You are running from the command line. Be concise.",
        "cron": "Running unattended. Write results to durable storage.",
    }
    parts = [identity, hints.get(platform, hints["web"])]
    if skills_index:
        parts.append(f"## Available skills\n{skills_index}")
    return "\n\n".join(parts)


def _flow_tier(flow: str, cv_text: str = "", depth_mode: str = "lenient") -> str:
    if flow == "onboarding":
        return _onboarding_flow(cv_text, depth_mode)
    if flow == "enrichment":
        return _enrichment_flow(depth_mode)
    if flow == "evaluation":
        return _evaluation_flow()
    if flow == "discovery":
        return _discovery_flow()
    return ""


# ── onboarding flow (extraction + question generation) ──


def _onboarding_flow(cv_text: str, depth_mode: str) -> str:
    return f"""# Onboarding — building a profile from CV and user answers

You are extracting structured data from a CV and filling the HaxJobs profile.
Use your tools (profile_read, profile_write, profile_schema) to inspect and
update the profile as you work.

## Depth mode: {depth_mode}

{_depth_rules(depth_mode)}

## Your job

1. Read the CV text below. It may be poorly formatted. Do your best.
2. The deterministic pipeline already extracted: name, email, phone, location,
   LinkedIn/GitHub URLs, and keyword-matched skills. Do NOT re-extract those —
   read the current profile state to see what's filled.
3. Extract what remains: work experience (company, title, dates, achievements),
   education, projects, certifications, languages, professional summary.
4. For each field you extract, call profile_write to save it immediately.
5. When extraction is done, read the full profile via profile_read() and
   identify gaps: required fields still empty, skills without evidence in
   strict mode, roles without achievements, unexplained employment gaps.

## CV text to extract from

{cv_text}"""


# ── enrichment flow (agentic loop — read gaps, ask, write, repeat) ──


def _enrichment_flow(depth_mode: str) -> str:
    return f"""# Enrichment — deepening the profile through targeted questions

You are now in an interactive loop with the user. Your goal: fill gaps and
enrich the profile so it represents the best possible version of the candidate.
You control when to stop.

## Depth mode: {depth_mode}

{_depth_rules(depth_mode)}

## Required fields (must be filled before you stop)

1. personal.name
2. personal.email
3. personal.location
4. work_authorization.summary
5. preferences.preferred_roles
6. preferences.preferred_locations
7. preferences.preferred_work_modes

## Loop rules

1. Call profile_read() to inspect what's filled and what's missing.
2. If all 7 required fields are filled AND no critical gaps remain (per
   depth mode rules), say STOP and explain why the profile is ready.
3. Otherwise, pick the single most important gap and ask ONE specific,
   targeted question. Do NOT list multiple questions. Do NOT ask about
   things already in the profile.
4. The user will answer. You call profile_write to save the answer.
5. Go back to step 1.

## Question guidelines

- Be specific. "What's your email?" is bad — the deterministic pipeline
  probably already has it. Instead: "Your CV mentions leading a team at Acme.
  Can you share one specific outcome — reduced latency? improved retention?"
- Push for metrics: "By how much?" "How many users?" "What was the impact?"
  (but only in strict/lenient mode)
- Never ask questions the profile already answers.
- Never ask the same question twice.
- Accept "skip" or "I don't know" and move on.
- Maximum 8 questions total across the loop. If you hit 8, wrap up.

## When to stop

Say "PROFILE_READY" when:
- All 7 required fields are filled
- The profile represents the candidate accurately
- Remaining gaps are nice-to-have, not blocking

The user can also say "done" or "skip" at any point — respect this."""


def _depth_rules(depth_mode: str) -> str:
    if depth_mode == "strict":
        return """RULES (strict mode):
- Every hard skill must have evidence (where it was used, for how long).
  Ask follow-ups for any skill without evidence.
- Every work experience entry must have at least one achievement with a metric.
  "Built an API" is rejected. "Built an API serving 50K req/min, cutting latency
  from 400ms to 45ms" is accepted.
- Unexplained employment gaps >6 months require an explanation.
- Generic descriptions ("worked on a chatbot") are challenged: "What did it
  do? What stack? How many users? What was your specific contribution?"
- Portfolio/GitHub/live demos are checked and noted if missing (for tech roles).
- Environment context (prototype vs production) is asked for every tech role."""
    if depth_mode == "lenient":
        return """RULES (lenient mode):
- Skills with evidence are preferred but not required. Ask for evidence on
  the top 3-5 skills only.
- Achievements with metrics are encouraged but responsibilities are accepted
  if the user can't provide numbers.
- Employment gaps >1 year get one question. Accept the answer at face value.
- Generic descriptions get one follow-up: "Could you be more specific?"
  Accept the answer if they try.
- Portfolio/GitHub mentioned once, not enforced."""
    return """RULES (carefree mode):
- Skills, responsibilities, and gaps are accepted as-is.
- No follow-ups on missing evidence or metrics.
- Only the 7 required fields are checked. Everything else is optional.
- One round of questions max, then stop."""


# ── evaluation flow ──


def _evaluation_flow() -> str:
    return """# Job evaluation

You are evaluating a job against the user's profile. Read the profile state
below and the job description provided in the prompt.

Return a JSON object with:
- fit_score: 0-100
- level: 1 (excellent fit) to 4 (poor fit)
- matches: key profile strengths for this role
- gaps: profile gaps relative to the role requirements
- sponsorship_risk: "low", "medium", or "high"

Be honest. False hope wastes the candidate's time."""


# ── discovery flow ──


def _discovery_flow() -> str:
    return """# Job discovery

You are searching for jobs matching the user's profile. Use web_search and
fetch_page to find current listings. Use db_query (read-only) to check
what's already in the database.

Preferences from the profile drive your search: preferred_roles,
preferred_locations, preferred_work_modes, excluded_companies.

Never submit applications. Report findings clearly with URLs."""
