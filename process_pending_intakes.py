#!/usr/bin/env python3
# ⚠ LEGACY — DO NOT USE ⚠
# This file is dead code. It is NOT imported by anything in the pipeline.
# All evaluation is now handled by evaluate_with_hermes.py (Hermes LLM-based).
# This file contains hardcoded Spotify-centric scoring rules that are outdated.
# It was superseded when the pipeline moved from rule-based to Hermes-based evaluation.
# Keeping for reference only. If you're looking for the evaluator, see evaluate_with_hermes.py.
import json
import os
import re
import smtplib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Any

BASE_DIR = Path('/home/hermes/haxjobs')
INTAKE_DIR = BASE_DIR / 'intake'
PACKS_DIR = BASE_DIR / 'packs'
PROFILE_PATH = BASE_DIR / 'profile' / 'arinze_profile.local.json'
STATE_DIR = BASE_DIR / 'state'
MANIFEST_PATH = STATE_DIR / 'last_batch_manifest.json'

APPLICANT_NAME = 'Arinze Elenasulu'
HEADLINE = 'Python Backend Engineer | AI & Automation'
PHONE = '+447****5497'
EMAIL = 'elenasuluarinze@gmail.com'
LINKEDIN = 'https://www.linkedin.com/in/arinze-elenasulu-b011a1249'
GITHUB = 'https://github.com/haxsysgit'

ROLE_THEME = {
    'backend': {
        'accent': '#1d4ed8',
        'summary_focus': 'backend systems, internal tooling, reliability, and developer productivity',
    },
    'fullstack': {
        'accent': '#7c3aed',
        'summary_focus': 'backend systems with practical full stack collaboration across product surfaces',
    },
    'ai_engineer': {
        'accent': '#0891b2',
        'summary_focus': 'AI engineering, agentic workflows, LLM integration, and practical AI tooling',
    },
    'other': {
        'accent': '#0f766e',
        'summary_focus': 'backend systems, workflow automation, and practical AI product work',
    },
}


@dataclass
class FitResult:
    score: int
    verdict: str
    role_type: str
    strongest_matches: list[str]
    major_gaps: list[str]
    sponsorship_risk: str
    summary: str
    questions_for_arinze: list[str]
    decision: str


@dataclass
class PackArtifacts:
    pack_dir: Path
    fit_report: Path
    tailored_cv_md: Path | None = None
    tailored_cv_html: Path | None = None
    tailored_cv_pdf: Path | None = None
    cover_letter_md: Path | None = None
    cover_letter_html: Path | None = None
    cover_letter_pdf: Path | None = None
    questions_md: Path | None = None
    questions_html: Path | None = None
    questions_pdf: Path | None = None
    pack_md: Path | None = None
    pack_html: Path | None = None
    pack_pdf: Path | None = None
    telegram_summary: Path | None = None


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_html(text: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.I)
    text = re.sub(r'</div\s*>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_text(text: str) -> str:
    replacements = {
        '—': ' - ',
        '–': ' - ',
        '“': '"',
        '”': '"',
        '’': "'",
        ' ': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def sanitize_filename(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r'[^A-Za-z0-9]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text or 'Unknown'


def infer_company_name(job: dict[str, Any]) -> str:
    url = (job.get('source_url') or '').lower()
    if 'jobs.lever.co/spotify' in url:
        return 'Spotify'
    return normalize_text(job.get('company') or 'Unknown Company')


def team_name(job: dict[str, Any]) -> str:
    team = normalize_text(job.get('company') or '')
    company = infer_company_name(job)
    if team.lower() == company.lower():
        return ''
    return team


def cleaned_title(job: dict[str, Any]) -> str:
    return normalize_text(job.get('title') or 'Untitled Role')


def cleaned_jd(job: dict[str, Any]) -> str:
    return normalize_text(strip_html(job.get('jd_text') or ''))


def has_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def classify_role(title: str, jd: str) -> str:
    text = f'{title} {jd}'.lower()
    title_lower = title.lower()

    # === HARD GATE: non-engineering job families (checked before any role matching) ===
    NON_ENG_TITLE_PATTERNS = [
        r'\baccount\s+executive\b', r'\baccount\s+manager\b', r'\benterprise\s+account\b',
        r'\bsales\s+development\b', r'\bsales\s+representative\b', r'\bsdr\b',
        r'\brvp\b', r'\bvice\s+president\b', r'\bdirector\b',
        r'\bmarketing\b', r'\bcommunications\b', r'\bpublic\s+relations\b',
        r'\balliances\b', r'\bbusiness\s+development\b',
        r'\blegal\s+counsel\b', r'\bcounsel\b', r'\battorney\b',
        r'\bpeople\s+relations\b', r'\bhuman\s+resources\b', r'\brecruiter\b',
        r'\btalent\s+acquisition\b', r'\bhr\s+manager\b',
        r'\bfinance\b', r'\btax\b', r'\baccountant\b', r'\bcontroller\b',
        r'\bcontracts\s+specialist\b', r'\bcompliance\b',
    ]
    for pattern in NON_ENG_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return 'non_engineering'
    if has_any(text, ['engineering manager']):
        return 'manager'
    if has_any(text, ['research scientist']):
        return 'research'
    # AI/agentic roles — detect before generic backend/fullstack to ensure proper classification
    if has_any(text, ['ai engineer', 'ai/ml engineer', 'agentic', 'ai deployment', 'gen ai engineer']):
        return 'ai_engineer'
    if has_any(text, ['machine learning engineer', 'applied research engineer']):
        return 'ml'
    if has_any(text, ['android', 'ios', 'mobile infrastructure']):
        return 'mobile'
    if has_any(text, ['security engineer']):
        return 'security'
    if 'c++' in text:
        return 'cpp'
    if has_any(text, ['frontend engineer']):
        return 'frontend'
    if has_any(text, ['full stack engineer', 'fullstack engineer', 'full-stack engineer']):
        return 'fullstack'
    if has_any(text, ['backend engineer', 'backend software engineer', 'backend developer', 'back-end engineer', 'back-end developer']):
        return 'backend'
    if 'staff engineer' in text:
        return 'staff_platform'
    return 'other'


def compute_fit(job: dict[str, Any], profile: dict[str, Any]) -> FitResult:
    title = cleaned_title(job)
    jd = cleaned_jd(job)
    text = f'{title} {jd}'.lower()
    role_type = classify_role(title, jd)
    company = infer_company_name(job)
    location = normalize_text(job.get('location') or '')

    hard_block = None
    if has_any(text, ['must be a british citizen', 'developed vetting', 'dv clearance', 'security clearance required']):
        hard_block = 'Role has a citizenship or clearance requirement that Arinze cannot meet.'
    if has_any(text, ['permanent right to work required', 'no sponsorship', 'must have permanent right to work']):
        hard_block = 'Role appears to have a strict right-to-work or sponsorship blocker.'

    if hard_block:
        return FitResult(
            score=5,
            verdict='SKIP',
            role_type=role_type,
            strongest_matches=['Location and general software interest are not enough to offset the eligibility blocker.'],
            major_gaps=[hard_block],
            sponsorship_risk='high',
            summary=hard_block,
            questions_for_arinze=[],
            decision='skipped',
        )

    stack_score = 0
    role_score = 0
    experience_score = 0
    location_lower = location.lower()
    is_prime_location = any(city in location_lower for city in ['london', 'manchester', 'leeds'])
    location_score = 14 if is_prime_location else (12 if 'uk' in location_lower or 'united kingdom' in location_lower else 10)

    strongest_matches: list[str] = []
    major_gaps: list[str] = []
    questions: list[str] = []

    if role_type == 'backend':
        stack_score = 33
        role_score = 24
        experience_score = 11
        strongest_matches = [
            'Strong overlap with Arinze\'s backend stack from Vigilis and Pharmax, especially Python, FastAPI, SQLAlchemy, PostgreSQL, Docker, and pytest-led engineering.',
            'Good match for internal platform and reliability work because he has built operational backend workflows and developer-facing AI tooling.',
            'London-based and actively targeting backend and automation roles, with immediate availability.',
        ]
        major_gaps = [
            'This role is framed around Spotify-scale platform systems, so the biggest gap is direct proof of very large-scale internal release infrastructure.',
            'Future sponsorship may still come up later even though immediate UK availability is fine.',
        ]
        if 'release' in text:
            strongest_matches[1] = 'Especially good fit for release and developer-productivity work because Haxaml and Hermes-style tooling map naturally to internal platform workflows, reliability, and engineering enablement.'
        if 'subscriptions' in text:
            strongest_matches[1] = 'Strong backend fit for data-backed subscription workflows because Arinze has built payment-adjacent and reporting-heavy operational systems with careful validation and data handling.'
            major_gaps.insert(0, 'The role expects global subscription-scale systems, while Arinze\'s strongest evidence is from smaller operational products rather than consumer internet scale.')
    elif role_type == 'fullstack':
        stack_score = 24
        role_score = 18
        experience_score = 11
        strongest_matches = [
            'Strong backend-first fit with real Python, PostgreSQL, SQLAlchemy, Docker, and API experience, plus workable React and TypeScript collaboration experience.',
            'Good fit for product-facing engineering where the backend does most of the heavy lifting and the UI layer needs pragmatic cross-stack collaboration.',
            'London-based and aligned with software roles that mix backend ownership with practical delivery across the wider application surface.',
        ]
        major_gaps = [
            'Arinze\'s strongest depth is still backend rather than deep frontend-specialist ownership.',
            'The role may expect broader production full stack ownership than is currently evidenced.',
        ]
        if 'django' in text:
            strongest_matches[0] = 'Strong Python and PostgreSQL overlap makes this a credible full stack stretch, especially for backend APIs, data workflows, and product engineering around a web app.'
            major_gaps.insert(0, 'The JD explicitly mentions Django, which is adjacent to Arinze\'s Python backend work but not directly confirmed in the profile.')
            stack_score += 4
        if 'java backend' in text or 'java backend services' in text:
            major_gaps.insert(0, 'The backend side leans on Java services, while Arinze\'s strongest evidence is in Python backend work.')
            stack_score -= 2
        if 'payments' in text or 'payment' in text or 'transactions' in text:
            major_gaps.insert(0, 'This team handles large payment volumes, and Arinze has payment-related product workflow exposure but not clear evidence of running global payment infrastructure.')
            stack_score -= 2
        if 'react' in text or 'typescript' in text:
            stack_score += 2
    elif role_type == 'ai_engineer':
        stack_score = 30
        role_score = 22
        experience_score = 10
        strongest_matches = [
            'Arinze has real hands-on AI engineering experience: agentic workflows via Hermes, RAG pipelines with RAGAS evaluation in Pharmax, and AI governance tooling with Haxaml.',
            'Daily AI agent usage via Archilles (Hermes Agent fork) makes him credible for roles that need builder-level AI engineering, not just framework familiarity.',
            'Python backend fundamentals (FastAPI, PostgreSQL, Docker, pytest) plus AI engineering make him a strong hybrid for AI product and platform roles.',
        ]
        major_gaps = [
            'Production AI platform experience at scale is still developing rather than fully proven.',
            'Some roles may expect deeper cloud infrastructure or MLOps depth beyond current evidence.',
        ]
    elif role_type == 'frontend':
        stack_score = 10
        role_score = 8
        experience_score = 8
        strongest_matches = [
            'There is some React and TypeScript exposure in Arinze\'s profile.',
            'He can collaborate across UI and backend boundaries when product flows depend on backend logic.',
        ]
        major_gaps = [
            'This is primarily a frontend role, while Arinze\'s strongest identity is backend and AI automation.',
            'The strongest public evidence for deep frontend ownership is limited.',
        ]
    elif role_type == 'ml':
        stack_score = 12
        role_score = 10
        experience_score = 8
        strongest_matches = [
            'Arinze has real AI and evaluation exposure through Pharmax, RAGAS, and agent/tooling work.',
            'He can discuss LLM workflow design, evaluation, and practical AI product integration credibly.',
        ]
        major_gaps = [
            'The JD centers machine learning engineering depth, while Arinze\'s strongest experience is AI application engineering rather than traditional ML platform ownership.',
            'Some ML roles expect deeper research or production ML systems depth beyond current evidence.',
        ]
    elif role_type == 'research':
        stack_score = 6
        role_score = 5
        experience_score = 4
        strongest_matches = [
            'There is genuine AI interest and some evaluation experience.',
        ]
        major_gaps = [
            'Research scientist roles ask for a much stronger research publication and advanced ML track record than the current profile shows.',
        ]
    elif role_type == 'manager':
        stack_score = 10
        role_score = 4
        experience_score = 3
        strongest_matches = [
            'There is some credibility in hands-on AI and backend building.',
        ]
        major_gaps = [
            'This role asks for formal management depth, which is not the main story in Arinze\'s current profile.',
        ]
    elif role_type == 'non_engineering':
        stack_score = 0
        role_score = 0
        experience_score = 0
        strongest_matches = []
        major_gaps = ['This is not an engineering role — it is a sales, marketing, business, or administrative position outside Arinze\'s target lane.']
    elif role_type in {'cpp', 'mobile', 'security', 'legal', 'non_fit_business', 'staff_platform'}:
        presets = {
            'cpp': (4, 3, 4, 'The role is centered on C++, which is not Arinze\'s strongest current application direction.'),
            'mobile': (4, 3, 4, 'The role is centered on mobile platform depth, while Arinze is targeting backend and AI engineering.'),
            'security': (5, 4, 5, 'The role expects product security depth that is not clearly evidenced in the current profile.'),
            'legal': (0, 0, 0, 'This is a legal role and is outside Arinze\'s engineering profile.'),
            'non_fit_business': (0, 0, 0, 'This is a business or product role outside Arinze\'s target lane.'),
            'staff_platform': (14, 8, 2, 'The platform angle is relevant, but the staff-level seniority is a major jump from the current evidence base.'),
        }
        stack_score, role_score, experience_score, gap = presets[role_type]
        strongest_matches = ['There is some adjacent relevance from software engineering or platform interest.']
        major_gaps = [gap]
    else:
        stack_score = 14
        role_score = 10
        experience_score = 7
        strongest_matches = ['Some software engineering overlap exists.']
        major_gaps = ['The role is not tightly aligned with Arinze\'s current strongest lane.']

    if company == 'Spotify':
        strongest_matches.append('Spotify\'s London location and the mix of product scale, internal tooling, and AI-aware engineering make it a realistic target in principle.')

    # Entry-level / junior / graduate / intern bonus
    is_entry_level = has_any(text, ['junior', 'graduate', 'grad ', 'intern', 'internship', 'entry level', 'entry-level', 'associate', 'trainee', 'apprentice', 'new grad', 'campus'])
    if is_entry_level and role_type not in {'legal', 'non_fit_business', 'security', 'research'}:
        experience_score += 4
        role_score += 2
        strongest_matches.insert(0, 'This is an entry-level, graduate, or junior role — Arinze\'s profile naturally fits early-career expectations.')

    # Mid-level bonus (neither entry nor senior signals)
    has_senior_signal = has_any(text, ['senior', 'lead ', 'principal', 'staff engineer', 'head of', 'director', 'vp '])
    if not is_entry_level and not has_senior_signal and role_type in {'backend', 'fullstack', 'ai_engineer', 'ml'}:
        experience_score += 2
        strongest_matches.insert(0, 'Mid-level role without senior expectations — a natural fit for Arinze\'s experience level.')

    if 'java' in text and role_type == 'backend':
        major_gaps.insert(0, 'The role leans on Java on the backend, while Arinze\'s strongest hands-on depth is in Python.')
        stack_score -= 4

    score = max(0, min(100, stack_score + role_score + experience_score + location_score))
    sponsorship_risk = 'medium' if location_score >= 10 else 'high'

    if score >= 80:
        verdict = 'STRONG_FIT'
        decision = 'completed'
    elif score >= 60:
        verdict = 'GOOD_FIT'
        decision = 'completed'
    elif score >= 40:
        verdict = 'WEAK_FIT'
        decision = 'skipped'
    else:
        verdict = 'SKIP'
        decision = 'skipped'

    strongest_matches = strongest_matches[:3]
    major_gaps = major_gaps[:3]

    if score >= 60:
        questions.append('If this application reaches a form stage, confirm the final sponsorship wording before any submission.')
    if role_type == 'fullstack' and ('react' in text or 'typescript' in text):
        questions.append('If needed later, be ready to describe the clearest React or TypeScript contribution with concrete examples.')
    if 'payments' in text or 'transactions' in text:
        questions.append('Prepare one concise story about handling transaction-sensitive workflows and validation, even if the scale was smaller.')

    summary = (
        f'{title} at {company} scores {score} because the role has '
        f'{ROLE_THEME.get(role_type, ROLE_THEME["other"])["summary_focus"]} in the overlap zone, '
        f'but the main risks are {major_gaps[0].lower() if major_gaps else "limited direct proof on some requirements"}.'
    )

    return FitResult(
        score=score,
        verdict=verdict,
        role_type=role_type,
        strongest_matches=strongest_matches,
        major_gaps=major_gaps,
        sponsorship_risk=sponsorship_risk,
        summary=normalize_text(summary),
        questions_for_arinze=questions,
        decision=decision,
    )


def load_email_credentials() -> tuple[str, str] | None:
    env_path = Path.home() / '.hermes' / '.env'
    if not env_path.exists():
        return None
    values = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    email_address = values.get('EMAIL_ADDRESS') or 'archilleshaxsys@gmail.com'
    email_password = values.get('EMAIL_PASSWORD')
    if not email_password:
        return None
    return email_address, email_password.replace(' ', '')


def send_email(subject: str, body: str, attachments: list[Path]) -> tuple[bool, str]:
    creds = load_email_credentials()
    if not creds:
        return False, 'EMAIL_PASSWORD not available in ~/.hermes/.env'
    sender, password = creds
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = EMAIL
    msg['Subject'] = normalize_text(subject)
    msg.set_content(normalize_text(body))

    for attachment in attachments:
        data = attachment.read_bytes()
        msg.add_attachment(data, maintype='application', subtype='pdf', filename=attachment.name)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=60) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, 'sent'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


def ensure_no_em_dash(text: str) -> str:
    text = normalize_text(text)
    return text.replace(' - ', ' - ')


def write_text(path: Path, content: str) -> None:
    cleaned = ensure_no_em_dash(content)
    if '—' in cleaned:
        raise ValueError(f'em dash found in {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned + ('\n' if not cleaned.endswith('\n') else ''))


def bullet_list(items: list[str]) -> str:
    return '\n'.join(f'- {ensure_no_em_dash(item)}' for item in items)


def html_page(title: str, body: str, accent: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    @page {{ size: A4; margin: 18mm 16mm; }}
    body {{ font-family: Arial, Helvetica, sans-serif; color: #111827; line-height: 1.45; font-size: 12px; }}
    .wrap {{ max-width: 820px; margin: 0 auto; }}
    .hero {{ border: 1px solid #d1d5db; border-top: 5px solid {accent}; padding: 18px 18px 14px; border-radius: 8px; background: #f8fafc; margin-bottom: 18px; }}
    .hero h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .hero .sub {{ color: #374151; font-size: 13px; }}
    h2 {{ font-size: 15px; margin: 18px 0 8px; color: {accent}; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
    h3 {{ font-size: 13px; margin: 14px 0 4px; color: #111827; }}
    p {{ margin: 0 0 10px; }}
    ul {{ margin: 6px 0 10px 18px; padding: 0; }}
    li {{ margin: 0 0 6px; }}
    .meta {{ color: #4b5563; font-size: 11px; margin-bottom: 6px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .pillbar {{ margin-top: 10px; color: #374151; font-size: 11px; }}
    .pillbar span {{ display: inline-block; border: 1px solid #d1d5db; border-radius: 999px; padding: 4px 8px; margin: 0 6px 6px 0; }}
    .section {{ break-inside: avoid; }}
  </style>
</head>
<body>
  <div class="wrap">
    {body}
  </div>
</body>
</html>
'''


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    cmd = [
        '/usr/bin/google-chrome',
        '--headless',
        '--no-sandbox',
        '--disable-gpu',
        '--no-pdf-header-footer',
        f'--print-to-pdf={str(pdf_path)}',
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f'PDF generation failed for {pdf_path}')


def cv_markdown(company: str, role_title: str, fit: FitResult, job: dict[str, Any]) -> str:
    role_type = fit.role_type
    summary_map = {
        'backend': "I'm a Python backend engineer — I build APIs, database-backed systems, internal tools, and automation workflows that people actually use every day. Most of my experience is in keeping services reliable under real usage: careful data handling, clear validation, and writing code that doesn't fall apart when requirements change. I enjoy platform and infrastructure-adjacent backend work where engineering quality and developer experience matter as much as the feature itself.",
        'fullstack': "I'm a Python backend engineer who's comfortable working across the full stack where APIs, data models, and product surfaces need to line up cleanly. My deepest strength is on the backend, but I've built with React and TypeScript enough to collaborate confidently on product-facing features. I enjoy roles where backend depth meets practical cross-stack delivery.",
        'ai_engineer': "I'm a Python backend engineer who also spends a lot of time building with AI — agentic workflows, RAG pipelines, LLM-backed tools, and AI-powered developer tooling. I use AI agents and LLM frameworks pretty much every day, so I've gotten comfortable building, evaluating, and shipping AI features that connect to real workflows. I'm looking for roles where I can keep growing at that intersection of solid backend engineering and practical AI work.",
    }
    core_skills = [
        'Backend: Python, FastAPI, SQLAlchemy, Alembic, REST APIs, async backend patterns',
        'Databases: PostgreSQL, schema design, query optimization, data modeling for real workflows',
        'Infrastructure & reliability: Docker, Linux, structured logging, validation, error handling',
        'Testing: pytest, structured test design, integration coverage, reliability-focused QA',
        'AI engineering: LLM integration, RAG pipelines, agentic workflows, RAGAS evaluation, MCP tooling',
    ]
    if role_type == 'fullstack':
        core_skills.append('Frontend: React, TypeScript, JavaScript, backend-frontend integration')

    header = f'''# {APPLICANT_NAME}\n\n**{HEADLINE}**  \nLondon, UK · {EMAIL} · {PHONE}  \nLinkedIn: {LINKEDIN}  \nGitHub: {GITHUB}\n'''

    body = f'''
## Professional Summary
{summary_map.get(role_type, "I'm a Python backend engineer who builds APIs, database-backed systems, and AI-assisted software workflows. I'm looking for roles where I can keep growing — backend, platform, or AI engineering — with a team that values reliability, clear thinking, and practical engineering judgment.")}

## Core Skills
{bullet_list(core_skills)}

## Experience
### Vigilis, Software Engineer
**August 2024 to February 2026 · Lagos, Nigeria**
- Built the backend for a pharmacy operations platform handling sales, inventory, payments, and reporting — used day-to-day by pharmacy staff.
- Designed the data models and API layer (FastAPI, PostgreSQL, SQLAlchemy) with role-based access, JWT auth, and Alembic for schema migrations.
- Tightened reliability across the system: added structured logging, input validation, and business rule enforcement to catch errors before they reached users.
- Sat with pharmacy staff directly to understand their manual processes, then turned those workflows into software that made their daily work faster and less error-prone.

### Bucca Hut, AI and Backend Engineer (Contract, part-time)
**February 2025 to May 2025**
- Built an AI-powered tool that analyzed sales data to surface practical business insights — designed the data pipeline and integrated LLM outputs into the reporting workflow.
- Kept the AI integration grounded: focused on reliable data inputs, clear output boundaries, and making sure the insights were actually useful rather than just clever.

### Aptech Computer Education, Software Engineer Intern
**September 2022 to August 2024 · Lagos, Nigeria**
- Contributed to backend features, debugging, and feature delivery across multiple project teams.
- Worked with Python, Flutter/Dart, and Java/Spring — gained experience across different stacks and team workflows during a hands-on training programme.

## Selected Projects
### Pharmax — AI-integrated SaaS for Nigerian pharmacies
- Built a platform that helps pharmacies manage inventory, sales, and reporting, with AI features layered on top for smarter insights.
- Backend: FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT auth, role-based access control.
- Used RAGAS to evaluate and improve the quality of AI-generated outputs before they reached users.

### Haxaml — Open-source governance tool for AI coding agents
- Built a developer tool that helps AI coding agents stay aligned with project rules, context, and decisions.
- Designed FRAME: a project memory model that tracks facts, rules, work history, and next steps so AI assistants don't drift.
- Implemented CLI and MCP integrations for context retrieval, project validation, and task tracking.

## Education
### Middlesex University, London
**BSc Information Technology**  \nGraduating June 2026

### Aptech Computer Education, Lagos
**Advanced Diploma in Software Engineering**
'''
    return ensure_no_em_dash(header + body)


def cv_html(company: str, role_title: str, fit: FitResult, markdown_text: str) -> str:
    role_type = fit.role_type if fit.role_type in ROLE_THEME else 'other'
    accent = ROLE_THEME[role_type]['accent']
    summary_match = re.search(r'## Professional Summary\n(.+?)\n\n## Core Skills', markdown_text, flags=re.S)
    skills_match = re.search(r'## Core Skills\n(.+?)\n\n## Experience', markdown_text, flags=re.S)
    summary_text = summary_match.group(1).strip() if summary_match else ''
    skills_lines = skills_match.group(1).strip().splitlines() if skills_match else []
    skills_html = ''.join(f'<li>{escape(item[2:])}</li>' for item in skills_lines)
    body = f'''
<div class="hero">
  <h1>{escape(APPLICANT_NAME)}</h1>
  <div class="sub">{escape(HEADLINE)}</div>
  <div class="pillbar">
    <span>London, UK</span>
    <span>{escape(EMAIL)}</span>
    <span>{escape(PHONE)}</span>
    <span>LinkedIn</span>
    <span>GitHub</span>
  </div>
</div>
<div class="section">
  <h2>Professional Summary</h2>
  <p>{escape(summary_text)}</p>
</div>
<div class="section">
  <h2>Core Skills</h2>
  <ul>{skills_html}</ul>
</div>
<div class="section">
  <h2>Experience</h2>
  <h3>Vigilis, Software Engineer</h3>
  <div class="meta">August 2024 to February 2026 · Lagos, Nigeria</div>
  <ul>
    <li>Built backend workflows for pharmacy operations covering sales, inventory, payments, reporting, and role-based access used in day-to-day business operations.</li>
    <li>Implemented FastAPI, SQLAlchemy, Alembic, JWT authentication, and PostgreSQL-backed workflows to support reliable operational software.</li>
    <li>Added validation, logging, and backend rules to improve maintainability, transaction accuracy, and safer day-to-day system use.</li>
    <li>Worked directly with users to turn manual operational processes into clearer software workflows.</li>
  </ul>
  <h3>Bucca Hut, AI and Backend Engineer (Contract, concurrent)</h3>
  <div class="meta">February 2025 to May 2025</div>
  <ul>
    <li>Built an AI-powered sales insight workflow that analyzed product and revenue data to suggest practical business improvements.</li>
    <li>Designed backend data flows that turned historical sales data into structured inputs for analysis.</li>
    <li>Integrated AI-assisted outputs into business workflows while keeping reliability and output boundaries under control.</li>
  </ul>
  <h3>Aptech Computer Education, Software Engineer Intern</h3>
  <div class="meta">September 2022 to August 2024 · Lagos, Nigeria</div>
  <ul>
    <li>Built practical experience across backend development, debugging, implementation work, and software delivery fundamentals.</li>
    <li>Worked across C, C++, Python, Flutter, Dart, Java, EJB, JavaBeans, and Spring during internship and training work.</li>
  </ul>
</div>
<div class="section">
  <h2>Selected Projects</h2>
  <h3>Pharmax</h3>
  <ul>
    <li>Built Pharmax, an AI-integrated SaaS for Nigerian pharmacies supporting operational workflows like inventory, sales, reporting, and AI-assisted workflows.</li>
    <li>Implemented backend logic using FastAPI, SQLAlchemy, Alembic, JWT authentication, and role-based access control.</li>
    <li>Used RAGAS in AI evaluation workflows while keeping the product grounded in real operational needs.</li>
  </ul>
  <h3>Haxaml</h3>
  <ul>
    <li>Created an open-source Python developer tool for helping AI coding agents follow project rules, retrieve context, and record decisions.</li>
    <li>Designed FRAME, a structured project memory model covering facts, rules, work history, impact maps, and expected next steps.</li>
    <li>Built CLI and MCP workflows for context retrieval, project validation, task tracking, and governed agent execution.</li>
  </ul>
</div>
<div class="section">
  <h2>Education</h2>
  <h3>Middlesex University, London</h3>
  <div class="meta">BSc Information Technology · Graduating June 2026</div>
  <h3>Aptech Computer Education, Lagos</h3>
  <div class="meta">Advanced Diploma in Software Engineering</div>
</div>
'''
    return html_page(f'{role_title} CV at {company}', body, accent)


def cover_letter_markdown(company: str, role_title: str, fit: FitResult, job: dict[str, Any]) -> str:
    team = team_name(job)
    team_phrase = f' on the {team} team' if team else ''
    title_lc = role_title.lower()

    # --- Intro hook (self-contained fragment) ---
    if fit.role_type == 'ai_engineer':
        intro = 'building AI applications that combine LLMs, retrieval, and practical product thinking is what I already do every day'
    elif fit.role_type == 'fullstack':
        intro = 'contributing as a backend-first engineer across both product-facing and backend layers is the kind of breadth I thrive on'
    elif fit.role_type == 'backend' and 'release' in title_lc:
        intro = 'developer productivity, release confidence, and internal platforms that help engineers ship safely is work I find genuinely satisfying'
    elif fit.role_type == 'backend' and 'subscriptions' in title_lc:
        intro = 'backend systems, subscription workflows, and product reliability behind a large consumer platform is a problem space I want to grow deeper in'
    else:
        intro = 'the mix of backend engineering, reliability, and practical product ownership is exactly the kind of work I enjoy and have been building toward'

    # --- Experience paragraph (varies by role type) ---
    if fit.role_type == 'ai_engineer':
        experience = (
            f'I build AI agents that work. I run a cloud-based multi-agent system for messaging, automation, and LLM-driven workflows. '
            f'I built Pharmax, an AI-integrated SaaS where I worked on RAG pipelines and evaluated outputs using RAGAS. '
            f'Behind the AI layer, I have solid backend foundations from Vigilis — FastAPI, SQLAlchemy, PostgreSQL, Docker — building operational systems '
            f'where reliability and data integrity were not optional.'
        )
    elif fit.role_type == 'fullstack':
        experience = (
            f'At Vigilis, I built backend workflows for pharmacy operations — sales, inventory, payments, reporting — turning messy real-world processes '
            f'into dependable software. I am comfortable working across the stack where APIs, data models, and UI behaviour need to line up cleanly, '
            f'though my deepest strength is on the backend side. I have also built AI tooling through Pharmax and Haxaml, which stretched my product thinking '
            f'and developer tooling skills.'
        )
    else:  # backend / other
        experience = (
            f'At Vigilis, I built backend workflows for pharmacy operations covering sales, inventory, payments, reporting, and access control. '
            f'That work meant turning messy real-world processes into dependable software — with real attention to validation, logging, maintainability, '
            f'and operational accuracy. I have also built AI and developer tooling through Pharmax and Haxaml, which gave me a broader sense of '
            f'how backend systems serve real products.'
        )

    # --- "Why this role/company" hook (varies by role type) ---
    if fit.role_type == 'ai_engineer':
        hook = (
            f'What pulled me toward {company} is that this role is not about theorising about AI — it is about identifying real opportunities '
            f'and building the tools to capture them. That is exactly what I do. I use AI tooling daily as production infrastructure, not as a curiosity.'
        )
    elif fit.role_type == 'fullstack':
        hook = (
            f'What I like about this role at {company} is the chance to own backend depth while contributing across the full product surface. '
            f'I enjoy shaping APIs and data models around real workflows, and I am most effective in teams where backend quality '
            f'and product thinking go hand in hand.'
        )
    else:
        hook = (
            f'What I like about this role at {company} is the focus on building systems people rely on every day while keeping '
            f'the engineering quality bar high. I care about building APIs carefully, shaping data models around real workflows, '
            f'and keeping software dependable under real usage.'
        )

    # --- Gap handling (strength-first, gap as honest aside) ---
    gaps = (
        f'I bring practical ownership, careful engineering judgment, and a calm approach to building systems that need to stay reliable as they grow. '
        f'My strongest depth is in Python backend engineering — I am comfortable with adjacent stacks and quick to ramp up where the overlap is real, '
        f'but I will not pretend to already know every tool in the JD.'
    )

    # --- Closing ---
    closing = (
        f'I am based in London, available to start immediately, and would welcome the chance to discuss the role further.'
    )

    body = f'''# Cover Letter - {role_title} at {company}

Hiring Team,

I am applying for the {role_title} role at {company}{team_phrase} — {intro}.

{experience}

{hook}

{gaps}

{closing}

Best regards,
Arinze Elenasulu
'''
    return ensure_no_em_dash(body)


def letter_html(company: str, role_title: str, fit: FitResult, markdown_text: str) -> str:
    role_type = fit.role_type if fit.role_type in ROLE_THEME else 'other'
    accent = ROLE_THEME[role_type]['accent']
    paragraphs = [escape(p.strip()) for p in markdown_text.split('\n\n')[1:] if p.strip()]
    rendered_paragraphs = ''.join(f'<p>{p.replace(chr(10), "<br />")}</p>' for p in paragraphs)
    body = f'''
<div class="hero">
  <h1>{escape(APPLICANT_NAME)}</h1>
  <div class="sub">Cover letter for {escape(role_title)} at {escape(company)}</div>
  <div class="pillbar">
    <span>London, UK</span>
    <span>{escape(EMAIL)}</span>
    <span>{escape(PHONE)}</span>
  </div>
</div>
<div class="section">
  {rendered_paragraphs}
</div>
'''
    return html_page(f'{role_title} cover letter at {company}', body, accent)


def questions_markdown(company: str, role_title: str, fit: FitResult, job: dict[str, Any]) -> str:
    why_company = f'I want to work at {company} because the role sits at a good intersection of backend engineering, product impact, and careful software delivery. The team is building systems people rely on at real scale, and that matches the kind of work I want to keep growing into.'
    if fit.role_type == 'backend' and 'release' in role_title.lower():
        why_company = f'I want to work at {company} because this role is close to the kind of engineering enablement work I enjoy most: release confidence, internal tools, reliability, and helping other engineers move faster without losing safety.'
    if fit.role_type == 'fullstack' and 'audiobooks' in role_title.lower():
        why_company = f'I want to work at {company} because the audiobook space mixes product thinking, creator tooling, and full stack delivery in a way that feels both practical and interesting. It is a good place to contribute backend depth while growing across the wider product surface.'
    if fit.role_type == 'fullstack' and 'whosampled' in role_title.lower():
        why_company = f'I want to work at {company} because WhoSampled is a product with a strong data and community story behind it. I like the idea of working on backend APIs, data flows, and product improvements in a smaller team where engineering ownership is broad.'

    questions = [
        ('Why do you want this role?', why_company),
        ('Tell us about yourself.', 'I am a Python backend engineer based in London. My strongest work has been building operational backend systems, AI-assisted workflows, and developer tooling. I have worked on FastAPI, SQLAlchemy, PostgreSQL, Docker, pytest, and workflow-heavy products where reliability and maintainability mattered.'),
        ('What project best matches this role?', 'Pharmax is a strong example because it combined backend APIs, PostgreSQL-backed workflows, role-aware logic, and practical AI features in a product people could use for real operational work.'),
        ('How have you used AI tools or LLMs?', 'I have used AI in practical product and tooling work, including RAGAS-based evaluation workflows, AI-assisted business analysis, and Haxaml for governed AI coding-agent workflows.'),
        ('What are your salary expectations?', 'I am flexible and mainly focused on finding the right fit. Based on the role scope and London market, I would be comfortable discussing a fair package in line with the level and total compensation structure.'),
        ('Are you comfortable with travel or hybrid work?', 'Yes. I am based in London and comfortable with hybrid work or reasonable travel where it makes sense for the role.'),
        ('Do you require sponsorship?', 'I may require sponsorship in the future, but not immediately. I am currently in the UK on a student visa, graduating on June 25, and plan to apply for the Graduate visa.'),
    ]
    if fit.role_type == 'fullstack':
        questions.insert(3, ('How do you approach working across the stack?', 'My strongest depth is on the backend side, but I am comfortable working across product flows where APIs, data models, and UI behavior need to line up cleanly. I focus on owning the hard backend parts well and collaborating clearly across the rest of the application surface.'))
    elif fit.role_type == 'backend':
        questions.insert(3, ('How do you think about reliability?', 'I try to make systems predictable under real use: clear validation, explicit rules around sensitive workflows, useful logging, careful schema changes, and tests that cover the critical paths. That mindset came from building operational software where bad data or unclear logic quickly becomes a real business problem.'))

    lines = [f'# Application Questions - {role_title} at {company}', '']
    for idx, (question, answer) in enumerate(questions, start=1):
        lines.append(f'## {idx}. {question}')
        lines.append(answer)
        lines.append('')
    return ensure_no_em_dash('\n'.join(lines).strip() + '\n')


def questions_html(company: str, role_title: str, fit: FitResult, markdown_text: str) -> str:
    role_type = fit.role_type if fit.role_type in ROLE_THEME else 'other'
    accent = ROLE_THEME[role_type]['accent']
    blocks = []
    parts = re.split(r'\n## ', markdown_text)
    for part in parts[1:]:
        title, rest = part.split('\n', 1)
        blocks.append(f'<div class="section"><h2>{escape(title)}</h2><p>{escape(rest.strip())}</p></div>')
    body = f'''
<div class="hero">
  <h1>{escape(APPLICANT_NAME)}</h1>
  <div class="sub">Application questions for {escape(role_title)} at {escape(company)}</div>
</div>
{''.join(blocks)}
'''
    return html_page(f'{role_title} application questions at {company}', body, accent)


def pack_markdown(company: str, role_title: str, fit: FitResult, cv_text: str, letter_text: str, questions_text: str) -> str:
    return ensure_no_em_dash(
        f'# Application Pack - {role_title} at {company}\n\n'
        f'## Fit Summary\n'
        f'- Score: {fit.score}\n'
        f'- Verdict: {fit.verdict}\n'
        f'- Strongest matches:\n{bullet_list(fit.strongest_matches)}\n\n'
        f'- Major gaps:\n{bullet_list(fit.major_gaps)}\n\n'
        f'## Tailored CV\n\n{cv_text}\n\n'
        f'## Cover Letter\n\n{letter_text}\n\n'
        f'## Application Questions\n\n{questions_text}'
    )


def pack_html(company: str, role_title: str, fit: FitResult) -> str:
    role_type = fit.role_type if fit.role_type in ROLE_THEME else 'other'
    accent = ROLE_THEME[role_type]['accent']
    body = f'''
<div class="hero">
  <h1>{escape(APPLICANT_NAME)}</h1>
  <div class="sub">Application pack for {escape(role_title)} at {escape(company)}</div>
  <div class="pillbar">
    <span>Score: {fit.score}</span>
    <span>Verdict: {escape(fit.verdict)}</span>
    <span>Sponsorship risk: {escape(fit.sponsorship_risk)}</span>
  </div>
</div>
<div class="section">
  <h2>Strongest matches</h2>
  <ul>{''.join(f'<li>{escape(item)}</li>' for item in fit.strongest_matches)}</ul>
</div>
<div class="section">
  <h2>Major gaps</h2>
  <ul>{''.join(f'<li>{escape(item)}</li>' for item in fit.major_gaps)}</ul>
</div>
<div class="section">
  <h2>Application link</h2>
  <p>{escape('Source URL is included in the fit report JSON saved alongside this pack.')}</p>
</div>
'''
    return html_page(f'{role_title} application pack at {company}', body, accent)


def create_pack(job: dict[str, Any], fit: FitResult) -> PackArtifacts:
    company = infer_company_name(job)
    team = team_name(job)
    role_title = cleaned_title(job)
    folder_parts = [company]
    if team:
        folder_parts.append(team)
    folder_parts.append(role_title)
    pack_dir = PACKS_DIR / sanitize_filename('_'.join(folder_parts))
    pack_dir.mkdir(parents=True, exist_ok=True)

    company_stem = sanitize_filename(company)
    fit_report = pack_dir / f'Arinze_Elenasulu_{company_stem}_Fit_Report.json'
    artifacts = PackArtifacts(pack_dir=pack_dir, fit_report=fit_report)

    fit_report_data = {
        'fit_score': fit.score,
        'verdict': fit.verdict,
        'strongest_matches': fit.strongest_matches,
        'major_gaps': fit.major_gaps,
        'sponsorship_risk': fit.sponsorship_risk,
        'application_url': job.get('source_url') or '',
        'summary': fit.summary,
        'questions_for_arinze': fit.questions_for_arinze,
    }
    save_json(fit_report, fit_report_data)

    if fit.score < 60:
        return artifacts

    cv_md = pack_dir / f'Arinze_Elenasulu_{company_stem}_Tailored_CV.md'
    cv_html_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Tailored_CV.html'
    cv_pdf = pack_dir / f'Arinze_Elenasulu_{company_stem}_Tailored_CV.pdf'
    letter_md = pack_dir / f'Arinze_Elenasulu_{company_stem}_Cover_Letter.md'
    letter_html_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Cover_Letter.html'
    letter_pdf = pack_dir / f'Arinze_Elenasulu_{company_stem}_Cover_Letter.pdf'
    questions_md_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Questions.md'
    questions_html_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Questions.html'
    questions_pdf = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Questions.pdf'
    pack_md_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Pack.md'
    pack_html_path = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Pack.html'
    pack_pdf = pack_dir / f'Arinze_Elenasulu_{company_stem}_Application_Pack.pdf'
    telegram_summary = pack_dir / 'telegram_summary.txt'

    cv_md_text = cv_markdown(company, role_title, fit, job)
    letter_md_text = cover_letter_markdown(company, role_title, fit, job)
    questions_md_text = questions_markdown(company, role_title, fit, job)
    pack_md_text = pack_markdown(company, role_title, fit, cv_md_text, letter_md_text, questions_md_text)

    write_text(cv_md, cv_md_text)
    write_text(letter_md, letter_md_text)
    write_text(questions_md_path, questions_md_text)
    write_text(pack_md_path, pack_md_text)

    cv_html_text = cv_html(company, role_title, fit, cv_md_text)
    letter_html_text = letter_html(company, role_title, fit, letter_md_text)
    questions_html_text = questions_html(company, role_title, fit, questions_md_text)
    pack_html_text = pack_html(company, role_title, fit)

    write_text(cv_html_path, cv_html_text)
    write_text(letter_html_path, letter_html_text)
    write_text(questions_html_path, questions_html_text)
    write_text(pack_html_path, pack_html_text)

    render_pdf(cv_html_path, cv_pdf)
    render_pdf(letter_html_path, letter_pdf)
    render_pdf(questions_html_path, questions_pdf)
    render_pdf(pack_html_path, pack_pdf)

    telegram_text = '\n'.join([
        'Job pipeline run complete.',
        '',
        f'- {company} | {role_title}',
        f'  Score: {fit.score}',
        f'  Verdict: {fit.verdict}',
        f'  Pack: {pack_dir}',
        '',
        'Top matches:',
        f'  - {fit.strongest_matches[0]}',
        f'  - {fit.strongest_matches[1] if len(fit.strongest_matches) > 1 else fit.strongest_matches[0]}',
        '',
        'Top gap:',
        f'  - {fit.major_gaps[0]}',
    ])
    write_text(telegram_summary, telegram_text)

    artifacts.tailored_cv_md = cv_md
    artifacts.tailored_cv_html = cv_html_path
    artifacts.tailored_cv_pdf = cv_pdf
    artifacts.cover_letter_md = letter_md
    artifacts.cover_letter_html = letter_html_path
    artifacts.cover_letter_pdf = letter_pdf
    artifacts.questions_md = questions_md_path
    artifacts.questions_html = questions_html_path
    artifacts.questions_pdf = questions_pdf
    artifacts.pack_md = pack_md_path
    artifacts.pack_html = pack_html_path
    artifacts.pack_pdf = pack_pdf
    artifacts.telegram_summary = telegram_summary
    return artifacts


def update_intake(job_path: Path, job: dict[str, Any], fit: FitResult, artifacts: PackArtifacts, email_status: dict[str, Any] | None = None) -> None:
    job['status'] = fit.decision
    job['processed_at'] = now_iso()
    job['fit_score'] = fit.score
    job['fit_verdict'] = fit.verdict
    job['fit_report_path'] = str(artifacts.fit_report)
    if artifacts.pack_dir:
        job['pack_dir'] = str(artifacts.pack_dir)
    if email_status is not None:
        job['email_delivery'] = email_status
    save_json(job_path, job)


def process_all() -> dict[str, Any]:
    profile = load_json(PROFILE_PATH)
    pending_files = [p for p in sorted(INTAKE_DIR.glob('*.json')) if load_json(p).get('status') == 'pending']
    manifest: dict[str, Any] = {
        'started_at': now_iso(),
        'profile_path': str(PROFILE_PATH),
        'processed_count': 0,
        'results': [],
    }

    for job_path in pending_files:
        job = load_json(job_path)
        fit = compute_fit(job, profile)
        artifacts = create_pack(job, fit)

        email_status = None
        if fit.score >= 80 and artifacts.tailored_cv_pdf and artifacts.cover_letter_pdf and artifacts.questions_pdf:
            subject = f'Job Fit: {fit.score}% - {cleaned_title(job)} at {infer_company_name(job)}'
            body = '\n'.join([
                f'{cleaned_title(job)} at {infer_company_name(job)}',
                '',
                f'Fit score: {fit.score}%',
                f'Verdict: {fit.verdict}',
                '',
                'Strongest matches:',
                *[f'- {item}' for item in fit.strongest_matches],
                '',
                'Major gaps:',
                *[f'- {item}' for item in fit.major_gaps],
                '',
                f'Sponsorship risk: {fit.sponsorship_risk}',
                f'Application link: {job.get("source_url") or ""}',
            ])
            ok, info = send_email(subject, body, [artifacts.tailored_cv_pdf, artifacts.cover_letter_pdf, artifacts.questions_pdf])
            email_status = {'sent': ok, 'info': info, 'subject': subject}

        update_intake(job_path, job, fit, artifacts, email_status)

        manifest['results'].append({
            'file': job_path.name,
            'company': infer_company_name(job),
            'team': team_name(job),
            'title': cleaned_title(job),
            'score': fit.score,
            'verdict': fit.verdict,
            'decision': fit.decision,
            'fit_report_path': str(artifacts.fit_report),
            'pack_dir': str(artifacts.pack_dir),
            'telegram_summary_path': str(artifacts.telegram_summary) if artifacts.telegram_summary else None,
            'email_delivery': email_status,
            'application_url': job.get('source_url') or '',
        })

    manifest['processed_count'] = len(manifest['results'])
    manifest['finished_at'] = now_iso()
    save_json(MANIFEST_PATH, manifest)
    return manifest


if __name__ == '__main__':
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    result = process_all()
    print(json.dumps(result, indent=2, ensure_ascii=False))
