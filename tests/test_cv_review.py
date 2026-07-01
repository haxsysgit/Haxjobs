"""Tests for CV review module — per-job CV improvement."""
import pytest
from haxjobs.evaluate.cv_review import (
    build_improved_cv,
    review_cv_for_job,
    extract_jd_requirements,
    inject_jd_keywords,
    JDRequirements,
)


def test_build_all_seven_variants():
    """Every role family generates a valid CV with role-appropriate metrics."""
    for role in [
        "backend_python", "ai_engineer_llm", "fullstack_python_react",
        "junior_software", "ai_automation_agents", "data_python", "platform_backend",
    ]:
        cv = build_improved_cv(role)
        assert len(cv) > 2000, f"{role}: CV too short"
        assert "Arinze Elenasulu" in cv
        assert "Vigilis" in cv
        assert "6,000" in cv, f"{role}: missing invoice volume metric"
        # Each role has at least one metric (70%, 60%, or invoice count)
        has_metric = "70%" in cv or "60%" in cv or "200+" in cv or "6,000" in cv
        assert has_metric, f"{role}: missing any metric"


def test_metrics_present_in_backend_cv():
    """Backend CV contains all key inferred metrics."""
    cv = build_improved_cv("backend_python")
    assert "200+ invoices/day" in cv
    assert "6,000+ invoices/month" in cv


def test_sole_developer_claim_present():
    """Every variant claims sole full-stack developer ownership."""
    cv = build_improved_cv("backend_python")
    assert "Sole" in cv and ("full-stack" in cv.lower() or "full stack" in cv.lower())


def test_ai_variant_has_ai_signals():
    """AI engineer variant mentions RAGAS and AI/LLM context."""
    cv = build_improved_cv("ai_engineer_llm")
    assert "RAGAS" in cv or "RAG" in cv
    assert "LLM" in cv


def test_junior_variant_has_learning_signal():
    """Junior variant emphasizes learning speed and full ownership."""
    cv = build_improved_cv("junior_software")
    assert "FastAPI" in cv  # still technical
    assert len(cv) > 3000


def test_variants_are_different():
    """Different role families produce different CVs (not carbon copies)."""
    cv_ai = build_improved_cv("ai_engineer_llm")
    cv_be = build_improved_cv("backend_python")
    # Should differ in at least one substantive way
    assert cv_ai != cv_be


def test_extract_jd_requirements_detects_ai():
    """JD keyword extraction detects AI engineer signals."""
    jd = "We need a Python engineer with LLM, RAG, LangChain, and HuggingFace experience."
    reqs = extract_jd_requirements(jd)
    assert reqs.role_type == "ai_engineer"


def test_extract_jd_requirements_detects_fullstack():
    """JD keyword extraction detects fullstack signals."""
    jd = "Looking for a full-stack developer with React, TypeScript, and Python FastAPI."
    reqs = extract_jd_requirements(jd)
    assert reqs.role_type == "fullstack"


def test_extract_jd_requirements_detects_seniority():
    """Seniority detection from JD text."""
    reqs = extract_jd_requirements("Senior Python Engineer with 5+ years")
    assert reqs.seniority == "senior"

    reqs = extract_jd_requirements("Mid-level Python Engineer")
    assert reqs.seniority == "mid"

    reqs = extract_jd_requirements("Python Engineer")
    assert reqs.seniority == "junior"


def test_keyword_injection_adds_missing():
    """JD keywords not in CV get injected into skills section."""
    cv = build_improved_cv("backend_python")
    reqs = JDRequirements(
        keywords=["Redis", "GraphQL", "NotInCV"],
        role_type="backend", seniority="mid",
        must_have=[], nice_to_have=[], raw_jd="",
    )
    injected = inject_jd_keywords(cv, reqs)
    assert len(injected) > len(cv)
    assert "Redis" in injected
    assert "GraphQL" in injected
    assert "NotInCV" in injected


def test_review_cv_for_job_end_to_end():
    """Full CV review pipeline works end-to-end."""
    jd = """
    We're looking for a Python Backend Engineer to join our platform team.
    Required: Python, FastAPI, PostgreSQL, Docker, Redis, AWS.
    Nice to have: Kubernetes, Terraform, CI/CD pipelines.
    """
    cv = review_cv_for_job("backend_python", jd)
    assert "Arinze Elenasulu" in cv
    assert "Vigilis" in cv
    assert "6,000" in cv
    # JD keywords should be in skills section
    assert "Redis" in cv


def test_visa_blurb_accurate():
    """Visa work authorization blurb is accurate and consistent."""
    cv = build_improved_cv("backend_python")
    assert "Graduate Route visa" in cv
    assert "no employer sponsorship required" in cv
    assert "full right to work" in cv
