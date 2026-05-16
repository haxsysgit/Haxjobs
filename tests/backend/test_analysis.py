from pathlib import Path

from app.services.analysis import parse_jd
from app.services.documents import extract_text_from_path
from app.services.reporting import generate_markdown_report
from app.services.workflow import analyze


def test_jd_parser_extracts_requirement_bullets_from_fixture() -> None:
    jd_text = Path("tests/jd/60x.txt").read_text(encoding="utf-8")
    jd_analysis = parse_jd(jd_text)
    assert jd_analysis.role_title
    assert jd_analysis.requirements
    assert any("python" in " ".join(req.keywords) for req in jd_analysis.requirements)


def test_analyze_returns_expected_sections_for_real_fixtures() -> None:
    cv_text = extract_text_from_path("tests/cv/Arinze_Agent_engineer_cv.pdf")
    jd_text = Path("tests/jd/60x.txt").read_text(encoding="utf-8")
    report = analyze(cv_text=cv_text, jd_text=jd_text)
    assert report.jd_analysis.requirements
    assert report.candidate_evidence
    assert report.evidence_map
    assert report.follow_up_questions
    assert any(match.match_label == "Gap" for match in report.evidence_map)


def test_markdown_report_contains_required_sections() -> None:
    cv_text = extract_text_from_path("tests/cv/Arinze_Agent_engineer_cv.pdf")
    jd_text = Path("tests/jd/60x.txt").read_text(encoding="utf-8")
    report = analyze(cv_text=cv_text, jd_text=jd_text)
    markdown = generate_markdown_report(report)
    for section in (
        "# Fit Summary",
        "# JD Analysis",
        "# Candidate Evidence",
        "# Evidence Map",
        "# Gaps and Warnings",
        "# Follow-up Questions",
    ):
        assert section in markdown

