from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from app.models.analysis import (
    AnalysisReport,
    EvidenceItem,
    EvidenceMatch,
    FitSummary,
    FollowUpQuestion,
    JDAnalysis,
    JDRequirement,
)

KNOWN_CV_HEADINGS = {
    "professional summary",
    "core skills",
    "professional experience",
    "projects",
    "education",
    "additional information",
}
KNOWN_JD_HEADINGS = {
    "what we're building",
    "the role",
    "our stack",
    "beyond the role",
    "the lifestyle",
    "what we're looking for",
    "you do not need",
}
TECH_TERMS = {
    "fastapi",
    "python",
    "pydantic",
    "typescript",
    "javascript",
    "next.js",
    "react",
    "vue",
    "tailwind",
    "sqlalchemy",
    "alembic",
    "postgres",
    "postgresql",
    "mysql",
    "sqlite",
    "docker",
    "vercel",
    "gcp",
    "gke",
    "cloud",
    "api",
    "apis",
    "rest",
    "llm",
    "openai",
    "langgraph",
    "mcp",
    "graph",
    "apache age",
    "alloydb",
    "vertex ai",
    "gemini",
    "claude",
    "testing",
    "eval",
    "validation",
    "reporting",
    "deployment",
    "workflows",
    "automation",
    "frontend",
    "backend",
}
STOPWORDS = {
    "about",
    "above",
    "across",
    "agent",
    "agents",
    "already",
    "also",
    "around",
    "because",
    "being",
    "between",
    "built",
    "clear",
    "client",
    "could",
    "daily",
    "data",
    "default",
    "directly",
    "drive",
    "each",
    "expect",
    "experience",
    "focus",
    "from",
    "have",
    "into",
    "just",
    "keep",
    "layer",
    "like",
    "make",
    "more",
    "need",
    "next",
    "only",
    "other",
    "over",
    "part",
    "real",
    "role",
    "same",
    "ship",
    "should",
    "small",
    "some",
    "team",
    "that",
    "their",
    "them",
    "they",
    "this",
    "through",
    "used",
    "user",
    "using",
    "want",
    "what",
    "where",
    "with",
    "work",
    "would",
    "write",
    "years",
    "your",
}
CATEGORY_KEYWORDS = {
    "Python": {"python", "django", "fastapi", "sqlalchemy", "alembic"},
    "APIs": {"api", "apis", "rest", "backend", "service", "services"},
    "AI Workflows": {
        "ai",
        "llm",
        "openai",
        "langgraph",
        "mcp",
        "prompt",
        "agentic",
        "agents",
        "vertex ai",
        "gemini",
        "claude",
    },
    "Frontend": {"typescript", "javascript", "next.js", "react", "vue", "tailwind", "frontend"},
    "Data": {"postgres", "postgresql", "mysql", "sqlite", "graph", "apache age", "alloydb"},
    "Cloud": {"cloud", "gcp", "gke", "vercel", "deployment", "docker"},
    "Testing": {"testing", "test", "validation", "quality", "eval", "logging"},
    "Stakeholders": {"stakeholder", "users", "client", "communication", "push", "temperament"},
}
SOFT_SKILL_HINTS = (
    "push back",
    "code quality",
    "agent-native",
    "taste and temperament",
    "comfort",
    "pairing",
    "stakeholder",
    "team",
)
MATCH_SCORES = {
    "Strong Match": 1.0,
    "Partial Match": 0.7,
    "Transferable Match": 0.5,
    "Weak Match": 0.25,
    "Gap": 0.0,
}


def parse_jd(jd_text: str) -> JDAnalysis:
    lines = [line.strip() for line in jd_text.splitlines()]
    sections = _split_sections(lines, KNOWN_JD_HEADINGS)
    role_title = _extract_role_title(jd_text)
    requirements: list[JDRequirement] = []
    requirement_sections = {"The Role", "Our Stack", "What We're Looking For", "You Do Not Need"}
    for section, body_lines in sections.items():
        if section not in requirement_sections:
            continue
        requirements.extend(_requirements_from_section(section, body_lines, len(requirements) + 1))
    recruiter_concerns = _collect_recruiter_concerns(jd_text)
    required_skills = _collect_skill_terms(
        requirement for requirement in requirements if requirement.importance == "required"
    )
    desirable_skills = _collect_skill_terms(
        requirement for requirement in requirements if requirement.importance == "nice_to_have"
    )
    return JDAnalysis(
        role_title=role_title or "Unspecified Role",
        section_titles=list(sections.keys()),
        requirements=requirements,
        recruiter_concerns=recruiter_concerns,
        required_skills=required_skills,
        desirable_skills=desirable_skills,
    )


def parse_cv(cv_text: str) -> dict[str, list[str] | str]:
    lines = [line.rstrip() for line in cv_text.splitlines()]
    sections = _split_sections(lines, KNOWN_CV_HEADINGS)
    summary = "\n".join(sections.get("Professional Summary", [])).strip()
    skills = _extract_skill_entries(sections.get("Core Skills", []))
    experience_bullets = _extract_bullets(sections.get("Professional Experience", []))
    project_bullets = _extract_bullets(sections.get("Projects", []))
    education = [line for line in sections.get("Education", []) if line.strip()]
    additional = [line for line in sections.get("Additional Information", []) if line.strip()]
    return {
        "summary": summary,
        "skills": skills,
        "experience_bullets": experience_bullets,
        "project_bullets": project_bullets,
        "education": education,
        "additional_information": additional,
    }


def build_candidate_evidence(cv_text: str) -> list[EvidenceItem]:
    parsed = parse_cv(cv_text)
    evidence: list[EvidenceItem] = []
    counter = 1

    def add_items(values: Iterable[str], section: str) -> None:
        nonlocal counter
        for value in values:
            text = value.strip()
            if not text:
                continue
            evidence.append(
                EvidenceItem(
                    id=f"ev-{counter}",
                    category=_categorize_text(text),
                    source_section=section,
                    evidence=text,
                    keywords=_extract_keywords(text),
                )
            )
            counter += 1

    summary = parsed["summary"]
    if isinstance(summary, str) and summary:
        add_items([summary], "Professional Summary")
    add_items(parsed["skills"], "Core Skills")
    add_items(parsed["experience_bullets"], "Professional Experience")
    add_items(parsed["project_bullets"], "Projects")
    add_items(parsed["education"], "Education")
    add_items(parsed["additional_information"], "Additional Information")
    return evidence


def build_evidence_map(
    requirements: list[JDRequirement], evidence_items: list[EvidenceItem]
) -> list[EvidenceMatch]:
    matches: list[EvidenceMatch] = []
    for requirement in requirements:
        scored = []
        for item in evidence_items:
            score = _score_requirement_match(requirement, item)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        top_items = [item for _, item in scored[:2]]
        top_score = scored[0][0] if scored else 0.0
        match_label = _match_label_from_score(top_score)
        claim_label = _claim_label_from_match(match_label, top_items)
        supporting = [item.evidence for item in top_items]
        matches.append(
            EvidenceMatch(
                requirement_id=requirement.id,
                requirement_text=requirement.text,
                section=requirement.section,
                importance=requirement.importance,
                match_label=match_label,
                claim_label=claim_label,
                supporting_evidence=supporting,
                suggested_safe_wording=_suggest_safe_wording(requirement, match_label, supporting),
                risk_warning=_build_risk_warning(requirement, match_label, claim_label),
            )
        )
    return matches


def build_follow_up_questions(evidence_map: list[EvidenceMatch]) -> list[FollowUpQuestion]:
    questions: list[FollowUpQuestion] = []
    for match in evidence_map:
        if match.match_label == "Strong Match" and match.claim_label == "Confirmed":
            continue
        priority = "high" if match.importance == "required" else "medium"
        if match.match_label == "Gap":
            question = f"What real example can you offer for '{match.requirement_text}' without overstating your experience?"
            reason = "The job description asks for this, but the current CV does not show defensible evidence."
        elif match.match_label == "Weak Match":
            question = f"Can you point to a concrete project, coursework, or shipped feature tied to '{match.requirement_text}'?"
            reason = "There is only a weak signal in the CV, so the claim needs a clearer example."
        else:
            question = f"What extra detail would make your experience with '{match.requirement_text}' interview-defensible?"
            reason = "The current evidence is promising but still partial or inferred."
        questions.append(
            FollowUpQuestion(
                requirement_id=match.requirement_id,
                requirement_text=match.requirement_text,
                question=question,
                reason=reason,
                priority=priority,
            )
        )
    return questions


def compute_fit_summary(evidence_map: list[EvidenceMatch]) -> FitSummary:
    if not evidence_map:
        return FitSummary(
            score=0,
            label="Low Fit",
            matched_requirements=0,
            total_requirements=0,
            summary="No requirements were extracted from the job description.",
        )
    weighted_total = 0.0
    weighted_score = 0.0
    matched = 0
    for match in evidence_map:
        weight = 2.0 if match.importance == "required" else 1.0
        weighted_total += weight
        weighted_score += MATCH_SCORES[match.match_label] * weight
        if match.match_label != "Gap":
            matched += 1
    score = round((weighted_score / weighted_total) * 100)
    if score >= 75:
        label = "Strong Fit"
    elif score >= 55:
        label = "Moderate Fit"
    elif score >= 35:
        label = "Developing Fit"
    else:
        label = "Low Fit"
    summary = (
        f"The CV shows defensible evidence for {matched} of {len(evidence_map)} extracted requirements. "
        f"The strongest signals cluster around confirmed backend, API, and agent workflow work, while weaker areas need tighter examples or explicit gap handling."
    )
    return FitSummary(
        score=score,
        label=label,
        matched_requirements=matched,
        total_requirements=len(evidence_map),
        summary=summary,
    )


def build_warnings(evidence_map: list[EvidenceMatch]) -> list[str]:
    gaps = [match for match in evidence_map if match.match_label == "Gap"]
    unsafe = [match for match in evidence_map if match.claim_label == "Unsafe Claim"]
    needs_confirmation = [
        match for match in evidence_map if match.claim_label == "Needs User Confirmation"
    ]
    warnings: list[str] = []
    if gaps:
        warnings.append(
            f"{len(gaps)} requirement(s) are direct gaps and should not be presented as existing experience."
        )
    if unsafe:
        warnings.append(
            f"{len(unsafe)} requirement(s) would become unsafe claims if written as direct experience without new evidence."
        )
    if needs_confirmation:
        warnings.append(
            f"{len(needs_confirmation)} requirement(s) need concrete examples before they should appear in tailored application material."
        )
    if not warnings:
        warnings.append("No high-risk claim warnings were generated from this deterministic pass.")
    return warnings


def analyze_texts(cv_text: str, jd_text: str) -> AnalysisReport:
    jd_analysis = parse_jd(jd_text)
    candidate_evidence = build_candidate_evidence(cv_text)
    evidence_map = build_evidence_map(jd_analysis.requirements, candidate_evidence)
    follow_up_questions = build_follow_up_questions(evidence_map)
    fit_summary = compute_fit_summary(evidence_map)
    warnings = build_warnings(evidence_map)
    return AnalysisReport(
        fit_summary=fit_summary,
        jd_analysis=jd_analysis,
        candidate_evidence=candidate_evidence,
        evidence_map=evidence_map,
        follow_up_questions=follow_up_questions,
        warnings=warnings,
    )


def _split_sections(lines: list[str], known_headings: set[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "General"
    sections[current] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            sections[current].append("")
            continue
        lowered = line.lower()
        if lowered in known_headings:
            current = _display_heading(line)
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {name: content for name, content in sections.items() if any(item.strip() for item in content)}


def _extract_skill_entries(lines: list[str]) -> list[str]:
    entries: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        if ":" in line:
            heading, remainder = line.split(":", 1)
            parts = [item.strip() for item in remainder.split(",") if item.strip()]
            for part in parts:
                entries.append(f"{heading.strip()}: {part}")
        else:
            entries.append(line.strip())
    return entries


def _extract_bullets(lines: list[str]) -> list[str]:
    bullets: list[str] = []
    current_heading = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _looks_like_resume_heading(stripped):
            current_heading = stripped
            continue
        if current_heading:
            bullets.append(f"{current_heading}: {stripped}")
        else:
            bullets.append(stripped)
    return bullets


def _looks_like_resume_heading(line: str) -> bool:
    return bool(
        re.search(r"\b(Engineer|Manager|University|Diploma|Haxaml|Pharmax|Autopahe|Basket)\b", line)
        and len(line.split()) <= 12
        and ":" not in line
    )


def _requirements_from_section(section: str, lines: list[str], start_index: int) -> list[JDRequirement]:
    text = "\n".join(lines)
    raw_candidates: list[str] = []
    for block in re.split(r"\n{2,}", text):
        stripped_block = " ".join(block.split())
        if not stripped_block:
            continue
        if "\n" in block:
            block_lines = [line.strip(" -\t") for line in block.splitlines() if line.strip()]
        else:
            block_lines = [stripped_block]
        for candidate in block_lines:
            raw_candidates.extend(_split_requirement_candidate(section, candidate))
    importance = "nice_to_have" if section.lower() == "you do not need" else "required"
    requirements: list[JDRequirement] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        normalized = candidate.strip().strip(".")
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        requirement = JDRequirement(
            id=f"req-{start_index + len(requirements)}",
            text=normalized,
            section=section,
            importance=importance if not _is_optional_requirement(normalized) else "nice_to_have",
            category=_categorize_text(normalized),
            keywords=_extract_keywords(normalized),
        )
        requirements.append(requirement)
    return requirements


def _split_requirement_candidate(section: str, candidate: str) -> list[str]:
    cleaned = " ".join(candidate.split())
    if not cleaned:
        return []
    if section.lower() in {"our stack", "what we're looking for", "you do not need"}:
        return [cleaned]
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    extracted = []
    for sentence in sentences:
        compact = sentence.strip().strip("•")
        if not compact:
            continue
        if len(compact.split()) <= 4 and section.lower() not in {"our stack", "what we're looking for"}:
            continue
        extracted.append(compact.rstrip("."))
    return extracted or [cleaned]


def _extract_role_title(jd_text: str) -> str:
    match = re.search(
        r"\b(?:our|a|an|the)\s+([A-Za-z][A-Za-z /\-]+?(?:engineer|developer|manager|analyst|designer))\b",
        jd_text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).title()
    first_line = next((line.strip() for line in jd_text.splitlines() if line.strip()), "")
    return first_line


def _display_heading(line: str) -> str:
    words = [word.capitalize() if word.lower() != "we're" else "We're" for word in line.lower().split()]
    return " ".join(words)


def _collect_recruiter_concerns(jd_text: str) -> list[str]:
    lowered = jd_text.lower()
    concerns = [hint for hint in SOFT_SKILL_HINTS if hint in lowered]
    return [concern.title() for concern in concerns]


def _collect_skill_terms(requirements: Iterable[JDRequirement]) -> list[str]:
    counter: Counter[str] = Counter()
    for requirement in requirements:
        for keyword in requirement.keywords:
            if keyword in TECH_TERMS:
                counter[keyword] += 1
    return [term for term, _ in counter.most_common(8)]


def _extract_keywords(text: str) -> list[str]:
    lowered = text.lower()
    keywords = {term for term in TECH_TERMS if term in lowered}
    tokens = re.findall(r"[a-zA-Z0-9.+#]+", lowered)
    for token in tokens:
        if token in STOPWORDS:
            continue
        if len(token) >= 4 or token in {"api", "sql", "gcp"}:
            keywords.add(token)
    return sorted(keywords)


def _categorize_text(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "General"


def _score_requirement_match(requirement: JDRequirement, item: EvidenceItem) -> float:
    shared_keywords = set(requirement.keywords) & set(item.keywords)
    score = min(0.9, 0.25 * len(shared_keywords))
    if requirement.category == item.category and requirement.category != "General":
        score += 0.25
    if requirement.category == "Python" and item.category == "APIs":
        score += 0.2
    if requirement.category == "APIs" and item.category == "Python":
        score += 0.15
    if requirement.category == "AI Workflows" and item.category == "Python":
        score += 0.1
    if requirement.category == "Stakeholders" and "users" in item.evidence.lower():
        score += 0.2
    if not shared_keywords:
        for keyword in requirement.keywords:
            if keyword and keyword in item.evidence.lower():
                score += 0.15
                break
    return min(score, 1.0)


def _match_label_from_score(score: float) -> str:
    if score >= 0.9:
        return "Strong Match"
    if score >= 0.65:
        return "Partial Match"
    if score >= 0.45:
        return "Transferable Match"
    if score >= 0.2:
        return "Weak Match"
    return "Gap"


def _claim_label_from_match(match_label: str, items: list[EvidenceItem]) -> str:
    if match_label == "Strong Match":
        return "Confirmed"
    if match_label == "Partial Match":
        return "Confirmed" if any(item.source_section == "Core Skills" for item in items) else "Inferred"
    if match_label == "Transferable Match":
        return "Stretch Wording"
    if match_label == "Weak Match":
        return "Needs User Confirmation"
    return "Unsafe Claim"


def _suggest_safe_wording(
    requirement: JDRequirement, match_label: str, supporting: list[str]
) -> str:
    if supporting and match_label in {"Strong Match", "Partial Match"}:
        return f"Lead with the existing evidence and keep the wording concrete: {supporting[0]}"
    if supporting and match_label == "Transferable Match":
        return (
            "Use adjacent experience wording and avoid claiming direct ownership where the CV only shows a nearby signal: "
            f"{supporting[0]}"
        )
    if supporting and match_label == "Weak Match":
        return (
            "Only mention this if you can expand the example in interview, otherwise keep it framed as exposure rather than proof: "
            f"{supporting[0]}"
        )
    return f"Treat '{requirement.text}' as a gap until new evidence or a user-confirmed example exists."


def _build_risk_warning(requirement: JDRequirement, match_label: str, claim_label: str) -> str | None:
    if match_label == "Gap":
        return f"No direct CV evidence was found for this {requirement.importance} requirement."
    if claim_label == "Needs User Confirmation":
        return "The current CV signal is too weak to state as direct experience without a better example."
    if claim_label == "Stretch Wording":
        return "This can be positioned as adjacent experience, but not as a direct stack match."
    return None


def _is_optional_requirement(text: str) -> bool:
    lowered = text.lower()
    return "do not need" in lowered or "if you've never done this" in lowered or "interest in" in lowered
