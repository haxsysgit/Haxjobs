"""Validate CV source markdown against governance rules.

TDD: these tests define what a valid CV source must satisfy BEFORE the source exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


CV_SOURCE_DIR = Path(__file__).resolve().parent.parent / "cv_variants"
PROFILE_PATH = Path(__file__).resolve().parent.parent / "profile" / "arinze_profile.local.json"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_source(variant_id: str) -> str:
    path = CV_SOURCE_DIR / variant_id / "cv_source.md"
    if not path.exists():
        raise FileNotFoundError(f"CV source not found: {path}")
    return path.read_text()


def _locked_facts() -> dict:
    """Return the locked facts every CV source must include."""
    return {
        "name": "Arinze Elenasulu",
        "email": "elenasuluarinze@gmail.com",
        "linkedin": "linkedin.com/in/arinze-elenasulu",
        "university": "Middlesex University",
        "degree": "BSc Information Technology",
        "vigilis": "Vigilis",
        "aptech": "Aptech",
        "pharmax": "Pharmax",
        "python_since": "2020",
    }


def _forbidden_patterns() -> list[tuple[str, str]]:
    """Patterns that must NOT appear in any CV source.

    Returns list of (regex_pattern, human description).
    """
    return [
        (r"\bphone\b", "phone number mention"),
        (r"\bTailored\b", "Tailored naming (per-job artifact)"),
        (r"Claude Code", "Claude Code mention (use Archilles)"),
        (r"\d+\+\s*(years|yrs).*experience", "inflated experience count"),
        (r"\d{2,}\s*%", "fake percentage metrics"),
        (r"Hiring Manager", "fake hiring manager"),
        (r"deep production (ownership|experience)", "unconfirmed deep production ownership"),
    ]


def _required_sections() -> list[str]:
    """Sections every CV source must contain (as markdown headings)."""
    return [
        "Experience",
        "Education",
        "Skills",
        "Projects",
    ]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


class TestCvSourceExists:
    """The CV source markdown file must exist before anything else."""

    def test_backend_python_source_exists(self):
        path = CV_SOURCE_DIR / "backend_python" / "cv_source.md"
        assert path.exists(), f"CV source missing: {path}"


class TestLockedFactsPresent:
    """Every locked fact from the governance brief must appear in the source."""

    @pytest.fixture(autouse=True)
    def source(self):
        return _load_source("backend_python")

    def test_name_present(self, source):
        assert "Arinze Elenasulu" in source, "Name missing from CV source"

    def test_email_present(self, source):
        assert _locked_facts()["email"] in source, "Email missing from CV source"

    def test_linkedin_present(self, source):
        assert _locked_facts()["linkedin"] in source, "LinkedIn URL missing from CV source"

    def test_university_present(self, source):
        assert _locked_facts()["university"] in source, "University missing from CV source"

    def test_degree_present(self, source):
        assert _locked_facts()["degree"] in source, "Degree missing from CV source"

    def test_vigilis_present(self, source):
        assert _locked_facts()["vigilis"] in source, "Vigilis experience missing from CV source"

    def test_aptech_present(self, source):
        assert _locked_facts()["aptech"] in source, "Aptech experience missing from CV source"

    def test_pharmax_present(self, source):
        assert _locked_facts()["pharmax"] in source, "Pharmax project missing from CV source"

    def test_python_present(self, source):
        """Python must be clearly stated as a primary skill."""
        assert "Python" in source, "Python not mentioned in CV source"


class TestNoForbiddenContent:
    """Forbidden patterns from the governance brief must be absent."""

    @pytest.fixture(autouse=True)
    def source(self):
        return _load_source("backend_python")

    @pytest.mark.parametrize("pattern, description", _forbidden_patterns())
    def test_forbidden_pattern_absent(self, source, pattern, description):
        match = re.search(pattern, source, re.IGNORECASE)
        assert match is None, (
            f"Forbidden content found: '{description}' matched '{match.group()}' "
            f"in CV source"
        )


class TestHasRequiredSections:
    """The CV source must have clear markdown sections."""

    @pytest.fixture(autouse=True)
    def source(self):
        return _load_source("backend_python")

    @pytest.mark.parametrize("section", _required_sections())
    def test_section_present(self, source, section):
        # Match markdown headings: ## Section or # Section
        pattern = rf"^#{{1,3}}\s+{re.escape(section)}"
        assert re.search(pattern, source, re.MULTILINE), (
            f"Required section '{section}' not found as markdown heading"
        )


class TestVoiceAndStyle:
    """The CV source should read human, not like ATS keyword soup."""

    @pytest.fixture(autouse=True)
    def source(self):
        return _load_source("backend_python")

    def test_no_ats_keyword_density(self, source):
        """A real CV should not be a wall of comma-separated keywords.

        Check that the skill section uses natural grouping, not one long
        comma-separated list of buzzwords.
        """
        # Find the Skills section and check it doesn't contain a run of
        # more than 12 comma-separated keywords in a single line.
        skills_section = re.search(
            r"^#+\s+Skills\s*$(.*?)(?=^#+\s|\Z)",
            source,
            re.MULTILINE | re.DOTALL,
        )
        if skills_section:
            for line in skills_section.group(1).splitlines():
                if line.strip():
                    commas = line.count(",")
                    assert commas < 12, (
                        f"Skills line has {commas} commas — looks like ATS keyword soup: "
                        f"'{line.strip()[:100]}'"
                    )

    def test_personal_voice_hints(self, source):
        """The source should have at least one sentence that sounds human,
        not purely robotic listing of facts.

        We check for first-person phrasing: 'I built', 'I have', 'I enjoy', etc.
        """
        first_person_patterns = [
            r"\bI (built|designed|created|have|enjoy|care|focus|learn|work)",
        ]
        found = any(
            re.search(pat, source) for pat in first_person_patterns
        )
        assert found, "CV source has no first-person voice — reads like a robot wrote it"

    def test_not_overly_formal(self, source):
        """Should not contain stiff corporate phrases that make it sound generic."""
        stiff_phrases = [
            "spearheaded",
            "synergize",
            "leveraged my",
            "utilized",
            "in order to",
            "seasoned professional",
        ]
        for phrase in stiff_phrases:
            assert phrase.lower() not in source.lower(), (
                f"Stiff phrase found: '{phrase}' — CV sounds too formal/corporate"
            )
