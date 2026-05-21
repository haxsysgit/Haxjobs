from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.models.analysis import AnalyzeResponse, EvidenceItem
from app.models.profile import (
    CandidateProfile,
    ProfileDocument,
    ProfileExportBundle,
    ProfileFact,
    ProfileJobRecord,
    ProfileSurveyResponse,
    SaveSurveyResponseRequest,
)
from app.services.analysis import build_candidate_evidence, parse_cv
from app.services.surveys import compose_follow_up_answer


def load_or_create_profile(path: Path) -> CandidateProfile:
    if path.exists():
        profile = CandidateProfile.model_validate_json(path.read_text(encoding="utf-8"))
        _hydrate_document_text(profile, path)
        return profile
    created_at = _timestamp()
    return CandidateProfile(
        created_at=created_at,
        updated_at=created_at,
        summary="Upload CVs to build a reusable local profile.",
    )


def save_profile(path: Path, profile: CandidateProfile) -> CandidateProfile:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_document_text(profile, path)
    profile.updated_at = _timestamp()
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return profile


def import_cv_documents(
    profile: CandidateProfile,
    documents: list[tuple[str, str]],
) -> CandidateProfile:
    for label, text in documents:
        parsed = parse_cv(text)
        evidence = build_candidate_evidence(text)
        document = ProfileDocument(
            id=_document_id(label, text),
            label=label,
            kind="cv",
            added_at=_timestamp(),
            summary=_cv_summary(parsed),
            skills=_top_items(parsed["skills"]),
            text=text,
        )
        profile.cv_documents = [item for item in profile.cv_documents if item.id != document.id]
        profile.cv_documents.insert(0, document)
        _merge_evidence(profile, evidence, label)
    _refresh_profile_summary(profile)
    return profile


def record_analysis(
    profile: CandidateProfile,
    analysis: AnalyzeResponse,
) -> CandidateProfile:
    record = ProfileJobRecord(
        id=_job_id(analysis.metadata.jd_label, analysis.jd_analysis.role_title),
        role_title=analysis.jd_analysis.role_title,
        jd_label=analysis.metadata.jd_label,
        mode=analysis.metadata.mode,
        fit_score=analysis.fit_summary.score,
        matched_requirements=analysis.fit_summary.matched_requirements,
        total_requirements=analysis.fit_summary.total_requirements,
        added_at=_timestamp(),
        focus_skills=_top_items(
            analysis.jd_analysis.required_skills + analysis.jd_analysis.desirable_skills,
            limit=6,
        ),
    )
    profile.jd_history.insert(0, record)
    profile.jd_history = profile.jd_history[:20]
    _merge_evidence(profile, analysis.candidate_evidence, analysis.metadata.cv_label)
    _refresh_profile_summary(profile)
    return profile


def save_survey_response(
    profile: CandidateProfile,
    payload: SaveSurveyResponseRequest,
) -> CandidateProfile:
    response = ProfileSurveyResponse(
        question_key=f"{payload.job_id}:{payload.requirement_id}",
        job_id=payload.job_id,
        requirement_id=payload.requirement_id,
        requirement_text=payload.requirement_text,
        choice_id=payload.choice_id,
        choice_label=payload.choice_label,
        notes=payload.notes.strip(),
        updated_at=_timestamp(),
    )
    profile.survey_responses = [
        item for item in profile.survey_responses if item.question_key != response.question_key
    ]
    profile.survey_responses.insert(0, response)
    profile.survey_responses = profile.survey_responses[:200]
    profile.updated_at = _timestamp()
    return profile


def export_profile_bundle(profile: CandidateProfile) -> ProfileExportBundle:
    documents = {
        document.id: document.text
        for document in profile.cv_documents
        if document.text is not None
    }
    return ProfileExportBundle(profile=profile, documents=documents)


def import_profile_bundle(bundle: ProfileExportBundle) -> CandidateProfile:
    profile = bundle.profile.model_copy(deep=True)
    for document in profile.cv_documents:
        document.text = bundle.documents.get(document.id)
    _refresh_profile_summary(profile)
    return profile


def build_follow_up_answer_map(profile: CandidateProfile, job_id: str) -> dict[str, str]:
    answer_map: dict[str, str] = {}
    for item in profile.survey_responses:
        if item.job_id != job_id:
            continue
        answer_map[item.requirement_id] = compose_follow_up_answer(item.choice_label, item.notes)
    return answer_map


def get_cv_text(profile: CandidateProfile, cv_document_id: str) -> str:
    for document in profile.cv_documents:
        if document.id == cv_document_id and document.text:
            return document.text
    raise KeyError(cv_document_id)


def _hydrate_document_text(profile: CandidateProfile, path: Path) -> None:
    documents_dir = _documents_dir(path)
    for document in profile.cv_documents:
        raw_path = documents_dir / f"{document.id}.txt"
        if raw_path.exists():
            document.text = raw_path.read_text(encoding="utf-8")


def _write_document_text(profile: CandidateProfile, path: Path) -> None:
    documents_dir = _documents_dir(path)
    documents_dir.mkdir(parents=True, exist_ok=True)
    live_ids = {document.id for document in profile.cv_documents}
    for raw_path in documents_dir.glob("*.txt"):
        if raw_path.stem not in live_ids:
            raw_path.unlink()
    for document in profile.cv_documents:
        if document.text is not None:
            (documents_dir / f"{document.id}.txt").write_text(document.text, encoding="utf-8")


def _merge_evidence(profile: CandidateProfile, evidence: list[EvidenceItem], source_label: str) -> None:
    merged = {fact.id: fact for fact in profile.evidence_library}
    for item in evidence:
        fact = ProfileFact(
            id=_fact_id(source_label, item.evidence),
            category=item.category,
            text=item.evidence,
            source_label=source_label,
        )
        merged[fact.id] = fact
    profile.evidence_library = list(merged.values())[:120]


def _refresh_profile_summary(profile: CandidateProfile) -> None:
    skills_counter = Counter()
    for document in profile.cv_documents:
        skills_counter.update(document.skills)
    profile.top_skills = [item for item, _ in skills_counter.most_common(8)]
    if not profile.cv_documents:
        profile.summary = "Upload CVs to build a reusable local profile."
        return
    headline = ", ".join(profile.top_skills[:4]) or "general experience"
    profile.summary = (
        f"Profile built from {len(profile.cv_documents)} CV source(s), "
        f"{len(profile.evidence_library)} saved evidence note(s), and "
        f"{len(profile.jd_history)} tracked job brief(s). Strongest signals: {headline}."
    )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _document_id(label: str, text: str) -> str:
    digest = hashlib.sha1(f"{label}:{text}".encode("utf-8")).hexdigest()[:10]
    slug = "".join(char.lower() if char.isalnum() else "-" for char in label).strip("-")
    return f"cv-{slug[:24]}-{digest}"


def _job_id(jd_label: str, role_title: str) -> str:
    digest = hashlib.sha1(f"{jd_label}:{role_title}:{_timestamp()}".encode("utf-8")).hexdigest()[:10]
    return f"job-{digest}"


def _fact_id(source_label: str, evidence: str) -> str:
    digest = hashlib.sha1(f"{source_label}:{evidence}".encode("utf-8")).hexdigest()[:12]
    return f"fact-{digest}"


def _cv_summary(parsed: dict[str, list[str] | str]) -> str:
    summary = parsed["summary"]
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    skills = parsed["skills"]
    if isinstance(skills, list) and skills:
        return f"Skills focus: {', '.join(skills[:5])}"
    return "Imported CV with reusable profile evidence."


def _top_items(values: list[str] | str, limit: int = 8) -> list[str]:
    if isinstance(values, str):
        return [values][:limit]
    seen: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen[:limit]


def _documents_dir(path: Path) -> Path:
    return path.parent / "documents"
