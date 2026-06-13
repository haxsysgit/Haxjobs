"""CV renderer: markdown source to styled HTML and PDF.

Uses headless Chrome for PDF generation with the Warm Editorial theme.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import markdown


# Warm Editorial theme CSS from Arinze's design standard
WARM_EDITORIAL_CSS = """
  @page { size: A4; margin: 0; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #334155;
    background: #f7f3ea;
    padding: 36px 44px;
    max-width: 210mm;
  }
  h1 { font-size: 20pt; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
  h2 { font-size: 14pt; font-weight: 600; color: #0f172a; border-bottom: 1.5px solid #cbd5e1; padding-bottom: 4px; margin: 18px 0 8px 0; }
  h3 { font-size: 11pt; font-weight: 600; color: #0f172a; margin: 12px 0 4px 0; }
  p { margin: 4px 0; color: #334155; }
  a { color: #2563eb; text-decoration: none; }
  ul { list-style: none; padding: 0; margin: 4px 0; }
  li { font-size: 9.5pt; color: #334155; padding: 2px 0 2px 14px; position: relative; line-height: 1.45; }
  li::before { content: "\\25B8"; position: absolute; left: 0; color: #64748b; font-size: 7pt; top: 4px; }
  strong { color: #0f172a; }
  em { color: #64748b; }
  hr { border: none; border-top: 1px solid #d9d6cc; margin: 12px 0; }
  .contact { font-size: 9pt; color: #64748b; margin-bottom: 4px; }
  .contact a { color: #2563eb; }
"""


def _md_to_html_body(md_text: str) -> str:
    """Convert markdown to HTML body content."""
    # Use the extras extension for code blocks, tables, etc.
    md = markdown.Markdown(extensions=["extra", "nl2br"])
    return md.convert(md_text)


def render_html(source_path: str | Path) -> str:
    """Render a CV source markdown file to a complete styled HTML document.

    Args:
        source_path: Path to cv_source.md

    Returns:
        Complete HTML string with Warm Editorial theme.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"CV source not found: {source}")

    md_text = source.read_text()
    body_html = _md_to_html_body(md_text)

    # Wrap contact info lines in a contact div for styling
    # The first paragraph after h1 usually contains contact info
    body_html = body_html.replace(
        "<p>London",
        '<p class="contact">London',
        1,
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Arinze Elenasulu, CV</title>
<style>
{WARM_EDITORIAL_CSS}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

    # Sanity check: no em dashes in output
    if "\u2014" in html:
        raise ValueError("Em dash found in generated HTML — source must be cleaned first")

    return html


def render_pdf(source_path: str | Path, output_pdf: str | Path) -> Path:
    """Render a CV source markdown to PDF via headless Chrome.

    Args:
        source_path: Path to cv_source.md
        output_pdf: Path where the PDF should be written

    Returns:
        Path to the generated PDF.
    """
    html = render_html(source_path)
    output = Path(output_pdf)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML to a temp file so Chrome can load it
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(html)
        tmp_html = tmp.name

    try:
        subprocess.run(
            [
                "google-chrome",
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output}",
                f"file://{tmp_html}",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    finally:
        Path(tmp_html).unlink(missing_ok=True)

    return output
