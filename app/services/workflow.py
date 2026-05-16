from __future__ import annotations

from app.models.analysis import AnalysisMetadata, AnalysisMode, AnalysisReport
from app.services.analysis import analyze_texts
from app.services.demo_fixtures import load_demo_texts
from app.services.reporting import response_from_report


def analyze(cv_text: str, jd_text: str, mode: AnalysisMode = "stretch") -> AnalysisReport:
    """Shared deterministic workflow used by both the CLI and API."""
    del mode
    return analyze_texts(cv_text=cv_text, jd_text=jd_text)


def analyze_upload(cv_text: str, jd_text: str, mode: AnalysisMode, cv_label: str):
    report = analyze(cv_text=cv_text, jd_text=jd_text, mode=mode)
    return response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode=mode,
            source="upload",
            cv_label=cv_label,
            jd_label="Pasted Job Description",
        ),
    )


def analyze_demo(cv_fixture_id: str, jd_fixture_id: str, mode: AnalysisMode):
    cv_text, jd_text, cv_label, jd_label = load_demo_texts(cv_fixture_id, jd_fixture_id)
    report = analyze(cv_text=cv_text, jd_text=jd_text, mode=mode)
    return response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode=mode,
            source="demo",
            cv_label=cv_label,
            jd_label=jd_label,
        ),
    )
