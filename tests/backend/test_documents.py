from pathlib import Path

from app.services.documents import extract_text_from_path


def test_pdf_cv_fixture_parses_successfully() -> None:
    text = extract_text_from_path("tests/cv/Arinze_Agent_engineer_cv.pdf")
    assert "Python Backend Engineer" in text
    assert "Haxaml" in text


def test_txt_cv_input_parses_successfully(tmp_path: Path) -> None:
    cv_path = tmp_path / "sample_cv.txt"
    cv_path.write_text(
        "PROFESSIONAL SUMMARY\nPython engineer with API and automation experience.\n",
        encoding="utf-8",
    )
    text = extract_text_from_path(cv_path)
    assert "Python engineer" in text

