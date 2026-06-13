"""Validate the CV renderer: markdown source to HTML and PDF.

TDD: these tests define the renderer contract BEFORE the renderer exists.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest


# Paths
ROOT = Path(__file__).resolve().parent.parent
CV_SOURCE_DIR = ROOT / "cv_variants"
TEST_VARIANT = "backend_python"
SOURCE_MD = CV_SOURCE_DIR / TEST_VARIANT / "cv_source.md"
OUTPUT_HTML = CV_SOURCE_DIR / TEST_VARIANT / "Arinze_Elenasulu_Backend_Python_CV.html"
OUTPUT_PDF = CV_SOURCE_DIR / TEST_VARIANT / "Arinze_Elenasulu_Backend_Python_CV.pdf"

# The renderer module we expect
RENDERER_PATH = CV_SOURCE_DIR / "renderer.py"


# ---------------------------------------------------------------------------
# RED: renderer module must exist
# ---------------------------------------------------------------------------


class TestRendererModuleExists:
    """The renderer module must be importable."""

    def test_renderer_module_exists(self):
        assert RENDERER_PATH.exists(), (
            f"Renderer module missing: {RENDERER_PATH}"
        )

    def test_renderer_has_expected_functions(self):
        # Dynamic import after module exists
        import importlib.util

        spec = importlib.util.spec_from_file_location("renderer", RENDERER_PATH)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)

        assert hasattr(renderer, "render_html"), (
            "renderer missing render_html function"
        )
        assert hasattr(renderer, "render_pdf"), (
            "renderer missing render_pdf function"
        )


# ---------------------------------------------------------------------------
# RED: HTML output tests
# ---------------------------------------------------------------------------


class TestHtmlOutput:
    """HTML rendered from CV source must be well-formed and styled."""

    @pytest.fixture(autouse=True)
    def html(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("renderer", RENDERER_PATH)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)

        return renderer.render_html(SOURCE_MD)

    def test_html_has_doctype(self, html):
        assert "<!DOCTYPE html>" in html, "HTML missing doctype declaration"

    def test_html_has_lang_attribute(self, html):
        assert 'lang="en"' in html, "HTML missing lang attribute"

    def test_html_has_title_tag(self, html):
        assert "<title>" in html, "HTML missing title tag"

    def test_html_contains_candidate_name(self, html):
        assert "Arinze Elenasulu" in html, "HTML missing candidate name"

    def test_html_contains_sections(self, html):
        """All key sections from the CV source must appear in the HTML."""
        sections = [
            "Professional Summary",
            "Core Skills",
            "Education",
            "Experience",
            "Selected Projects",
        ]
        for section in sections:
            assert section in html, f"HTML missing section: {section}"

    def test_html_has_print_stylesheet(self, html):
        """Must have @page rule for A4 output."""
        assert "@page" in html, "HTML missing @page rule for print styling"
        assert "A4" in html, "HTML must specify A4 page size"

    def test_html_has_warm_editorial_theme(self, html):
        """Warm Editorial theme colours must be present."""
        warm_colors = ["#f7f3ea", "#0f172a"]
        for color in warm_colors:
            assert color in html, (
                f"Warm Editorial theme color {color} missing from HTML"
            )

    def test_html_has_no_em_dashes(self, html):
        """Generated HTML must not contain em dashes."""
        assert "\u2014" not in html, (
            "Em dash found in generated HTML"
        )


# ---------------------------------------------------------------------------
# RED: PDF output tests
# ---------------------------------------------------------------------------


class TestPdfOutput:
    """PDF rendered from HTML must be valid and non-empty."""

    @pytest.fixture(autouse=True)
    def pdf_path(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("renderer", RENDERER_PATH)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)

        # Generate HTML first, then PDF
        html_path = CV_SOURCE_DIR / TEST_VARIANT / "_test_output.html"
        pdf_path = CV_SOURCE_DIR / TEST_VARIANT / "_test_output.pdf"
        renderer.render_pdf(SOURCE_MD, pdf_path)
        return pdf_path

    def test_pdf_file_exists_and_non_empty(self, pdf_path):
        assert pdf_path.exists(), f"PDF file not created: {pdf_path}"
        size = pdf_path.stat().st_size
        assert size > 1000, f"PDF too small ({size} bytes), likely empty or broken"

    def test_pdf_has_at_least_one_page(self, pdf_path):
        """Use pdftotext to verify the PDF has readable content."""
        if shutil.which("pdftotext") is None:
            pytest.skip("pdftotext not installed")
        import subprocess

        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-", "-l", "1"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pdftotext failed: {result.stderr}"
        assert "Arinze Elenasulu" in result.stdout, (
            "PDF first page missing candidate name"
        )

    def test_pdf_has_no_browser_headers(self, pdf_path):
        """Browser-generated PDF must not have URL/date headers."""
        if shutil.which("pdftotext") is None:
            pytest.skip("pdftotext not installed")
        import subprocess

        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-", "-l", "1"],
            capture_output=True,
            text=True,
        )
        # Headless Chrome with --no-pdf-header-footer should prevent this
        forbidden = ["file:///", "localhost", "about:blank"]
        for phrase in forbidden:
            assert phrase not in result.stdout, (
                f"PDF contains browser artifact: '{phrase}'"
            )


# ---------------------------------------------------------------------------
# RED: edge case tests
# ---------------------------------------------------------------------------


class TestRendererEdgeCases:
    """Renderer should handle edge cases gracefully."""

    def test_renderer_rejects_missing_source(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("renderer", RENDERER_PATH)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)

        missing = CV_SOURCE_DIR / TEST_VARIANT / "nonexistent.md"
        with pytest.raises(FileNotFoundError):
            renderer.render_html(missing)
