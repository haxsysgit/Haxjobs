from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.analysis import DEFAULT_MODE, DemoFixtureOption, DemoOptionsResponse
from app.services.documents import extract_text_from_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CV_FIXTURE_DIR = PROJECT_ROOT / "tests" / "cv"
JD_FIXTURE_DIR = PROJECT_ROOT / "tests" / "jd"


@dataclass(frozen=True)
class DemoFixture:
    id: str
    label: str
    path: Path


class InvalidDemoFixtureError(ValueError):
    """Raised when a requested demo fixture is not in the approved whitelist."""


_CV_FIXTURES = {
    "Arinze_Agent_engineer_cv.pdf": DemoFixture(
        id="Arinze_Agent_engineer_cv.pdf",
        label="Agent Engineer CV",
        path=CV_FIXTURE_DIR / "Arinze_Agent_engineer_cv.pdf",
    ),
    "Arinze_Resume_010426.pdf": DemoFixture(
        id="Arinze_Resume_010426.pdf",
        label="General Resume CV",
        path=CV_FIXTURE_DIR / "Arinze_Resume_010426.pdf",
    ),
    "Arinze_intern_cv.pdf": DemoFixture(
        id="Arinze_intern_cv.pdf",
        label="Intern CV",
        path=CV_FIXTURE_DIR / "Arinze_intern_cv.pdf",
    ),
}
_JD_FIXTURES = {
    "60x.txt": DemoFixture(
        id="60x.txt",
        label="60x Agent Engineer JD",
        path=JD_FIXTURE_DIR / "60x.txt",
    ),
    "cobaltsky.txt": DemoFixture(
        id="cobaltsky.txt",
        label="Cobalt Sky JD",
        path=JD_FIXTURE_DIR / "cobaltsky.txt",
    ),
    "endava.txt": DemoFixture(
        id="endava.txt",
        label="Endava JD",
        path=JD_FIXTURE_DIR / "endava.txt",
    ),
}

DEFAULT_CV_FIXTURE = "Arinze_Agent_engineer_cv.pdf"
DEFAULT_JD_FIXTURE = "60x.txt"


def get_demo_options() -> DemoOptionsResponse:
    return DemoOptionsResponse(
        cv_fixtures=[_to_option(item) for item in _CV_FIXTURES.values()],
        jd_fixtures=[_to_option(item) for item in _JD_FIXTURES.values()],
        default_cv_fixture=DEFAULT_CV_FIXTURE,
        default_jd_fixture=DEFAULT_JD_FIXTURE,
        modes=["safe", "stretch", "interview", "ideal"],
    )


def load_demo_texts(
    cv_fixture_id: str = DEFAULT_CV_FIXTURE,
    jd_fixture_id: str = DEFAULT_JD_FIXTURE,
) -> tuple[str, str, str, str]:
    cv_fixture = _CV_FIXTURES.get(cv_fixture_id)
    jd_fixture = _JD_FIXTURES.get(jd_fixture_id)
    if cv_fixture is None:
        raise InvalidDemoFixtureError(f"Unknown demo CV fixture: {cv_fixture_id}")
    if jd_fixture is None:
        raise InvalidDemoFixtureError(f"Unknown demo JD fixture: {jd_fixture_id}")
    cv_text = extract_text_from_path(cv_fixture.path)
    jd_text = jd_fixture.path.read_text(encoding="utf-8")
    return cv_text, jd_text, cv_fixture.label, jd_fixture.label


def _to_option(fixture: DemoFixture) -> DemoFixtureOption:
    return DemoFixtureOption(id=fixture.id, label=fixture.label)
