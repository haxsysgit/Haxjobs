"""Onboarding service — deterministic extraction → agent enrichment → wizard.

Phase 1: Deterministic — regex + keyword extraction from CV text
Phase 2: Agent — fills structured sections (experience, education, projects)
Phase 3: Agent generates personalized deep-dive questions
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from haxjobs.agent import Agent, get_prompt
from haxjobs.config import STATE_DIR
from haxjobs.evaluate.common import extract_json

PROFILE_PATH = STATE_DIR / "profile.json"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "profile" / "profile_schema.json"

# In-memory session state
_pending_profile: dict | None = None
_answered_questions: list[str] = []
_phase: str = "deterministic"
_agent_questions: list[dict] = []


# ── file extraction ──


def extract_text_from_upload(content: bytes, filename: str) -> str:
    try:
        return content.decode("utf-8").strip()
    except UnicodeDecodeError:
        pass
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(content)
    if ext in (".docx", ".doc"):
        return _extract_docx(content)
    raise ValueError(f"Cannot read {filename}. Upload PDF, DOCX, or paste text.")


def _extract_pdf(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(content)
        tmp_path = tf.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "not found" in stderr.lower() or "No such file" in stderr:
                raise ValueError(
                    "pdftotext not found. Install it:\n"
                    "  Linux: sudo apt install poppler-utils\n"
                    "  macOS: brew install poppler\n"
                    "  Windows: install poppler from "
                    "https://github.com/oschwartz10612/poppler-windows/releases\n"
                    "Or paste your CV as plain text instead."
                )
            raise ValueError(f"pdftotext failed: {stderr}")
        text = result.stdout.strip()
        if not text:
            raise ValueError("PDF appears empty or is image-only. Try pasting your CV as plain text.")
        return text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx if available, otherwise error."""
    try:
        from docx import Document
        from io import BytesIO
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise ValueError("DOCX support requires python-docx. Install: pip install python-docx")


# ── deterministic extraction ──

# ponytail: regex-based, covers 90% of CV formats. Edge cases handled by agent phase.
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_PHONE_RE = re.compile(r'(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}')
_LINKEDIN_RE = re.compile(r'linkedin\.com/in/[\w-]+')
_GITHUB_RE = re.compile(r'github\.com/[\w.-]+')
_PORTFOLIO_RE = re.compile(r'(?:portfolio|website|web):\s*(https?://[^\s]+)', re.I)
_LOCATION_RE = re.compile(r'(?:London|Manchester|Birmingham|Leeds|Edinburgh|Glasgow|Bristol|'
                           r'Liverpool|Sheffield|Oxford|Cambridge|Cardiff|Belfast|'
                           r'New York|San Francisco|Chicago|Austin|Seattle|Boston|'
                           r'Berlin|Paris|Amsterdam|Toronto|Sydney|Singapore|'
                           r'Remote|United Kingdom|UK|USA|US)[\s,]*(?:UK|United Kingdom)?', re.I)
_NAME_RE = re.compile(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})', re.M)

# Common skills dict — can be expanded
_KNOWN_SKILLS = {
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C", "C#",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "Bash",
    "FastAPI", "Django", "Flask", "Spring", "Express", "React", "Vue", "Angular",
    "Next.js", "Node.js", "PyTorch", "TensorFlow", "HuggingFace", "scikit-learn",
    "Pandas", "NumPy", "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "Ansible",
    "Linux", "Git", "GitHub", "GitLab", "CI/CD", "Jenkins", "Nginx", "Apache",
    "GraphQL", "REST", "gRPC", "WebSocket", "RabbitMQ", "Kafka", "Celery",
    "pytest", "Jest", "Mocha", "Selenium", "Cypress",
    "HTML", "CSS", "Sass", "Tailwind", "Bootstrap",
    "RAGAS", "LangChain", "Ollama", "OpenAI", "Claude", "Hermes",
    "React Native", "Flutter", "Electron",
    "EJB", "JPA", "Hibernate", "SQLAlchemy",
    "Redis", "Celery", "Nginx",
}


def _extract_deterministic(cv_text: str) -> dict:
    """Extract everything we can without an LLM."""
    profile = {
        "schema_version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "personal": {},
        "work_experience": [],
        "education": [],
        "skills": {"languages": [], "frameworks": [], "databases": [], "devops": [], "ai_ml": [], "tools": [], "soft_skills": []},
        "projects": [],
        "certifications": [],
        "languages": [],
        "work_authorization": {"status": ""},
        "preferences": {"preferred_roles": [], "preferred_locations": [], "preferred_work_modes": []},
        "cv_tailoring": {},
        "learning": {"preferred_company_patterns": [], "salary_signal": {}, "role_refinements": [], "keyword_effectiveness": {}},
        "confirmed_profile_facts": [],
        "evaluation_context": {"behavioral_guardrails": [], "scoring_guidance": {}},
        "company_notes": {},
        "saved_answers": [],
        "platform_accounts": [],
    }

    # Email
    emails = _EMAIL_RE.findall(cv_text)
    if emails:
        profile["personal"]["email"] = emails[0]

    # Phone
    phones = _PHONE_RE.findall(cv_text)
    if phones:
        profile["personal"]["phone"] = phones[0].strip()

    # LinkedIn
    linkedin = _LINKEDIN_RE.findall(cv_text)
    if linkedin:
        profile["personal"]["linkedin_url"] = f"https://www.{linkedin[0]}" if not linkedin[0].startswith("http") else linkedin[0]

    # GitHub
    github = _GITHUB_RE.findall(cv_text)
    if github:
        gh = github[0]
        # Filter out generic github.com matches
        if gh != "github.com" and not gh.endswith(".github.com"):
            profile["personal"]["github_url"] = f"https://{gh}" if not gh.startswith("http") else gh

    # Portfolio
    portfolio = _PORTFOLIO_RE.findall(cv_text)
    if portfolio:
        profile["personal"]["portfolio_url"] = portfolio[0]

    # Location
    locations = _LOCATION_RE.findall(cv_text)
    if locations:
        profile["personal"]["location"] = locations[0]

    # Name — first line heuristic
    lines = [l.strip() for l in cv_text.split("\n") if l.strip()]
    if lines:
        name_match = _NAME_RE.match(lines[0])
        if name_match and not _EMAIL_RE.search(lines[0]):
            profile["personal"]["name"] = name_match.group(1)

    # Skills — keyword match
    text_lower = cv_text.lower()
    skill_categories = {
        "languages": {"Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "Bash"},
        "frameworks": {"FastAPI", "Django", "Flask", "Spring", "Express", "React", "Vue", "Angular", "Next.js", "Node.js", "EJB", "JPA", "Hibernate", "SQLAlchemy"},
        "databases": {"PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite"},
        "devops": {"Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "Ansible", "Linux", "Nginx", "Jenkins", "CI/CD"},
        "ai_ml": {"PyTorch", "TensorFlow", "HuggingFace", "scikit-learn", "Pandas", "NumPy", "RAGAS", "LangChain", "Ollama", "OpenAI", "Claude", "Hermes"},
        "tools": {"Git", "GitHub", "GitLab", "pytest", "Jest", "Mocha", "Selenium", "Cypress", "VS Code", "IntelliJ", "Celery", "RabbitMQ", "Kafka"},
    }
    for category, skill_set in skill_categories.items():
        found = []
        for skill in skill_set:
            if skill.lower() in text_lower:
                found.append({"name": skill, "proficiency": "intermediate"})
        if found:
            profile["skills"][category] = found

    return profile


# ── gap detection ──


REQUIRED_FIELDS = [
    ("personal.name", "Full name"),
    ("personal.email", "Email address"),
    ("personal.location", "Current location (city, country)"),
    ("work_authorization.status", "Work authorization / visa status"),
    ("preferences.preferred_roles", "Target job roles"),
    ("preferences.preferred_locations", "Preferred work locations"),
    ("preferences.preferred_work_modes", "Remote / Hybrid / Onsite preference"),
]

OPTIONAL_AGENT_FIELDS = [
    "personal.preferred_headline",
    "personal.phone",
    "personal.summary",
    "work_experience",
    "education",
    "projects",
    "languages",
    "preferences.salary_range",
    "preferences.experience_levels",
    "preferences.availability",
]


def _get_nested(profile: dict, path: str):
    parts = path.split(".")
    target = profile
    for p in parts:
        if isinstance(target, dict):
            target = target.get(p)
        else:
            return None
    return target


def _is_empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


def _find_gaps(profile: dict) -> list[tuple[str, str]]:
    """Return (field_path, label) for required fields still empty."""
    return [(path, label) for path, label in REQUIRED_FIELDS if _is_empty(_get_nested(profile, path))]


# ── agent extraction ──


def _run_agent_extraction(cv_text: str, profile: dict) -> dict:
    """Use the agent to extract structured sections from CV text into profile."""
    # Temporarily persist so agent's profile_read/profile_write tools can access it
    save_profile(profile)
    system = (
        "You are an expert CV parser. You receive raw CV text and a partial profile JSON. "
        "Your job: extract structured data from the CV into the profile.\n\n"
        "Fill these sections if you find them in the CV:\n"
        "- personal.preferred_headline: professional headline\n"
        "- personal.phone: if not already filled\n"
        "- personal.summary: 2-3 sentence professional summary\n"
        "- work_experience[]: company, title, start_date, end_date, location, description, technologies, highlights\n"
        "- education[]: institution, degree, field, dates, location\n"
        "- projects[]: name, description, url, technologies, highlights\n"
        "- certifications[]: name, issuer, date\n"
        "- languages[]: human languages spoken\n"
        "- preferences.experience_levels[]: target levels\n"
        "- preferences.availability: when can they start\n\n"
        "IMPORTANT: Only add information you can directly find or reasonably infer from the CV text. "
        "Do not hallucinate or invent details.\n\n"
        "Return the COMPLETE profile JSON with your additions merged in."
    )
    user = f"CV TEXT:\n\n{cv_text}\n\nCURRENT PROFILE:\n{json.dumps(profile, indent=2)}"
    raw = Agent().run(prompt=user, system=system, temperature=0.2)
    result = extract_json(raw)
    if isinstance(result, dict):
        return result
    return profile


def _generate_agent_questions(cv_text: str, profile: dict) -> list[dict]:
    """Agent generates personalized questions to fill remaining gaps and enrich metadata."""
    # Persist so agent's profile_read tool can access the current profile
    save_profile(profile)
    gaps = _find_gaps(profile)
    gap_list = "\n".join(f"- {label} ({path})" for path, label in gaps) if gaps else "(all required fields filled)"

    system = (
        "You are an expert career coach onboarding a job seeker into HaxJobs, "
        "a job search automation platform. The user has uploaded their CV and we have "
        "extracted a partial profile.\n\n"
        "Your job: generate 5-8 specific, useful questions that will:\n"
        "1. Fill remaining required gaps in the profile (listed below)\n"
        "2. Add depth and detail useful for job matching, CV tailoring, and the learning engine\n"
        "3. Help the platform understand the candidate beyond what's on the CV\n\n"
        "Good questions cover:\n"
        "- Specific technologies and proficiency levels (not just 'Python' but 'FastAPI with async, PostgreSQL optimization')\n"
        "- Project impact metrics ('how many users', 'what did you improve by X%')\n"
        "- Career trajectory preferences ('do you want to go deep in backend or branch into AI?')\n"
        "- Non-obvious skills ('I notice you built X, did you also handle deployment?')\n"
        "- Company culture fit ('what kind of team makes you most productive?')\n"
        "- Industry preferences ('fintech vs healthtech vs pure SaaS')\n\n"
        "Return a JSON OBJECT with a 'questions' key containing the array:\n"
        '{"questions": [{"field": "...", "question": "...", "type": "text|list", "description": "..."}, ...]}'
    )
    user = (
        f"CV TEXT:\n\n{cv_text[:3000]}\n\n"
        f"CURRENT PROFILE:\n{json.dumps(profile, indent=2)}\n\n"
        f"REMAINING REQUIRED GAPS:\n{gap_list}\n\n"
        f"Generate 5-8 personalized questions. Focus on filling gaps AND adding depth."
    )
    raw = Agent().run(prompt=user, system=system, temperature=0.7)
    result = extract_json(raw)
    if isinstance(result, dict):
        questions = result.get("questions", [])
        if isinstance(questions, list):
            return questions
    return []


# ── wizard flow ──


def process_cv(cv_text: str) -> tuple[dict, list[dict], list[dict]]:
    """Full pipeline: deterministic → agent extraction → agent questions.

    Returns (profile, questions, extraction_phases).
    """
    phases = [{"phase": "reading", "label": "Reading your CV…", "done": True}]

    profile = _extract_deterministic(cv_text)
    phases.append({"phase": "extracting", "label": "Extracting skills & contact…", "done": True})

    profile = _run_agent_extraction(cv_text, profile)
    phases.append({"phase": "agent_enriching", "label": "Enriching with AI…", "done": True})

    questions = _generate_agent_questions(cv_text, profile)
    phases.append({"phase": "generating_questions", "label": "Profile draft ready", "done": True})

    return profile, questions, phases


def get_next_question(profile: dict) -> dict | None:
    global _answered_questions, _agent_questions
    pending = [q for q in _agent_questions if q["field"] not in _answered_questions]

    # First, check required gaps
    gaps = _find_gaps(profile)
    unanswered_gaps = [(p, l) for p, l in gaps if p not in _answered_questions]
    if unanswered_gaps:
        path, label = unanswered_gaps[0]
        return {
            "field": path,
            "question": f"What is your {label.lower()}?",
            "type": "text",
            "description": f"Required: {label}",
        }

    # Then agent-generated questions
    if pending:
        return pending[0]

    return None


def apply_answer(profile: dict, field_path: str, answer: str) -> dict:
    global _answered_questions
    _answered_questions.append(field_path)

    # Check if this is a list field
    field_key = field_path.split(".")[-1]
    # List fields: split comma-separated values
    _list_keys = ["roles", "locations", "work_modes", "levels", "technologies",
                  "highlights", "relevance_tags", "industries", "company_sizes",
                  "excluded_companies"]
    is_list = any(key in field_key for key in _list_keys)

    if is_list and "," in answer:
        value = [item.strip() for item in answer.split(",") if item.strip()]
    elif field_path.startswith("skills.") and field_key:
        # Skill category — parse as skill name
        value = [{"name": answer.strip(), "proficiency": "intermediate"}]
    elif field_path == "preferences.salary_range":
        # Parse salary range
        value = {"currency": "GBP", "flexibility": answer}
    else:
        value = answer

    parts = field_path.split(".")
    target = profile
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        target = target[part]

    if parts[-1] not in target or not isinstance(target.get(parts[-1]), (list, dict)):
        target[parts[-1]] = value
    elif isinstance(target[parts[-1]], list):
        if isinstance(value, list):
            target[parts[-1]] = value
        else:
            target[parts[-1]].append(value)
    else:
        target[parts[-1]] = value

    return profile


# ── persist ──


def save_profile(profile: dict):
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    PROFILE_PATH.chmod(0o600)


def load_profile() -> dict | None:
    """Return profile only if user completed onboarding."""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            data = json.load(f)
        if data.get("onboarding_complete"):
            return data
    return None


def delete_profile():
    """Remove the persisted profile so onboarding starts fresh."""
    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()


# ── session ──


def start_session(profile: dict, questions: list[dict]):
    global _pending_profile, _answered_questions, _phase, _agent_questions
    _pending_profile = profile
    _answered_questions = []
    _phase = "wizard"
    _agent_questions = questions


def get_session() -> tuple[dict | None, str, int]:
    if _pending_profile is None:
        return None, "not_started", 0
    pending_questions = [
        q for q in _agent_questions
        if q["field"] not in _answered_questions
    ]
    gap_count = len(_find_gaps(_pending_profile or {}))
    remaining = max(gap_count, len(pending_questions))
    return _pending_profile, _phase, remaining


def clear_session():
    global _pending_profile, _answered_questions, _phase, _agent_questions
    _pending_profile = None
    _answered_questions = []
    _phase = "deterministic"
    _agent_questions = []
