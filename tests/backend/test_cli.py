from pathlib import Path

from app.cli import main


def test_cli_writes_expected_output_files(tmp_path, monkeypatch) -> None:
    cv_path = tmp_path / "sample_cv.txt"
    cv_path.write_text(
        "\n".join(
            [
                "PROFESSIONAL SUMMARY",
                "Python backend engineer with FastAPI and workflow automation experience.",
                "",
                "CORE SKILLS",
                "Languages: Python, TypeScript",
                "Frameworks: FastAPI, Vue",
                "",
                "PROFESSIONAL EXPERIENCE",
                "Backend Engineer",
                "- Built API workflows and internal tooling.",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    exit_code = main(
        [
            "analyze",
            "--cv",
            str(cv_path),
            "--jd-text",
            "Backend Engineer\nThe Role\nStrong Python fundamentals\nProduction API delivery\nVue exposure",
            "--mode",
            "stretch",
        ]
    )
    assert exit_code == 0
    for path in (
        "outputs/analysis.json",
        "outputs/analysis.md",
        "outputs/tailored_cv.md",
        "outputs/cover_letter.md",
        "outputs/application_notes.md",
        "outputs/application_pack.json",
    ):
        assert Path(path).exists(), f"expected {path} to be written"
