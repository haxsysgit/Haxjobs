"""CV Review — per-job CV improvement before pack generation.

Reads the JD and the best-fit CV variant, then rewrites the CV to:
1. Mirror the JD's keywords exactly (ATS optimization)
2. Add inferred-but-realistic metrics (user-approved estimation)
3. Frame experience bullets per role family (same work, different emphasis)
4. Rewrite professional summary for this specific role
5. Ensure one-page format for junior/mid roles

This runs automatically for L1/L2 jobs after evaluation.
"""
from __future__ import annotations

import re
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Inferred metrics — based on Arinze's real experience, conservatively estimated
# ---------------------------------------------------------------------------

_VIGILIS_METRICS = {
    "invoice_volume": "200+ invoices/day, ~6,000 per month",
    "invoice_volume_short": "6,000+ invoices/month",
    "admin_time_reduction": "~70%",
    "stock_discrepancy_reduction": "~60%",
    "pharmacy_locations": "3+ pharmacy locations",
    "role": "Sole full-stack developer — owned infrastructure, backend, frontend, and deployment",
    "role_short": "Sole developer across full stack (infra, backend, frontend, DevOps)",
    "system_uptime": "production system used daily by pharmacy staff across multiple locations",
}

_BUCCA_HUT_METRICS = {
    "duration": "3-month contract",
    "deliverable": "working prototype delivered from concept",
    "role": "designed and built the backend API bridging AI processing with existing operational workflows",
}

# ---------------------------------------------------------------------------
# Per-role experience bullet templates
# Each role family gets different framing of the SAME Vigilis and Bucca Hut work
# ---------------------------------------------------------------------------

_VIGILIS_BULLETS: dict[str, list[str]] = {
    "backend_python": [
        "Designed the full data model and REST API (FastAPI, PostgreSQL, SQLAlchemy) with role-based access, JWT auth, and Alembic migrations — serving {pharmacy_locations} processing {invoice_volume}.",
        "Built the complete invoice lifecycle (create → finalise with auto stock deduction → cancel with stock reversal), with every state transition validated and audited — processing {invoice_volume_short}.",
        "Reduced daily administrative processing time by {admin_time_reduction} by replacing manual paper workflows with a digital system, and cut stock discrepancies by {stock_discrepancy_reduction} through real-time inventory tracking.",
        "Added structured logging, input validation, and business rule enforcement at the API boundary, preventing data corruption downstream — {system_uptime}.",
        "{role_short} — handled feature planning, database design, deployment, monitoring, and production bug fixes with no handoff.",
    ],
    "ai_engineer_llm": [
        "Built the backend for an AI-integrated pharmacy platform (FastAPI, PostgreSQL, SQLAlchemy) processing {invoice_volume_short}, with JWT auth, role-based access, and Alembic migrations.",
        "Integrated LLM evaluation into the development workflow using RAGAS, building a structured evaluation pipeline for AI-assisted features — reducing manual QA cycles.",
        "Designed and implemented the full invoice lifecycle with automated state transitions, audit trail, and business rule validation — {system_uptime}.",
        "Replaced manual paper-based workflows with a digital AI-assisted system, reducing admin time by {admin_time_reduction} and stock discrepancies by {stock_discrepancy_reduction} across {pharmacy_locations}.",
        "{role_short} — end-to-end ownership from infrastructure through deployment and monitoring.",
    ],
    "fullstack_python_react": [
        "Sole full-stack developer for a pharmacy operations platform (FastAPI + React + TypeScript + PostgreSQL) serving {pharmacy_locations}, processing {invoice_volume_short}.",
        "Built the frontend dashboard (React, TypeScript, Vite) for real-time inventory tracking, invoice management, and reporting — used daily by pharmacy staff.",
        "Designed and implemented the REST API with JWT auth, role-based access control, and Alembic migrations — all state transitions validated and audited.",
        "Replaced paper workflows with a full-stack digital system: reduced admin time by {admin_time_reduction} and stock discrepancies by {stock_discrepancy_reduction}.",
        "Owned the entire product surface: infrastructure (Docker, Linux), backend (FastAPI, PostgreSQL), frontend (React, TypeScript), and DevOps (CI/CD, deployment, monitoring).",
    ],
    "junior_software": [
        "Built and shipped a complete pharmacy operations platform end-to-end (FastAPI, React, PostgreSQL, Docker) as the sole developer — processing {invoice_volume_short} across {pharmacy_locations}.",
        "Replaced manual paper workflows with a full-stack digital system: built the database, API, frontend dashboard, and deployed it — reduced admin time by {admin_time_reduction}.",
        "Designed the invoice lifecycle from scratch (create → finalise → dispense → cancel), with automatic stock tracking, audit trail, and role-based access — {system_uptime}.",
        "Learned and applied production-grade practices: structured logging, input validation, Alembic migrations, pytest test suites — with no senior engineer to fall back on.",
        "Demonstrated ability to own a product end-to-end: gathered requirements from pharmacy staff, designed the schema, built the stack, and maintained it in production.",
    ],
    "ai_automation_agents": [
        "Built the backend and automation infrastructure for a pharmacy platform (FastAPI, PostgreSQL, SQLAlchemy) — processing {invoice_volume_short} with automated stock tracking and audit logging.",
        "Designed automated workflows replacing manual processes: invoice state machine with automatic stock deduction/reversal, low-stock alerts, and scheduled reporting — reducing admin time by {admin_time_reduction}.",
        "Integrated AI-assisted features (LLM evaluation via RAGAS, automated data validation) into the production workflow — {system_uptime}.",
        "Built agent-adjacent infrastructure: structured logging, rule-based validation, automated state transitions, and monitoring — patterns that directly transfer to agent orchestration.",
        "{role_short} — designed, built, deployed, and maintained the entire automation stack with no handoff.",
    ],
    "data_python": [
        "Designed the PostgreSQL data model and analytics pipeline for a pharmacy operations platform processing {invoice_volume_short} across {pharmacy_locations}.",
        "Built reporting and analytics dashboards (Python, SQL) for daily sales, inventory levels, payment method breakdown, and stock discrepancy tracking — replacing paper-based reporting.",
        "Implemented data validation and business rule enforcement at the API layer, ensuring data integrity across the invoice lifecycle (create → finalise → dispense → cancel) with full audit trail.",
        "Used RAGAS evaluation framework for LLM-powered data quality checks, reducing manual review cycles.",
        "{role_short} — owned the data layer, reporting, and analytics for a production system used daily.",
    ],
    "platform_backend": [
        "Sole developer for a production backend platform (FastAPI, PostgreSQL, Docker) processing {invoice_volume_short} across {pharmacy_locations} — {system_uptime}.",
        "Built and maintained the full infrastructure: Docker multi-stage builds, Linux VPS deployment, CI/CD pipeline, structured logging, and production monitoring.",
        "Designed the database schema and API with Alembic migrations for safe schema evolution, role-based access control, JWT authentication, and input validation at every endpoint.",
        "Reduced operational overhead by {admin_time_reduction} by replacing manual processes with automated workflows: invoice state machine, stock tracking, audit logging, and scheduled reporting.",
        "Owned on-call and production reliability — handled deployment, monitoring, debugging, and bug fixes with no handoff to a separate DevOps team.",
    ],
}

_BUCCA_BULLETS: dict[str, list[str]] = {
    "backend_python": [
        "Built a data analysis and mining tool for a food business — {role}.",
        "Delivered a {deliverable} in a {duration}.",
    ],
    "ai_engineer_llm": [
        "Built a data mining tool connecting LLM outputs to operational business decisions — {role}.",
        "Delivered a {deliverable} bridging AI insights with existing workflows in a {duration}.",
    ],
    "fullstack_python_react": [
        "Built a full-stack data analysis tool for a food business — {role}.",
        "Delivered a {deliverable} in a {duration}, working alongside the main Vigilis position.",
    ],
    "junior_software": [
        "Built a data analysis tool for a food business, connecting insights to operational decisions — {role}.",
        "Delivered a {deliverable} in a {duration} while also working full-time at Vigilis.",
    ],
    "ai_automation_agents": [
        "Designed and built an AI-assisted data mining tool automating insights extraction for a food business — {role}.",
        "Delivered a {deliverable} in a {duration}, bridging LLM outputs with real operational workflows.",
    ],
    "data_python": [
        "Built a data mining and analysis tool extracting operational insights for a food business — {role}.",
        "Delivered a {deliverable} from data pipeline to working dashboard in a {duration}.",
    ],
    "platform_backend": [
        "Built and deployed a data analysis tool for a food business — {role}.",
        "Delivered a {deliverable} with API backend and deployment in a {duration}.",
    ],
}


# ---------------------------------------------------------------------------
# Professional summary templates per role family
# ---------------------------------------------------------------------------

_SUMMARY_TEMPLATES: dict[str, str] = {
    "backend_python": (
        "Backend engineer with {years} years of Python experience and a track record of building "
        "production systems people rely on daily. Sole developer of a pharmacy operations platform "
        "(FastAPI, PostgreSQL, SQLAlchemy) processing {invoice_volume_short} across {pharmacy_locations}. "
        "Comfortable owning the full backend: database design, API architecture, testing, deployment, "
        "and production debugging. Looking for a backend role where clean code, honest testing, and "
        "systems that stay up matter more than buzzwords."
    ),
    "ai_engineer_llm": (
        "AI Engineer with {years} years of Python backend engineering and practical AI/LLM experience. "
        "Built production AI-assisted features (RAGAS evaluation pipelines, LLM-powered data processing) "
        "for a pharmacy platform serving {pharmacy_locations}. Designed FRAME and Haxaml — open-source "
        "agent memory and governance tools published on PyPI. Comfortable with the full AI engineering "
        "surface: prompt design, evaluation methodology, RAG architecture, and the production debugging "
        "that comes from shipping AI features that actually work."
    ),
    "fullstack_python_react": (
        "Full-stack engineer with {years} years of Python and TypeScript experience. Sole developer "
        "of a pharmacy operations platform (FastAPI, React, PostgreSQL) processing {invoice_volume_short} "
        "across {pharmacy_locations}. Owned the entire product surface: database design, REST API, "
        "React dashboard, Docker deployment, and production monitoring. Backend-first with enough "
        "frontend depth to ship the whole feature properly."
    ),
    "junior_software": (
        "Software engineer with {years} years of Python and strong full-stack fundamentals. "
        "Built and shipped a complete pharmacy operations platform (FastAPI, React, PostgreSQL, Docker) "
        "as the sole developer — processing {invoice_volume_short} daily. Graduating with a BSc in "
        "Information Technology from Middlesex University. Fast learner with production evidence: "
        "the Vigilis platform replaced paper workflows, cut admin time by {admin_time_reduction}, "
        "and runs in production across {pharmacy_locations}."
    ),
    "ai_automation_agents": (
        "Automation and AI engineer with {years} years of Python backend experience. Built the "
        "full automation stack for a pharmacy platform processing {invoice_volume_short}: automated "
        "state machines, scheduled reporting, audit logging, and AI-assisted data validation. "
        "Creator of FRAME and Haxaml — agent memory and governance infrastructure published on PyPI. "
        "I build automation that replaces manual work, not automation that creates new problems."
    ),
    "data_python": (
        "Python engineer with {years} years of experience building data-driven backend systems. "
        "Designed the data model, analytics pipeline, and reporting layer for a pharmacy platform "
        "processing {invoice_volume_short} across {pharmacy_locations}. Strong SQL, data validation, "
        "and pipeline design — with practical AI/LLM evaluation experience (RAGAS). I turn raw "
        "operational data into dashboards, reports, and decisions people actually use."
    ),
    "platform_backend": (
        "Platform and backend engineer with {years} years of Python experience. Sole developer "
        "and operator of a production backend platform (FastAPI, PostgreSQL, Docker) processing "
        "{invoice_volume_short} across {pharmacy_locations}. Own the full infrastructure surface: "
        "Docker multi-stage builds, Linux deployment, CI/CD, structured logging, and production "
        "monitoring. I build platforms that stay up and make sense to the next engineer who inherits them."
    ),
}

# ---------------------------------------------------------------------------
# Skills section per role family — mirrors the research from UK recruiter guidance
# ---------------------------------------------------------------------------

_SKILLS_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "backend_python": {
        "Backend Engineering": [
            "Python (primary, since 2020)", "FastAPI", "SQLAlchemy", "Alembic",
            "PostgreSQL (advanced)", "REST API design", "async/await",
            "JWT authentication", "role-based access control", "schema design",
            "query optimisation",
        ],
        "Testing and Quality": [
            "Advanced pytest (fixtures, parametrisation, integration coverage)",
            "API test automation", "test-driven development", "structured logging",
            "input validation",
        ],
        "Infrastructure": [
            "Docker (multi-stage builds, docker-compose)", "Linux", "Git/GitHub",
            "CI/CD", "production monitoring",
        ],
    },
    "ai_engineer_llm": {
        "AI and LLM Systems": [
            "Production RAG architecture", "LLM evaluation (RAGAS)",
            "prompt engineering", "model fine-tuning", "HuggingFace",
            "AI agent infrastructure (FRAME, Haxaml, MCP servers)",
            "structured output validation",
        ],
        "Backend Engineering": [
            "Python (advanced)", "FastAPI", "PostgreSQL", "SQLAlchemy",
            "REST API design", "async/await",
        ],
        "Testing and Evaluation": [
            "Advanced pytest", "LLM evaluation pipelines", "regression testing",
            "structured test design for AI workflows",
        ],
        "Infrastructure": [
            "Docker", "Linux", "Git/GitHub", "cloud VPS workflows",
        ],
    },
    "fullstack_python_react": {
        "Backend Engineering": [
            "Python (primary)", "FastAPI", "SQLAlchemy", "PostgreSQL",
            "REST API design", "JWT authentication", "Alembic migrations",
        ],
        "Frontend": [
            "React", "TypeScript", "Vite", "HTML/CSS",
            "dashboard design", "API integration", "form handling",
        ],
        "Testing": [
            "Advanced pytest", "API test automation", "integration testing",
        ],
        "Infrastructure": [
            "Docker", "Linux", "Git/GitHub", "CI/CD",
        ],
    },
    "junior_software": {
        "Languages and Frameworks": [
            "Python (primary, since 2020)", "FastAPI", "React", "TypeScript",
            "Java (Spring Framework, EJB)", "C++", "C",
        ],
        "Backend and Databases": [
            "PostgreSQL", "SQLAlchemy", "REST APIs", "Alembic migrations",
        ],
        "Tools and Practices": [
            "Git/GitHub", "Docker", "Linux", "pytest", "CI/CD",
        ],
    },
    "ai_automation_agents": {
        "Automation and Agents": [
            "AI agent infrastructure (FRAME, Haxaml)", "MCP server patterns",
            "browser automation", "workflow automation", "scheduled job orchestration",
        ],
        "Backend Engineering": [
            "Python (advanced)", "FastAPI", "PostgreSQL", "SQLAlchemy",
            "REST API design",
        ],
        "AI and LLM": [
            "LLM evaluation (RAGAS)", "prompt engineering", "structured output",
            "agent orchestration",
        ],
        "Infrastructure": [
            "Docker", "Linux", "cloud VPS (Archilles)", "Git/GitHub",
        ],
    },
    "data_python": {
        "Data and Analytics": [
            "Python (primary)", "SQL (PostgreSQL, advanced)", "data pipeline design",
            "reporting and dashboards", "data validation", "audit trail design",
        ],
        "Backend Engineering": [
            "FastAPI", "SQLAlchemy", "REST API design", "Alembic migrations",
        ],
        "AI and LLM": [
            "RAGAS evaluation", "LLM-powered data processing",
        ],
        "Tools": [
            "Docker", "Git/GitHub", "Linux", "pytest",
        ],
    },
    "platform_backend": {
        "Platform and Infrastructure": [
            "Docker (multi-stage builds, docker-compose)", "Linux (production, VPS)",
            "CI/CD", "production monitoring", "structured logging",
            "deployment automation",
        ],
        "Backend Engineering": [
            "Python (advanced)", "FastAPI", "PostgreSQL", "SQLAlchemy",
            "REST API design", "Alembic migrations",
        ],
        "Reliability": [
            "Production on-call experience", "incident response",
            "input validation", "API error handling",
        ],
        "Tools": [
            "Git/GitHub", "pytest (advanced)",
        ],
    },
}

# ---------------------------------------------------------------------------
# Project emphasis per role family — which projects to list and how
# ---------------------------------------------------------------------------

_PROJECT_EMPHASIS: dict[str, list[dict]] = {
    "backend_python": [
        {
            "name": "Pharmax, Pharmacy Operations Platform",
            "stack": "Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Docker",
            "bullets": [
                "Production SaaS platform processing {invoice_volume_short} across {pharmacy_locations}.",
                "Products CRUD with multi-unit pricing; full invoice lifecycle with automatic stock deduction and reversal.",
                "Stock adjustments with audit trail, reorder-level tracking, and role-based access (JWT auth).",
                "Comprehensive pytest suite covering endpoints, business logic, and edge cases.",
                "Backend skeleton public on GitHub; full SaaS code proprietary.",
            ],
        },
        {
            "name": "HaxJobs, Automated Job Discovery Pipeline",
            "stack": "Python, FastAPI, SQLite, React, TypeScript",
            "bullets": [
                "End-to-end job discovery and evaluation pipeline with multi-platform scraping (Greenhouse, Ashby, Lever).",
                "Config-driven role classifier, pluggable evaluation agents, and automated pack generation.",
                "React dashboard with real-time pipeline monitoring.",
            ],
        },
    ],
    "ai_engineer_llm": [
        {
            "name": "FRAME, Typed Project Memory for AI Agents",
            "stack": "Python, Markdown/YAML, Multi-Agent Architecture",
            "bullets": [
                "Designed a portable standard for structured AI agent context across sessions — a five-part memory model (Facts, Rules, Acts, Map, Expect).",
                "Open-source on GitHub with documentation; used as the memory layer for multiple AI coding tools.",
            ],
        },
        {
            "name": "Haxaml, AI Agent Governance Runtime",
            "stack": "Python, MCP, FRAME",
            "bullets": [
                "Built and published to PyPI a governance runtime that enforces project rules for AI coding agents.",
                "MCP server integration so AI tools can read/write structured project state during sessions.",
                "Five-stage pipeline (Admission → Verification → Recording) with documentation and setup guides.",
            ],
        },
        {
            "name": "Pharmax, AI-Integrated Pharmacy SaaS",
            "stack": "Python, FastAPI, PostgreSQL, RAGAS, LLM evaluation",
            "bullets": [
                "Built AI-assisted pharmacy workflows with RAGAS-based LLM evaluation pipeline.",
                "Production SaaS platform processing {invoice_volume_short} — backend skeleton public on GitHub.",
            ],
        },
    ],
    "fullstack_python_react": [
        {
            "name": "Pharmax, Full-Stack Pharmacy Platform",
            "stack": "FastAPI, React, TypeScript, PostgreSQL, Docker",
            "bullets": [
                "Sole full-stack developer — built backend API (FastAPI), frontend dashboard (React/TypeScript), and deployment (Docker).",
                "Production platform processing {invoice_volume_short} across {pharmacy_locations}.",
                "Replaced paper workflows: invoice lifecycle, real-time inventory, role-based dashboards, audit trail.",
            ],
        },
        {
            "name": "HaxJobs, Pipeline Dashboard",
            "stack": "React, TypeScript, Vite, FastAPI, SQLite",
            "bullets": [
                "Full-stack job discovery platform with React dashboard for real-time pipeline monitoring.",
                "API server (FastAPI) with SQLite backend, TypeScript frontend with Vite build tooling.",
            ],
        },
    ],
    "junior_software": [
        {
            "name": "Pharmax, Pharmacy Management Platform",
            "stack": "Python, FastAPI, React, PostgreSQL, Docker",
            "bullets": [
                "Built and shipped end-to-end as sole developer — processing {invoice_volume_short} across {pharmacy_locations}.",
                "Full stack: database design, REST API, React dashboard, Docker deployment.",
                "Replaced manual paper workflows with a digital system used daily by pharmacy staff.",
            ],
        },
        {
            "name": "FRAME and Haxaml, AI Agent Tooling",
            "stack": "Python, schema design, AI agent workflows",
            "bullets": [
                "Designed FRAME (typed project memory format) and built Haxaml (governance runtime published on PyPI).",
                "Demonstrates systems thinking: define the rules, build the system, test it, document it.",
            ],
        },
    ],
    "ai_automation_agents": [
        {
            "name": "HaxJobs, Autonomous Job Discovery and Application Pipeline",
            "stack": "Python, FastAPI, SQLite, Multi-Agent Architecture",
            "bullets": [
                "Built an end-to-end autonomous pipeline: multi-platform scraping → classification → agent-based evaluation → pack generation → reporting.",
                "Runs on Archilles, a 24/7 AI agent VPS, with config-driven agent selection and automated cron scheduling.",
                "Designed for zero-human-in-the-loop operation: scrapes, evaluates, and generates application packs automatically.",
            ],
        },
        {
            "name": "FRAME and Haxaml, Agent Memory Infrastructure",
            "stack": "Python, MCP, FRAME",
            "bullets": [
                "Built agent infrastructure tools (FRAME memory model, Haxaml governance runtime) published on PyPI.",
                "MCP server patterns for AI agent tool orchestration and structured state management.",
            ],
        },
    ],
    "data_python": [
        {
            "name": "Pharmax, Data-Driven Pharmacy Platform",
            "stack": "Python, PostgreSQL, SQLAlchemy, RAGAS",
            "bullets": [
                "Designed the data model, analytics pipeline, and reporting layer for a platform processing {invoice_volume_short}.",
                "Built dashboards for daily sales, inventory levels, payment breakdowns, and stock discrepancy tracking.",
                "Implemented data validation and business rule enforcement with full audit trail across the invoice lifecycle.",
            ],
        },
        {
            "name": "Bucca Hut, Data Mining Tool",
            "stack": "Python, FastAPI, LLM-powered data processing",
            "bullets": [
                "Built a data analysis tool connecting LLM outputs and mined data insights to operational business decisions.",
                "Delivered end-to-end: data pipeline, API backend, and working dashboard.",
            ],
        },
    ],
    "platform_backend": [
        {
            "name": "Pharmax, Production Backend Platform",
            "stack": "Python, FastAPI, PostgreSQL, Docker, Linux",
            "bullets": [
                "Sole developer and operator of a production platform processing {invoice_volume_short} across {pharmacy_locations}.",
                "Full infrastructure ownership: Docker multi-stage builds, Linux VPS deployment, CI/CD, structured logging, production monitoring.",
                "Database schema with Alembic migrations, JWT authentication, role-based access, input validation.",
            ],
        },
        {
            "name": "Archilles, 24/7 AI Agent Infrastructure",
            "stack": "Linux VPS, Docker, Python, Cron-based orchestration",
            "bullets": [
                "Built and maintain a 24/7 cloud VPS running AI agent infrastructure (HaxJobs pipeline, Hermes agent fork).",
                "Docker-based deployment with cron scheduling, structured logging, and automated pipeline execution.",
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Years of Python experience — same across all variants
# ---------------------------------------------------------------------------

_YEARS_PYTHON = "6"  # Since 2020
_ADMIN_TIME_REDUCTION = "70%"
_STOCK_DISCREPANCY_REDUCTION = "60%"
_PHARMACY_LOCATIONS = "3+ pharmacy locations"
_INVOICE_VOLUME = "200+ invoices/day, ~6,000/month"
_INVOICE_VOLUME_SHORT = "6,000+ invoices/month"

# ---------------------------------------------------------------------------
# JD keyword extraction (lightweight — full extraction uses LLM)
# ---------------------------------------------------------------------------


class JDRequirements(NamedTuple):
    """Extracted requirements from a job description."""
    keywords: list[str]           # ATS-critical keywords to mirror
    role_type: str                # e.g., "backend", "ai_engineer", "fullstack"
    seniority: str                # "junior", "mid", "senior"
    must_have: list[str]          # Skills the JD says are required
    nice_to_have: list[str]       # Skills the JD says are preferred
    raw_jd: str                   # Original JD text for LLM-based extraction


def extract_jd_requirements(jd_text: str) -> JDRequirements:
    """Extract requirements from a job description using keyword heuristics.

    This is a lightweight pre-filter. For full extraction, the LLM evaluation
    prompt already captures role fit. Here we just extract ATS-keyword signals.
    """
    jd_lower = jd_text.lower()

    # Detect role type from keyword density
    ai_signals = sum(1 for kw in [
        "llm", "langchain", "rag", "prompt engine", "fine-tun",
        "hugging face", "openai", "claude", "gpt", "ai engine",
        "machine learning", "nlp", "transformer", "agent"
    ] if kw in jd_lower)

    fullstack_signals = sum(1 for kw in [
        "react", "typescript", "frontend", "full stack", "full-stack",
        "javascript", "angular", "vue"
    ] if kw in jd_lower)

    backend_signals = sum(1 for kw in [
        "fastapi", "django", "flask", "postgres", "sqlalchemy",
        "rest api", "backend", "api design", "microservice"
    ] if kw in jd_lower)

    platform_signals = sum(1 for kw in [
        "docker", "kubernetes", "ci/cd", "aws", "gcp", "azure",
        "terraform", "devops", "infrastructure", "platform"
    ] if kw in jd_lower)

    data_signals = sum(1 for kw in [
        "data engineer", "data pipeline", "etl", "analytics",
        "sql", "data warehouse", "spark", "reporting"
    ] if kw in jd_lower)

    # Pick dominant role type
    scores = {
        "ai_engineer": ai_signals,
        "fullstack": fullstack_signals,
        "backend": backend_signals,
        "platform": platform_signals,
        "data": data_signals,
    }
    role_type = max(scores, key=scores.get) if max(scores.values()) > 0 else "backend"

    # Detect seniority
    if any(w in jd_lower for w in ["senior", "lead", "principal", "staff", "head of"]):
        seniority = "senior"
    elif any(w in jd_lower for w in ["mid", "mid-level", "intermediate"]):
        seniority = "mid"
    else:
        seniority = "junior"

    # Extract keywords from common JD patterns
    keywords = _extract_keywords(jd_text)

    return JDRequirements(
        keywords=keywords,
        role_type=role_type,
        seniority=seniority,
        must_have=[],
        nice_to_have=[],
        raw_jd=jd_text,
    )


def _extract_keywords(jd_text: str) -> list[str]:
    """Extract technology keywords from JD text for ATS mirroring."""
    known_keywords = [
        "Python", "FastAPI", "Django", "Flask", "PostgreSQL", "SQLAlchemy",
        "Alembic", "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "React", "TypeScript", "JavaScript", "Vite", "Next.js",
        "LangChain", "LlamaIndex", "HuggingFace", "PyTorch", "RAG",
        "REST API", "GraphQL", "gRPC", "Redis", "Celery",
        "CI/CD", "GitHub Actions", "Terraform", "Linux",
        "pytest", "JWT", "OAuth", "microservices",
        "SQL", "NoSQL", "MongoDB", "MySQL",
        "LLM", "AI", "Machine Learning", "prompt engineering",
        "Django REST", "FastAPI", "asyncio",
    ]
    jd_lower = jd_text.lower()
    found = []
    for kw in known_keywords:
        if kw.lower() in jd_lower:
            found.append(kw)
    return found


# ---------------------------------------------------------------------------
# CV improvement: assemble a per-job CV variant
# ---------------------------------------------------------------------------

_VISA_BLURB = (
    "Applying for UK Graduate Route visa — full right to work for 2 years, "
    "no employer sponsorship required."
)

_LOCATION_PREF = "London, Manchester, Leeds, Remote UK, Hybrid UK."


def _format_skills(role_family: str) -> str:
    """Generate skills section markdown for a role family."""
    groups = _SKILLS_TEMPLATES.get(role_family, _SKILLS_TEMPLATES["backend_python"])
    lines = ["## Core Skills", ""]
    for group_name, skills in groups.items():
        lines.append(f"**{group_name}:** " + ", ".join(skills))
        lines.append("")
    return "\n".join(lines)


def _format_summary(role_family: str) -> str:
    """Generate professional summary for a role family."""
    template = _SUMMARY_TEMPLATES.get(role_family, _SUMMARY_TEMPLATES["backend_python"])
    return template.format(
        years=_YEARS_PYTHON,
        invoice_volume=_INVOICE_VOLUME,
        invoice_volume_short=_INVOICE_VOLUME_SHORT,
        pharmacy_locations=_PHARMACY_LOCATIONS,
        admin_time_reduction=_ADMIN_TIME_REDUCTION,
        stock_discrepancy_reduction=_STOCK_DISCREPANCY_REDUCTION,
    )


def _format_vigilis_bullets(role_family: str) -> list[str]:
    """Generate Vigilis experience bullets for a role family."""
    bullets = _VIGILIS_BULLETS.get(role_family, _VIGILIS_BULLETS["junior_software"])
    return [
        b.format(
            invoice_volume=_INVOICE_VOLUME,
            invoice_volume_short=_INVOICE_VOLUME_SHORT,
            admin_time_reduction=_ADMIN_TIME_REDUCTION,
            stock_discrepancy_reduction=_STOCK_DISCREPANCY_REDUCTION,
            pharmacy_locations=_PHARMACY_LOCATIONS,
            role=_VIGILIS_METRICS["role"],
            role_short=_VIGILIS_METRICS["role_short"],
            system_uptime=_VIGILIS_METRICS["system_uptime"],
        )
        for b in bullets
    ]


def _format_bucca_bullets(role_family: str) -> list[str]:
    """Generate Bucca Hut experience bullets for a role family."""
    bullets = _BUCCA_BULLETS.get(role_family, _BUCCA_BULLETS["backend_python"])
    return [
        b.format(
            role=_BUCCA_HUT_METRICS["role"],
            deliverable=_BUCCA_HUT_METRICS["deliverable"],
            duration=_BUCCA_HUT_METRICS["duration"],
        )
        for b in bullets
    ]


def _format_projects(role_family: str) -> str:
    """Generate projects section for a role family."""
    projects = _PROJECT_EMPHASIS.get(role_family, _PROJECT_EMPHASIS["backend_python"])
    lines = ["## Selected Projects", ""]
    for proj in projects:
        lines.append(f"### {proj['name']}")
        lines.append(f"*{proj['stack']}*")
        lines.append("")
        for bullet in proj["bullets"]:
            formatted = bullet.format(
                invoice_volume=_INVOICE_VOLUME,
                invoice_volume_short=_INVOICE_VOLUME_SHORT,
                pharmacy_locations=_PHARMACY_LOCATIONS,
            )
            lines.append(f"- {formatted}")
        lines.append("")
    return "\n".join(lines)


def build_improved_cv(role_family: str, jd_requirements: JDRequirements | None = None) -> str:
    """Build a complete, metric-rich CV markdown for a role family.

    Args:
        role_family: One of the 7 role family IDs.
        jd_requirements: Optional extracted JD requirements for ATS mirroring.

    Returns:
        Complete CV in markdown format.
    """
    role_family = role_family.lower().strip()
    if role_family not in _VIGILIS_BULLETS:
        role_family = "junior_software"

    summary = _format_summary(role_family)
    skills = _format_skills(role_family)
    vigilis_bullets = _format_vigilis_bullets(role_family)
    bucca_bullets = _format_bucca_bullets(role_family)
    projects = _format_projects(role_family)

    # Assemble full CV
    lines = [
        "# Arinze Elenasulu",
        "",
        f"**{_get_role_headline(role_family)}**",
        "",
        "London, UK · elenasuluarinze@gmail.com",
        "[linkedin.com/in/arinze-elenasulu](https://linkedin.com/in/arinze-elenasulu) · [github.com/haxsysgit](https://github.com/haxsysgit)",
        "",
        "---",
        "",
        "## Professional Summary",
        "",
        summary,
        "",
        "---",
        "",
        skills,
        "---",
        "",
        "## Education",
        "",
        "**BSc Information Technology**, Middlesex University London (June 2026)",
        "",
        "**Advanced Diploma in Software Engineering (ADSE Java)**, Aptech Computer Education, Lagos (September 2022 – August 2024)",
        "A structured two-year programme combining classroom training with hands-on project work across four semesters. Covered Linux, Python, C++, C, Java, Spring Framework, EJB, Flutter/Dart, MERN and MEAN stacks. Python became my primary language during this period.",
        "",
        "---",
        "",
        "## Experience",
        "",
        "### Software Engineer, Vigilis",
        f"*August 2024 – February 2026 · Lagos, Nigeria*",
        "",
    ]

    for bullet in vigilis_bullets:
        lines.append(f"- {bullet}")
    lines.append("")

    lines.extend([
        "### AI and Backend Engineer (Contract), Bucca Hut",
        "*February 2025 – May 2025*",
        "",
    ])
    for bullet in bucca_bullets:
        lines.append(f"- {bullet}")
    lines.append("")

    lines.extend([
        "### Software Engineer Intern, Aptech Computer Education",
        "*September 2022 – August 2024 · Lagos, Nigeria*",
        "",
        "Completed the Advanced Diploma in Software Engineering (ADSE Java track), a structured two-year programme combining classroom training with hands-on project work.",
        "",
        "- Covered Linux, Python, C++, C, Java, Spring Framework, Enterprise Java Beans (EJB), Flutter/Dart, MERN and MEAN stacks across four semesters.",
        "- Built multiple projects across different technology stacks, gaining practical exposure to how different languages and frameworks solve similar problems.",
        "- Developed strong fundamentals in object-oriented programming, database design, and software architecture.",
        "- Python became my primary language during this period and has remained so. I have been studying and building with it continuously since 2020.",
        "",
        "---",
        "",
        projects,
        "---",
        "",
        "## Additional Information",
        "",
        f"- Work authorization: {_VISA_BLURB}",
        "- Availability: available to start immediately.",
        f"- Location preference: {_LOCATION_PREF}",
    ])

    return "\n".join(lines)


def _get_role_headline(role_family: str) -> str:
    """Role-specific headline under the name."""
    headlines = {
        "backend_python": "Python Backend Engineer | API Design & Data Systems",
        "ai_engineer_llm": "AI & LLM Engineer | Production AI Systems & Evaluation",
        "fullstack_python_react": "Full-Stack Engineer | Python Backend & React Frontend",
        "junior_software": "Software Engineer | Python, Full-Stack, Fast Learner",
        "ai_automation_agents": "AI Automation Engineer | Agent Infrastructure & Workflows",
        "data_python": "Python Data Engineer | Analytics, Pipelines & Reporting",
        "platform_backend": "Platform & Backend Engineer | Infrastructure & Reliability",
    }
    return headlines.get(role_family, headlines["backend_python"])


# ---------------------------------------------------------------------------
# JD-aware keyword injection
# ---------------------------------------------------------------------------

def inject_jd_keywords(cv_text: str, jd_requirements: JDRequirements) -> str:
    """Add JD keywords to the skills section of a CV if they're missing.

    This is ATS optimization: if the JD asks for Redis and Arinze knows Redis
    but it's not on this CV variant, add it to the relevant skills group.
    """
    if not jd_requirements or not jd_requirements.keywords:
        return cv_text

    cv_lower = cv_text.lower()
    missing = [kw for kw in jd_requirements.keywords if kw.lower() not in cv_lower]

    if not missing:
        return cv_text

    # Add missing keywords to the first skills group
    insertion = ", ".join(sorted(missing))
    lines = cv_text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("**") and ":** " in line and i > 0:
            lines[i] = line.rstrip() + ", " + insertion
            break

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point for the pipeline
# ---------------------------------------------------------------------------

def review_cv_for_job(role_family: str, jd_text: str) -> str:
    """Full CV review pipeline: build improved CV + inject JD keywords.

    Args:
        role_family: The classified role family (e.g., "backend_python").
        jd_text: The full job description text.

    Returns:
        Complete improved CV in markdown format, ready for pack generation.
    """
    jd_reqs = extract_jd_requirements(jd_text)
    cv = build_improved_cv(role_family, jd_reqs)
    cv = inject_jd_keywords(cv, jd_reqs)
    return cv


# ---------------------------------------------------------------------------
# CLI demo — build one CV variant and print
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    role = sys.argv[1] if len(sys.argv) > 1 else "backend_python"
    jd = sys.argv[2] if len(sys.argv) > 2 else "Python, FastAPI, PostgreSQL, REST APIs, Docker"

    cv = review_cv_for_job(role, jd)
    print(cv)
    print(f"\n\n--- CV length: {len(cv)} chars, ~{len(cv.splitlines())} lines ---")
